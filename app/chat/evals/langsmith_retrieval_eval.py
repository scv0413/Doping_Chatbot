import argparse
import uuid
from collections.abc import Callable
from typing import Any

from langsmith import Client, evaluate, traceable

from app.chat.config import settings
from app.chat.evals.cases import DEFAULT_CASES, EvalCase, case_to_inputs, case_to_outputs
from app.chat.evals.retrieval_token_experiment import (
    ExperimentConfig,
    build_eval_retrieval_query,
    count_term_hits,
    has_expected_source,
    preview_match,
    score_result,
    should_retrieve,
)
from app.chat.retrieval.query_rewriter import rewrite_query
from app.chat.retrieval.retriever import search
from app.chat.retrieval.schemas import RetrievalMatch
from app.chat.router.intent_router import route_question

DATASET_NAME = "doping-chatbot-retrieval-v1"
DATASET_DESCRIPTION = "Retrieval-only evaluation cases for the doping chatbot."
EXAMPLE_NAMESPACE = uuid.UUID("3cae3a37-68f6-4ba1-a311-3e11b41c4040")

Retriever = Callable[[str, int], list[RetrievalMatch]]


def build_example_id(case_id: str) -> uuid.UUID:
    return uuid.uuid5(EXAMPLE_NAMESPACE, case_id)


def get_or_create_dataset(
    client: Client,
    dataset_name: str = DATASET_NAME,
    description: str = DATASET_DESCRIPTION,
) -> object:
    try:
        return client.read_dataset(dataset_name=dataset_name)
    except Exception:
        return client.create_dataset(
            dataset_name=dataset_name,
            description=description,
            metadata={"app": "doping-chatbot", "eval_type": "retrieval-only"},
        )


def build_langsmith_examples(cases: list[EvalCase] | None = None) -> list[dict[str, Any]]:
    resolved_cases = cases or DEFAULT_CASES
    return [
        {
            "id": build_example_id(case.case_id),
            "inputs": case_to_inputs(case),
            "outputs": case_to_outputs(case),
            "metadata": {"case_id": case.case_id},
        }
        for case in resolved_cases
    ]


def upsert_dataset_examples(
    client: Client,
    dataset_name: str = DATASET_NAME,
    cases: list[EvalCase] | None = None,
) -> object:
    get_or_create_dataset(client=client, dataset_name=dataset_name)
    return client.create_examples(
        dataset_name=dataset_name,
        examples=build_langsmith_examples(cases),
    )


