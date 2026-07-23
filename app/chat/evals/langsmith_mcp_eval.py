from __future__ import annotations

import argparse
import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from langsmith import Client, evaluate, traceable
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

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
from app.chat.evals.langsmith_tool_eval import tool_contract_evaluator
from app.chat.evals.retrieval_token_experiment import build_eval_retrieval_query, should_retrieve
from app.chat.pharmacology.service import should_run_pharmacology_info
from app.chat.retrieval.query_rewriter import rewrite_query
from app.chat.router.intent_router import ChatRoute, route_question

DEFAULT_TOP_K = 3
DEFAULT_MCP_URL = "http://127.0.0.1:8012/mcp"
EXPECTED_MCP_TOOLS = {"rag_search_tool", "drug_search_tool", "pharmacology_info_tool"}

ToolCall = tuple[str, dict[str, Any]]
MCPSequenceRunner = Callable[[str, list[ToolCall]], Awaitable[dict[str, Any]]]


async def run_mcp_tool_sequence(url: str, tool_calls: list[ToolCall]) -> dict[str, Any]:
    async with streamablehttp_client(url) as (read_stream, write_stream, _get_session_id):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools_response = await session.list_tools()
            tool_names = sorted(tool.name for tool in tools_response.tools)

            call_results: dict[str, dict[str, Any]] = {}
            for tool_name, arguments in tool_calls:
                call_result = await session.call_tool(tool_name, arguments)
                call_results[tool_name] = {
                    "is_error": bool(call_result.isError),
                    "structured_content": call_result.structuredContent or {},
                }

            return {
                "tool_names": tool_names,
                "call_results": call_results,
            }


def build_mcp_tool_calls(
    query: str,
    route: ChatRoute,
    retrieval_terms: tuple[str, ...],
    top_k: int,
    rewrite_enabled: bool,
) -> tuple[str, str, list[ToolCall]]:
    retrieval_query = build_eval_retrieval_query(query, route)
    if retrieval_query and retrieval_terms:
        retrieval_query = "\n".join([retrieval_query, *retrieval_terms])
    final_query = rewrite_query(retrieval_query) if rewrite_enabled and retrieval_query else retrieval_query

    request_id_prefix = query[:32]
    tool_calls: list[ToolCall] = []
    if should_retrieve(route):
        tool_calls.append(
            (
                "rag_search_tool",
                {
                    "query": final_query,
                    "top_k": top_k,
                    "request_id": f"mcp-eval:rag:{request_id_prefix}",
                },
            )
        )

    if route in {ChatRoute.DRUG_SEARCH, ChatRoute.DRUG_SEARCH_WITH_RAG}:
        tool_calls.append(
            (
                "drug_search_tool",
                {
                    "query": query,
                    "competition_period": "unknown",
                    "request_id": f"mcp-eval:drug:{request_id_prefix}",
                },
            )
        )

    if should_run_pharmacology_info(query):
        tool_calls.append(
            (
                "pharmacology_info_tool",
                {
                    "query": query,
                    "request_id": f"mcp-eval:pharmacology:{request_id_prefix}",
                },
            )
        )

    return retrieval_query, final_query, tool_calls


async def run_mcp_eval_case(
    inputs: dict[str, Any],
    url: str = DEFAULT_MCP_URL,
    top_k: int = DEFAULT_TOP_K,
    rewrite_enabled: bool = True,
    sequence_runner: MCPSequenceRunner = run_mcp_tool_sequence,
) -> dict[str, Any]:
    query = str(inputs["query"])
    retrieval_terms = tuple(str(term) for term in inputs.get("retrieval_terms", []))
    decision = route_question(query)
    retrieval_query, final_query, tool_calls = build_mcp_tool_calls(
        query=query,
        route=decision.route,
        retrieval_terms=retrieval_terms,
        top_k=top_k,
        rewrite_enabled=rewrite_enabled,
    )

    sequence_error: str | None = None
    tool_names: list[str] = []
    call_results: dict[str, dict[str, Any]] = {}
    try:
        sequence_output = await sequence_runner(url, tool_calls)
        tool_names = list(sequence_output.get("tool_names", []))
        call_results = dict(sequence_output.get("call_results", {}))
    except Exception as exc:  # pragma: no cover - exercised by CLI/runtime validation
        sequence_error = f"{type(exc).__name__}: {exc}"

    rag_payload = get_tool_payload(call_results, "rag_search_tool")
    drug_payload = get_tool_payload(call_results, "drug_search_tool")
    pharmacology_payload = get_tool_payload(call_results, "pharmacology_info_tool")

    rag_results = list(rag_payload.get("results", []))
    drug_result = drug_payload.get("result") or {}
    pharmacology_result = pharmacology_payload.get("result") or {}

    rag_errors = list(rag_payload.get("errors", []))
    drug_errors = list(drug_payload.get("errors", []))
    pharmacology_errors = list(pharmacology_payload.get("errors", []))

    retrieved_text = "\n".join(str(result.get("text", "")) for result in rag_results)
    errors = [sequence_error] if sequence_error else []

    return {
        "query": query,
        "actual_route": decision.route.value,
        "route_reason": decision.reason,
        "matched_terms": decision.matched_terms,
        "retrieval_query": retrieval_query,
        "final_query": final_query,
        "top_k": top_k,
        "rewrite_enabled": rewrite_enabled,
        "mcp_url": url,
        "mcp_tool_names": tool_names,
        "mcp_missing_tools": sorted(EXPECTED_MCP_TOOLS - set(tool_names)) if tool_names else sorted(EXPECTED_MCP_TOOLS),
        "mcp_called_tools": [tool_name for tool_name, _arguments in tool_calls],
        "tool_name": rag_payload.get("tool_name"),
        "tool_query": rag_payload.get("query"),
        "tool_top_k": rag_payload.get("top_k"),
        "tool_result_count": len(rag_results),
        "tool_errors": rag_errors,
        "tool_source_ids": [result.get("source_id") for result in rag_results],
        "tool_chunk_ids": [result.get("chunk_id") for result in rag_results],
        "rag_tool_name": rag_payload.get("tool_name"),
        "rag_tool_query": rag_payload.get("query"),
        "rag_tool_top_k": rag_payload.get("top_k"),
        "rag_tool_result_count": len(rag_results),
        "rag_tool_errors": rag_errors,
        "rag_tool_source_ids": [result.get("source_id") for result in rag_results],
        "rag_tool_chunk_ids": [result.get("chunk_id") for result in rag_results],
        "drug_tool_name": drug_payload.get("tool_name"),
        "drug_tool_query": drug_payload.get("query"),
        "drug_tool_status": drug_result.get("status"),
        "drug_tool_matched_substances": drug_result.get("matched_substances", []),
        "drug_tool_prohibited_categories": drug_result.get("prohibited_categories", []),
        "drug_tool_errors": drug_errors,
        "pharmacology_tool_name": pharmacology_payload.get("tool_name"),
        "pharmacology_tool_query": pharmacology_payload.get("query"),
        "pharmacology_tool_status": pharmacology_result.get("status"),
        "pharmacology_tool_substance_name": pharmacology_result.get("substance_name"),
        "pharmacology_tool_matched_terms": pharmacology_result.get("matched_terms", []),
        "pharmacology_tool_has_half_life": bool(pharmacology_result.get("half_life")),
        "pharmacology_tool_errors": pharmacology_errors,
        "match_count": len(rag_results),
        "source_ids": [result.get("source_id") for result in rag_results],
        "chunk_ids": [result.get("chunk_id") for result in rag_results],
        "distances": [round(float(result.get("distance", 0.0)), 4) for result in rag_results],
        "context_chars": sum(len(str(result.get("text", ""))) for result in rag_results),
        "retrieved_text": retrieved_text,
        "error": "; ".join(errors) or None,
    }


