import argparse
import uuid
from collections.abc import Callable
from typing import Any

from langsmith import Client, evaluate, traceable

from app.core.config import settings
from app.chat.evals.answer_cases import (
    ANSWER_EVAL_CASES,
    AnswerEvalCase,
    answer_case_to_inputs,
    answer_case_to_outputs,
)
from app.chat.orchestration.pipeline.chat_pipeline import ChatPipelineResult, run_chat_pipeline
from app.chat.domain.policy.answer_policy import OFFICIAL_DECISION_DISCLAIMER, get_answer_rule

DATASET_NAME = "doping-chatbot-answer-v1"
DATASET_DESCRIPTION = "Answer evaluation cases for formatter and LLM chain outputs."
EXAMPLE_NAMESPACE = uuid.UUID("d7f3a71d-8e2e-43b8-93a8-c2fc12d68e01")
DEFAULT_TOP_K = 3

PipelineRunner = Callable[..., ChatPipelineResult]


def build_answer_example_id(case_id: str) -> uuid.UUID:
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
            metadata={"app": "doping-chatbot", "eval_type": "answer-formatter"},
        )


def build_langsmith_examples(cases: list[AnswerEvalCase] | None = None) -> list[dict[str, Any]]:
    resolved_cases = cases or ANSWER_EVAL_CASES
    return [
        {
            "id": build_answer_example_id(case.case_id),
            "inputs": answer_case_to_inputs(case),
            "outputs": answer_case_to_outputs(case),
            "metadata": {"case_id": case.case_id},
        }
        for case in resolved_cases
    ]


def upsert_dataset_examples(
    client: Client,
    dataset_name: str = DATASET_NAME,
    cases: list[AnswerEvalCase] | None = None,
) -> object | None:
    dataset = get_or_create_dataset(client=client, dataset_name=dataset_name)
    examples = build_langsmith_examples(cases)
    existing_examples = {
        str(example.metadata.get("case_id")): example.id
        for example in client.list_examples(dataset_id=getattr(dataset, "id", None))
        if isinstance(example.metadata, dict) and example.metadata.get("case_id")
    }

    for example in examples:
        case_id = str(example["metadata"]["case_id"])
        existing_id = existing_examples.get(case_id)
        if existing_id is None:
            client.create_examples(
                dataset_id=getattr(dataset, "id", None),
                examples=[example],
            )
            continue

        client.update_example(
            example_id=existing_id,
            inputs=example["inputs"],
            outputs=example["outputs"],
            metadata=example["metadata"],
            dataset_id=getattr(dataset, "id", None),
        )
    return None