def build_retrieval_target(
    config: ExperimentConfig,
    retriever: Retriever = search,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    @traceable(name=f"retrieval_target_top{config.top_k}_rewrite{config.rewrite_enabled}")
    def target(inputs: dict[str, Any]) -> dict[str, Any]:
        query = str(inputs["query"])
        retrieval_terms = tuple(str(term) for term in inputs.get("retrieval_terms", []))
        decision = route_question(query)
        retrieval_query = build_eval_retrieval_query(query, decision.route)
        if retrieval_query and retrieval_terms:
            retrieval_query = "\n".join([retrieval_query, *retrieval_terms])
        final_query = rewrite_query(retrieval_query) if config.rewrite_enabled else retrieval_query

        matches: list[RetrievalMatch] = []
        error: str | None = None
        if should_retrieve(decision.route):
            try:
                matches = retriever(final_query, config.top_k)
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"

        return {
            "actual_route": decision.route.value,
            "route_reason": decision.reason,
            "matched_terms": decision.matched_terms,
            "retrieval_query": retrieval_query,
            "final_query": final_query,
            "top_k": config.top_k,
            "rewrite_enabled": config.rewrite_enabled,
            "match_count": len(matches),
            "source_ids": [match.source_id for match in matches],
            "chunk_ids": [match.chunk_id for match in matches],
            "distances": [round(match.distance, 4) for match in matches],
            "context_chars": sum(len(match.text) for match in matches),
            "retrieved_text": "\n".join(match.text for match in matches),
            "previews": [preview_match(match, config.max_preview_chars) for match in matches],
            "error": error,
        }

    return target


def route_match_evaluator(outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> dict[str, Any]:
    expected_route = reference_outputs.get("expected_route")
    actual_route = outputs.get("actual_route")
    return {
        "key": "route_match",
        "score": int(actual_route == expected_route),
        "comment": f"expected={expected_route}, actual={actual_route}",
    }


def source_hit_evaluator(outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> dict[str, Any]:
    expected_sources = tuple(reference_outputs.get("expected_sources", []))
    source_ids = list(outputs.get("source_ids", []))
    score = int(has_expected_source(source_ids, expected_sources))
    return {
        "key": "source_hit",
        "score": score,
        "comment": f"expected_any={list(expected_sources)}, actual={source_ids}",
    }


def term_hit_evaluator(outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> dict[str, Any]:
    terms = tuple(reference_outputs.get("must_include_terms", []))
    text = str(outputs.get("retrieved_text", ""))
    hits = count_term_hits(text, terms)
    score = 1 if not terms or hits > 0 else 0
    return {
        "key": "term_hit",
        "score": score,
        "comment": f"hits={hits}/{len(terms)}",
    }


def context_budget_evaluator(outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> dict[str, Any]:
    del reference_outputs
    context_chars = int(outputs.get("context_chars", 0))
    score = int(context_chars <= 3000)
    return {
        "key": "context_budget",
        "score": score,
        "comment": f"context_chars={context_chars}, budget=3000",
    }


def retrieval_quality_evaluator(outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> dict[str, Any]:
    expected_route = str(reference_outputs.get("expected_route"))
    source_ids = list(outputs.get("source_ids", []))
    terms = tuple(reference_outputs.get("must_include_terms", []))
    retrieved_text = str(outputs.get("retrieved_text", ""))
    error = outputs.get("error")
    route_match = outputs.get("actual_route") == expected_route
    expected_source_hit = has_expected_source(
        source_ids=source_ids,
        expected_sources=tuple(reference_outputs.get("expected_sources", [])),
    )
    must_terms_hit = count_term_hits(retrieved_text, terms)
    quality_score = score_result(
        route_match=route_match,
        expected_source_hit=expected_source_hit,
        must_terms_hit=must_terms_hit,
        must_terms_total=len(terms),
        should_have_matches=outputs.get("actual_route") != "drug_search",
        match_count=int(outputs.get("match_count", 0)),
        error=str(error) if error else None,
    )
    return {
        "key": "retrieval_quality",
        "score": quality_score / 3,
        "comment": f"quality_score={quality_score}/3",
    }


def run_langsmith_retrieval_eval(
    config: ExperimentConfig,
    dataset_name: str = DATASET_NAME,
    upload_dataset: bool = True,
    client: Client | None = None,
) -> object:
    resolved_client = client or Client()
    if upload_dataset:
        upsert_dataset_examples(client=resolved_client, dataset_name=dataset_name)

    return evaluate(
        build_retrieval_target(config),
        data=dataset_name,
        evaluators=[
            route_match_evaluator,
            source_hit_evaluator,
            term_hit_evaluator,
            context_budget_evaluator,
            retrieval_quality_evaluator,
        ],
        experiment_prefix=f"retrieval-top{config.top_k}-rewrite-{config.rewrite_enabled}",
        description="Retrieval-only evaluation before LLM answer evaluation.",
        metadata={
            "top_k": config.top_k,
            "rewrite_enabled": config.rewrite_enabled,
            "project": settings.langsmith_project,
        },
        client=resolved_client,
        blocking=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-name", default=DATASET_NAME)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--rewrite", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--skip-dataset-upload", action="store_true")
    args = parser.parse_args()

    result = run_langsmith_retrieval_eval(
        config=ExperimentConfig(top_k=args.top_k, rewrite_enabled=args.rewrite),
        dataset_name=args.dataset_name,
        upload_dataset=not args.skip_dataset_upload,
    )
    print(result)


if __name__ == "__main__":
    main()
