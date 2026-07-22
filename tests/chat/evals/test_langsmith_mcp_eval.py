from typing import Any

from app.chat.evals.langsmith_mcp_eval import (
    build_mcp_tool_calls,
    build_mcp_tool_target,
    mcp_connection_evaluator,
    run_mcp_eval_case,
)
from app.chat.evals.langsmith_tool_eval import tool_contract_evaluator
from app.chat.router.intent_router import ChatRoute


async def fake_sequence_runner(url: str, tool_calls: list[tuple[str, dict[str, Any]]]) -> dict[str, Any]:
    del url
    call_results: dict[str, dict[str, Any]] = {}
    for tool_name, arguments in tool_calls:
        if tool_name == "rag_search_tool":
            call_results[tool_name] = {
                "is_error": False,
                "structured_content": {
                    "tool_name": "rag_search_tool",
                    "query": arguments["query"],
                    "top_k": arguments["top_k"],
                    "results": [
                        {
                            "rank": 1,
                            "chunk_id": "wada_prohibited_list_2026_ko:p5:c0",
                            "source_id": "wada_prohibited_list_2026_ko",
                            "title": "금지목록 국제표준",
                            "text": "S0 비승인 약물은 상시 금지입니다. Pseudoephedrine S6 경기기간 중 금지 기준 확인.",
                            "distance": 0.2,
                            "page": 5,
                        }
                    ],
                    "errors": [],
                    "request_id": arguments.get("request_id"),
                },
            }
        elif tool_name == "drug_search_tool":
            call_results[tool_name] = {
                "is_error": False,
                "structured_content": {
                    "tool_name": "drug_search_tool",
                    "query": arguments["query"],
                    "result": {
                        "status": "prohibited_possible",
                        "matched_substances": ["슈도에페드린"],
                        "prohibited_categories": ["S6_120"],
                    },
                    "errors": [],
                    "request_id": arguments.get("request_id"),
                },
            }
        elif tool_name == "pharmacology_info_tool":
            call_results[tool_name] = {
                "is_error": False,
                "structured_content": {
                    "tool_name": "pharmacology_info_tool",
                    "query": arguments["query"],
                    "result": {
                        "status": "found",
                        "substance_name": "pseudoephedrine",
                        "matched_terms": ["슈도에페드린"],
                        "half_life": {"typical_range": "대략 4-8시간", "unit": "hours"},
                    },
                    "errors": [],
                    "request_id": arguments.get("request_id"),
                },
            }

    return {
        "tool_names": ["drug_search_tool", "pharmacology_info_tool", "rag_search_tool"],
        "call_results": call_results,
    }


def test_build_mcp_tool_calls_for_rag_only_case() -> None:
    retrieval_query, final_query, tool_calls = build_mcp_tool_calls(
        query="S0 비승인약물이 뭐야?",
        route=ChatRoute.RAG,
        retrieval_terms=("상시 금지",),
        top_k=3,
        rewrite_enabled=False,
    )

    assert "상시 금지" in final_query
    assert retrieval_query == final_query
    assert [tool_name for tool_name, _arguments in tool_calls] == ["rag_search_tool"]


def test_build_mcp_tool_calls_for_drug_with_rag_and_pharmacology() -> None:
    _retrieval_query, _final_query, tool_calls = build_mcp_tool_calls(
        query="슈도에페드린 반감기가 얼마나 돼?",
        route=ChatRoute.DRUG_SEARCH_WITH_RAG,
        retrieval_terms=("S6",),
        top_k=3,
        rewrite_enabled=True,
    )

    assert [tool_name for tool_name, _arguments in tool_calls] == [
        "rag_search_tool",
        "drug_search_tool",
        "pharmacology_info_tool",
    ]


def test_mcp_tool_target_returns_langsmith_eval_shape() -> None:
    target = build_mcp_tool_target(
        url="http://mcp.test/mcp",
        top_k=3,
        rewrite_enabled=False,
        sequence_runner=fake_sequence_runner,
    )

    outputs = target({"query": "슈도에페드린 반감기가 얼마나 돼?", "retrieval_terms": ["S6"]})

    assert outputs["actual_route"] == "drug_search_with_rag"
    assert outputs["mcp_missing_tools"] == []
    assert outputs["mcp_called_tools"] == ["rag_search_tool", "drug_search_tool", "pharmacology_info_tool"]
    assert outputs["rag_tool_name"] == "rag_search_tool"
    assert outputs["drug_tool_name"] == "drug_search_tool"
    assert outputs["pharmacology_tool_name"] == "pharmacology_info_tool"
    assert outputs["pharmacology_tool_has_half_life"] is True
    assert outputs["source_ids"] == ["wada_prohibited_list_2026_ko"]

    assert mcp_connection_evaluator(outputs, {})["score"] == 1
    assert tool_contract_evaluator(outputs, {})["score"] == 1


def test_run_mcp_eval_case_reports_connection_error() -> None:
    async def failing_sequence_runner(url: str, tool_calls: list[tuple[str, dict[str, Any]]]) -> dict[str, Any]:
        del url, tool_calls
        raise RuntimeError("server unavailable")

    import asyncio

    outputs = asyncio.run(
        run_mcp_eval_case(
            {"query": "S0 비승인약물이 뭐야?"},
            url="http://mcp.test/mcp",
            sequence_runner=failing_sequence_runner,
        )
    )

    assert "RuntimeError" in outputs["error"]
    assert mcp_connection_evaluator(outputs, {})["score"] == 0