def build_answer_target(
    top_k: int = DEFAULT_TOP_K,
    use_llm: bool = False,
    pipeline_runner: PipelineRunner = run_chat_pipeline,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    target_name = "answer_chain_target" if use_llm else "answer_formatter_target"

    @traceable(name=f"{target_name}_top{top_k}")
    def target(inputs: dict[str, Any]) -> dict[str, Any]:
        query = str(inputs["query"])
        result = pipeline_runner(query, top_k=top_k, use_llm=use_llm)
        answer = result.answer
        return {
            "answer": answer,
            "actual_route": result.decision.route.value,
            "retrieval_query": result.retrieval_query,
            "rewritten_query": result.rewritten_query,
            "source_ids": [match.source_id for match in result.retrieval_matches],
            "chunk_ids": [match.chunk_id for match in result.retrieval_matches],
            "official_source_citations": [
                {
                    "source_id": match.metadata.official_source_id,
                    "page": match.metadata.official_source_page,
                }
                for match in result.retrieval_matches
                if match.metadata.official_source_id
            ],
            "drug_status": result.drug_result.status.value if result.drug_result else None,
            "errors": [error.model_dump() for error in result.errors],
            "answer_chars": len(answer),
            "use_llm": use_llm,
            "top_k": top_k,
        }

    return target


def normalize_text(text: str) -> str:
    return text.casefold().replace(" ", "")


def count_concept_hits(answer: str, groups: list[list[str]]) -> int:
    normalized_answer = normalize_text(answer)
    hits = 0
    for group in groups:
        if any(normalize_text(term) in normalized_answer for term in group):
            hits += 1
    return hits


def route_match_evaluator(outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> dict[str, Any]:
    expected_route = reference_outputs.get("expected_route")
    actual_route = outputs.get("actual_route")
    return {
        "key": "answer_route_match",
        "score": int(actual_route == expected_route),
        "comment": f"expected={expected_route}, actual={actual_route}",
    }


def must_include_evaluator(outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> dict[str, Any]:
    answer = str(outputs.get("answer", ""))
    groups = list(reference_outputs.get("must_include_groups", []))
    hits = count_concept_hits(answer, groups)
    score = hits / len(groups) if groups else 1
    return {
        "key": "answer_must_include",
        "score": score,
        "comment": f"concept_hits={hits}/{len(groups)}",
    }


def must_not_include_evaluator(outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> dict[str, Any]:
    answer = str(outputs.get("answer", ""))
    normalized_answer = normalize_text(answer)
    banned_terms = list(reference_outputs.get("must_not_include_terms", []))
    found = [term for term in banned_terms if normalize_text(term) in normalized_answer]
    return {
        "key": "answer_must_not_include",
        "score": int(not found),
        "comment": f"found={found}",
    }


def citation_presence_evaluator(outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> dict[str, Any]:
    del reference_outputs
    answer = str(outputs.get("answer", ""))
    has_citation_section = "## 근거" in answer
    has_chunk_id = bool(outputs.get("chunk_ids")) and ":" in answer
    return {
        "key": "answer_citation_presence",
        "score": int(has_citation_section and has_chunk_id),
        "comment": (
            f"{get_answer_rule('explicit_citations').name}: "
            f"has_citation_section={has_citation_section}, has_chunk_id={has_chunk_id}"
        ),
    }


def reviewed_manual_official_citation_evaluator(
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
) -> dict[str, Any]:
    del reference_outputs
    reviewed_sources = [
        source_id
        for source_id in outputs.get("source_ids", [])
        if isinstance(source_id, str) and source_id.endswith("_human_reviewed")
    ]
    if not reviewed_sources:
        return {
            "key": "answer_reviewed_manual_official_citation",
            "score": 1,
            "comment": "not_applicable:no_human_reviewed_source",
        }

    answer = str(outputs.get("answer", ""))
    official_citations = list(outputs.get("official_source_citations", []))
    valid_citations = [
        citation
        for citation in official_citations
        if isinstance(citation, dict)
        and isinstance(citation.get("source_id"), str)
        and isinstance(citation.get("page"), int)
        and f"`{citation['source_id']}`" in answer
        and f"p.{citation['page']}" in answer
    ]
    score = int(len(valid_citations) >= len(reviewed_sources))
    return {
        "key": "answer_reviewed_manual_official_citation",
        "score": score,
        "comment": (
            f"reviewed_sources={len(reviewed_sources)}, "
            f"valid_official_citations={len(valid_citations)}"
        ),
    }


def safety_disclaimer_evaluator(outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> dict[str, Any]:
    del reference_outputs
    answer = str(outputs.get("answer", ""))
    normalized_answer = normalize_text(answer)
    required = normalize_text(OFFICIAL_DECISION_DISCLAIMER)
    score = int(required in normalized_answer)
    return {
        "key": "answer_safety_disclaimer",
        "score": score,
        "comment": f"{get_answer_rule('apply_safety_caveats').name}: requires policy official decision disclaimer",
    }


def pipeline_error_evaluator(outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> dict[str, Any]:
    del reference_outputs
    errors = list(outputs.get("errors", []))
    return {
        "key": "answer_pipeline_errors",
        "score": int(not errors),
        "comment": f"errors={len(errors)}",
    }


def run_langsmith_answer_eval(
    dataset_name: str = DATASET_NAME,
    top_k: int = DEFAULT_TOP_K,
    use_llm: bool = False,
    upload_dataset: bool = True,
    client: Client | None = None,
) -> object:
    resolved_client = client or Client()
    if upload_dataset:
        upsert_dataset_examples(client=resolved_client, dataset_name=dataset_name)

    experiment_kind = "answer-chain" if use_llm else "answer-formatter"

    return evaluate(
        build_answer_target(top_k=top_k, use_llm=use_llm),
        data=dataset_name,
        evaluators=[
            route_match_evaluator,
            must_include_evaluator,
            must_not_include_evaluator,
            citation_presence_evaluator,
            reviewed_manual_official_citation_evaluator,
            safety_disclaimer_evaluator,
            pipeline_error_evaluator,
        ],
        experiment_prefix=f"{experiment_kind}-top{top_k}",
        description="Answer evaluation using deterministic formatter or LLM chain output.",
        metadata={
            "top_k": top_k,
            "use_llm": use_llm,
            "project": settings.langsmith_project,
        },
        client=resolved_client,
        blocking=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-name", default=DATASET_NAME)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--use-llm", action="store_true")
    parser.add_argument("--skip-dataset-upload", action="store_true")
    args = parser.parse_args()

    result = run_langsmith_answer_eval(
        dataset_name=args.dataset_name,
        top_k=args.top_k,
        use_llm=args.use_llm,
        upload_dataset=not args.skip_dataset_upload,
    )
    print(result)


if __name__ == "__main__":
    main()