def get_tool_payload(call_results: dict[str, dict[str, Any]], tool_name: str) -> dict[str, Any]:
    return dict(call_results.get(tool_name, {}).get("structured_content") or {})


def build_mcp_tool_target(
    url: str = DEFAULT_MCP_URL,
    top_k: int = DEFAULT_TOP_K,
    rewrite_enabled: bool = True,
    sequence_runner: MCPSequenceRunner = run_mcp_tool_sequence,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    @traceable(name=f"mcp_tool_target_top{top_k}_rewrite{rewrite_enabled}")
    def target(inputs: dict[str, Any]) -> dict[str, Any]:
        return asyncio.run(
            run_mcp_eval_case(
                inputs=inputs,
                url=url,
                top_k=top_k,
                rewrite_enabled=rewrite_enabled,
                sequence_runner=sequence_runner,
            )
        )

    return target


def mcp_connection_evaluator(outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> dict[str, Any]:
    del reference_outputs
    missing_tools = list(outputs.get("mcp_missing_tools", []))
    error = outputs.get("error")
    score = int(not missing_tools and not error)
    return {
        "key": "mcp_connection",
        "score": score,
        "comment": f"missing_tools={missing_tools}, error={error}",
    }


def run_langsmith_mcp_tool_eval(
    dataset_name: str = RETRIEVAL_DATASET_NAME,
    top_k: int = DEFAULT_TOP_K,
    rewrite_enabled: bool = True,
    mcp_url: str = DEFAULT_MCP_URL,
    upload_dataset: bool = True,
    client: Client | None = None,
) -> object:
    resolved_client = client or Client()
    if upload_dataset:
        upsert_dataset_examples(client=resolved_client, dataset_name=dataset_name)
    else:
        get_or_create_dataset(client=resolved_client, dataset_name=dataset_name)

    return evaluate(
        build_mcp_tool_target(url=mcp_url, top_k=top_k, rewrite_enabled=rewrite_enabled),
        data=dataset_name,
        evaluators=[
            route_match_evaluator,
            source_hit_evaluator,
            term_hit_evaluator,
            context_budget_evaluator,
            retrieval_quality_evaluator,
            tool_contract_evaluator,
            mcp_connection_evaluator,
        ],
        experiment_prefix=f"mcp-tool-top{top_k}-rewrite-{rewrite_enabled}",
        description="MCP streamable HTTP tool calls evaluated through LangSmith.",
        metadata={
            "top_k": top_k,
            "rewrite_enabled": rewrite_enabled,
            "runner": "mcp_streamable_http",
            "mcp_url": mcp_url,
            "tools": sorted(EXPECTED_MCP_TOOLS),
            "project": settings.langsmith_project,
        },
        client=resolved_client,
        blocking=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-name", default=RETRIEVAL_DATASET_NAME)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--mcp-url", default=DEFAULT_MCP_URL)
    parser.add_argument("--no-rewrite", action="store_true")
    parser.add_argument("--skip-dataset-upload", action="store_true")
    args = parser.parse_args()

    result = run_langsmith_mcp_tool_eval(
        dataset_name=args.dataset_name,
        top_k=args.top_k,
        rewrite_enabled=not args.no_rewrite,
        mcp_url=args.mcp_url,
        upload_dataset=not args.skip_dataset_upload,
    )
    print(result)


if __name__ == "__main__":
    main()
