import argparse
from collections.abc import Callable
from typing import Any

from langsmith import Client, evaluate, traceable

from app.core.config import settings
from app.chat.evals.langsmith_retrieval_eval import (
    DATASET_NAME as RETRIEVAL_DATASET_NAME,
    context_budget_evaluator,
    get_or_create_dataset,
    retrieval_quality_evaluator,
    route_match_evaluator,
    source_hit_evaluator,
    term_hit_evaluator,
    upsert_dataset_examples,
)
from app.chat.orchestration.graph.graph import run_chat_graph
from app.chat.domain.pharmacology.service import should_run_pharmacology_info
from app.chat.orchestration.pipeline.chat_pipeline import ChatPipelineResult
from app.chat.domain.retrieval.query_rewriter import rewrite_query

DEFAULT_TOP_K = 3
GraphRunner = Callable[..., ChatPipelineResult]


def build_graph_tool_target(
    top_k: int = DEFAULT_TOP_K,
    use_llm: bool = False,
    graph_runner: GraphRunner = run_chat_graph,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    target_name = "graph_tool_target"

    @traceable(name=f"{target_name}_top{top_k}_llm{use_llm}")
    def target(inputs: dict[str, Any]) -> dict[str, Any]:
        query = str(inputs["query"])
        retrieval_terms = tuple(str(term) for term in inputs.get("retrieval_terms", []))

        def eval_query_rewriter(retrieval_query: str) -> str:
            rewritten_query = rewrite_query(retrieval_query)
            if not retrieval_terms:
                return rewritten_query
            return "\n".join([rewritten_query, *retrieval_terms])

        result = graph_runner(
            query,
            top_k=top_k,
            use_llm=use_llm,
            query_rewriter=eval_query_rewriter,
        )
        rag_output = result.rag_search_output
        rag_results = rag_output.results if rag_output else []
        rag_errors = rag_output.errors if rag_output else []
        drug_output = result.drug_search_tool_output
        drug_result = drug_output.result if drug_output else None
        drug_errors = drug_output.errors if drug_output else []
        pharmacology_output = result.pharmacology_info_tool_output
        pharmacology_result = pharmacology_output.result if pharmacology_output else None
        pharmacology_errors = pharmacology_output.errors if pharmacology_output else []

        return {
            "query": query,
            "actual_route": result.decision.route.value,
            "route_reason": result.decision.reason,
            "matched_terms": result.decision.matched_terms,
            "retrieval_query": result.retrieval_query,
            "final_query": result.rewritten_query,
            "top_k": top_k,
            "rewrite_enabled": result.rewritten_query != result.retrieval_query,
            "tool_name": rag_output.tool_name if rag_output else None,
            "tool_query": rag_output.query if rag_output else None,
            "tool_top_k": rag_output.top_k if rag_output else None,
            "tool_result_count": len(rag_results),
            "tool_errors": [error.model_dump() for error in rag_errors],
            "tool_source_ids": [tool_result.source_id for tool_result in rag_results],
            "tool_chunk_ids": [tool_result.chunk_id for tool_result in rag_results],
            "rag_tool_name": rag_output.tool_name if rag_output else None,
            "rag_tool_query": rag_output.query if rag_output else None,
            "rag_tool_top_k": rag_output.top_k if rag_output else None,
            "rag_tool_result_count": len(rag_results),
            "rag_tool_errors": [error.model_dump() for error in rag_errors],
            "rag_tool_source_ids": [tool_result.source_id for tool_result in rag_results],
            "rag_tool_chunk_ids": [tool_result.chunk_id for tool_result in rag_results],
            "drug_tool_name": drug_output.tool_name if drug_output else None,
            "drug_tool_query": drug_output.query if drug_output else None,
            "drug_tool_status": drug_result.status.value if drug_result else None,
            "drug_tool_matched_substances": drug_result.matched_substances if drug_result else [],
            "drug_tool_prohibited_categories": drug_result.prohibited_categories if drug_result else [],
            "drug_tool_errors": [error.model_dump() for error in drug_errors],
            "pharmacology_tool_name": pharmacology_output.tool_name if pharmacology_output else None,
            "pharmacology_tool_query": pharmacology_output.query if pharmacology_output else None,
            "pharmacology_tool_status": pharmacology_result.status.value if pharmacology_result else None,
            "pharmacology_tool_substance_name": pharmacology_result.substance_name if pharmacology_result else None,
            "pharmacology_tool_matched_terms": pharmacology_result.matched_terms if pharmacology_result else [],
            "pharmacology_tool_has_half_life": bool(pharmacology_result and pharmacology_result.half_life),
            "pharmacology_tool_errors": [error.model_dump() for error in pharmacology_errors],
            "match_count": len(result.retrieval_matches),
            "source_ids": [match.source_id for match in result.retrieval_matches],
            "chunk_ids": [match.chunk_id for match in result.retrieval_matches],
            "distances": [round(match.distance, 4) for match in result.retrieval_matches],
            "context_chars": sum(len(match.text) for match in result.retrieval_matches),
            "retrieved_text": "\n".join(match.text for match in result.retrieval_matches),
            "answer_chars": len(result.answer),
            "retrieval_attempts": result.retrieval_attempts,
            "retrieval_retry_reason": result.retrieval_retry_reason,
            "planned_tool_names": result.planned_tool_names,
            "errors": [error.model_dump() for error in result.errors],
            "error": "; ".join(error.message for error in result.errors) or None,
        }

    return target


def should_have_rag_tool(route: str | None) -> bool:
    return route in {"rag", "drug_search_with_rag"}


def should_have_drug_tool(route: str | None) -> bool:
    return route in {"drug_search", "drug_search_with_rag"}


def should_have_pharmacology_tool(query: str | None) -> bool:
    return should_run_pharmacology_info(str(query or ""))


def score_rag_tool_contract(outputs: dict[str, Any]) -> bool:
    route = outputs.get("actual_route")
    rag_tool_name = outputs.get("rag_tool_name")
    rag_tool_result_count = int(outputs.get("rag_tool_result_count", outputs.get("tool_result_count", 0)))
    rag_tool_errors = list(outputs.get("rag_tool_errors", outputs.get("tool_errors", [])))
    chunk_ids = list(outputs.get("chunk_ids", []))
    rag_tool_chunk_ids = list(outputs.get("rag_tool_chunk_ids", outputs.get("tool_chunk_ids", [])))

    if not should_have_rag_tool(str(route)):
        return rag_tool_name is None and rag_tool_result_count == 0

    return (
        rag_tool_name == "rag_search_tool"
        and rag_tool_result_count == len(chunk_ids)
        and rag_tool_chunk_ids == chunk_ids
        and not rag_tool_errors
    )


def score_drug_tool_contract(outputs: dict[str, Any]) -> bool:
    route = outputs.get("actual_route")
    drug_tool_name = outputs.get("drug_tool_name")
    drug_tool_errors = list(outputs.get("drug_tool_errors", []))
    drug_tool_status = outputs.get("drug_tool_status")

    if not should_have_drug_tool(str(route)):
        return drug_tool_name is None

    return drug_tool_name == "drug_search_tool" and bool(drug_tool_status) and not drug_tool_errors


def score_pharmacology_tool_contract(outputs: dict[str, Any]) -> bool:
    pharmacology_tool_name = outputs.get("pharmacology_tool_name")
    pharmacology_tool_status = outputs.get("pharmacology_tool_status")
    pharmacology_tool_errors = list(outputs.get("pharmacology_tool_errors", []))

    if not should_have_pharmacology_tool(outputs.get("query")):
        return pharmacology_tool_name is None

    return (
        pharmacology_tool_name == "pharmacology_info_tool"
        and bool(pharmacology_tool_status)
        and not pharmacology_tool_errors
    )


def tool_contract_evaluator(outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> dict[str, Any]:
    del reference_outputs
    rag_ok = score_rag_tool_contract(outputs)
    drug_ok = score_drug_tool_contract(outputs)
    pharmacology_ok = score_pharmacology_tool_contract(outputs)
    score = int(rag_ok and drug_ok and pharmacology_ok)

    return {
        "key": "tool_contract",
        "score": score,
        "comment": (
            f"route={outputs.get('actual_route')}, "
            f"rag_tool={outputs.get('rag_tool_name') or outputs.get('tool_name')}, "
            f"drug_tool={outputs.get('drug_tool_name')}, "
            f"pharmacology_tool={outputs.get('pharmacology_tool_name')}, "
            f"rag_ok={rag_ok}, drug_ok={drug_ok}, pharmacology_ok={pharmacology_ok}"
        ),
    }


def run_langsmith_graph_tool_eval(
    dataset_name: str = RETRIEVAL_DATASET_NAME,
    top_k: int = DEFAULT_TOP_K,
    use_llm: bool = False,
    upload_dataset: bool = True,
    client: Client | None = None,
) -> object:
    resolved_client = client or Client()
    if upload_dataset:
        upsert_dataset_examples(client=resolved_client, dataset_name=dataset_name)
    else:
        get_or_create_dataset(client=resolved_client, dataset_name=dataset_name)

    return evaluate(
        build_graph_tool_target(top_k=top_k, use_llm=use_llm),
        data=dataset_name,
        evaluators=[
            route_match_evaluator,
            source_hit_evaluator,
            term_hit_evaluator,
            context_budget_evaluator,
            retrieval_quality_evaluator,
            tool_contract_evaluator,
        ],
        experiment_prefix=f"graph-tool-top{top_k}-llm-{use_llm}",
        description="LangGraph retrieval, drug search, and pharmacology info evaluated through tool contracts.",
        metadata={
            "top_k": top_k,
            "use_llm": use_llm,
            "runner": "langgraph",
            "tools": ["rag_search_tool", "drug_search_tool", "pharmacology_info_tool"],
            "project": settings.langsmith_project,
        },
        client=resolved_client,
        blocking=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-name", default=RETRIEVAL_DATASET_NAME)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--use-llm", action="store_true")
    parser.add_argument("--skip-dataset-upload", action="store_true")
    args = parser.parse_args()

    result = run_langsmith_graph_tool_eval(
        dataset_name=args.dataset_name,
        top_k=args.top_k,
        use_llm=args.use_llm,
        upload_dataset=not args.skip_dataset_upload,
    )
    print(result)


if __name__ == "__main__":
    main()
