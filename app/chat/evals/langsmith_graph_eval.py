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
from app.chat.graph.graph import run_chat_graph
from app.chat.domain.retrieval.query_rewriter import rewrite_query
from app.chat.pipeline.chat_pipeline import ChatPipelineResult

DEFAULT_TOP_K = 3
GraphRunner = Callable[..., ChatPipelineResult]


def build_graph_retrieval_target(
    top_k: int = DEFAULT_TOP_K,
    use_llm: bool = False,
    graph_runner: GraphRunner = run_chat_graph,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    target_name = "graph_retrieval_target"

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
        return {
            "actual_route": result.decision.route.value,
            "route_reason": result.decision.reason,
            "matched_terms": result.decision.matched_terms,
            "retrieval_query": result.retrieval_query,
            "final_query": result.rewritten_query,
            "top_k": top_k,
            "rewrite_enabled": result.rewritten_query != result.retrieval_query,
            "match_count": len(result.retrieval_matches),
            "source_ids": [match.source_id for match in result.retrieval_matches],
            "chunk_ids": [match.chunk_id for match in result.retrieval_matches],
            "distances": [round(match.distance, 4) for match in result.retrieval_matches],
            "context_chars": sum(len(match.text) for match in result.retrieval_matches),
            "retrieved_text": "\n".join(match.text for match in result.retrieval_matches),
            "answer_chars": len(result.answer),
            "retrieval_attempts": result.retrieval_attempts,
            "retrieval_retry_reason": result.retrieval_retry_reason,
            "errors": [error.model_dump() for error in result.errors],
            "error": "; ".join(error.message for error in result.errors) or None,
        }

    return target


def run_langsmith_graph_retrieval_eval(
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
        build_graph_retrieval_target(top_k=top_k, use_llm=use_llm),
        data=dataset_name,
        evaluators=[
            route_match_evaluator,
            source_hit_evaluator,
            term_hit_evaluator,
            context_budget_evaluator,
            retrieval_quality_evaluator,
        ],
        experiment_prefix=f"graph-retrieval-top{top_k}-llm-{use_llm}",
        description="LangGraph execution evaluated with retrieval-only criteria.",
        metadata={
            "top_k": top_k,
            "use_llm": use_llm,
            "runner": "langgraph",
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

    result = run_langsmith_graph_retrieval_eval(
        dataset_name=args.dataset_name,
        top_k=args.top_k,
        use_llm=args.use_llm,
        upload_dataset=not args.skip_dataset_upload,
    )
    print(result)


if __name__ == "__main__":
    main()
