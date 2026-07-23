from typing import Any

import pytest

from app.chat.orchestration.graph.nodes import ChatGraphDependencies, build_retrieve_node, build_rewrite_node, build_route_node
from app.chat.mcp.client_executor import MCPHTTPToolExecutor, build_mcp_client_error_payload


async def fake_async_caller(url: str, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    assert url == "http://mcp.test/mcp"
    assert name == "rag_search_tool"
    return {
        "tool_name": "rag_search_tool",
        "query": arguments["query"],
        "top_k": arguments["top_k"],
        "results": [
            {
                "rank": 1,
                "chunk_id": "field_response_manual:s1:c0",
                "source_id": "field_response_manual",
                "title": "현장 대응 매뉴얼",
                "text": "검사관 신분 확인, 기록, 동석 요청.",
                "distance": 0.2,
                "page": 1,
            }
        ],
        "errors": [],
        "request_id": arguments.get("request_id"),
    }


def identity_rewriter(query: str) -> str:
    return query


def test_mcp_http_tool_executor_can_drive_graph_retrieve_node() -> None:
    executor = MCPHTTPToolExecutor(url="http://mcp.test/mcp", async_caller=fake_async_caller)
    dependencies = ChatGraphDependencies(
        query_rewriter=identity_rewriter,
        tool_executor=executor,
    )
    state = {
        "query": "도핑 검사관 신분이 불분명하면 어떻게 확인해야 해?",
        "top_k": 3,
        "use_llm": False,
        "errors": [],
    }

    state.update(build_route_node(dependencies)(state))
    state.update(build_rewrite_node(dependencies)(state))
    state.update(build_retrieve_node(dependencies)(state))

    assert state["rag_search_output"].tool_name == "rag_search_tool"
    assert state["retrieval_matches"][0].source_id == "field_response_manual"
    assert state["errors"] == []


def test_build_mcp_client_error_payload_matches_tool_error_shape() -> None:
    payload = build_mcp_client_error_payload(
        name="rag_search_tool",
        message="connection failed",
        error_type="ConnectError",
    )

    assert payload == {
        "tool_name": "rag_search_tool",
        "errors": [
            {
                "stage": "mcp_http_client",
                "message": "connection failed",
                "error_type": "ConnectError",
            }
        ],
    }


def test_mcp_http_tool_executor_rejects_running_event_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.chat.mcp.client_executor.asyncio.get_running_loop", lambda: object())
    executor = MCPHTTPToolExecutor(url="http://mcp.test/mcp", async_caller=fake_async_caller)

    with pytest.raises(RuntimeError, match="cannot be used inside an already running event loop"):
        executor("rag_search_tool", {"query": "S0", "top_k": 3})


async def failing_async_caller(url: str, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    del url, name, arguments
    raise TimeoutError("mcp timeout")


def test_mcp_http_tool_executor_retries_before_success() -> None:
    calls = {"count": 0}

    async def flaky_async_caller(url: str, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        calls["count"] += 1
        if calls["count"] == 1:
            raise TimeoutError("first timeout")
        return await fake_async_caller(url, name, arguments)

    executor = MCPHTTPToolExecutor(
        url="http://mcp.test/mcp",
        async_caller=flaky_async_caller,
        max_attempts=2,
        fallback_executor=None,
    )

    output = executor("rag_search_tool", {"query": "S0", "top_k": 3})

    assert calls["count"] == 2
    assert output["tool_name"] == "rag_search_tool"
    assert output["errors"] == []


def test_mcp_http_tool_executor_falls_back_after_failed_attempts() -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    def fallback_executor(name, arguments, dependencies):
        calls.append((name, arguments))
        assert dependencies is not None
        return {
            "tool_name": name,
            "query": arguments["query"],
            "top_k": arguments["top_k"],
            "results": [],
            "errors": [],
            "request_id": arguments.get("request_id"),
        }

    executor = MCPHTTPToolExecutor(
        url="http://mcp.test/mcp",
        async_caller=failing_async_caller,
        max_attempts=2,
        fallback_executor=fallback_executor,
    )

    output = executor("rag_search_tool", {"query": "S0", "top_k": 3}, dependencies=object())

    assert calls == [("rag_search_tool", {"query": "S0", "top_k": 3})]
    assert output["tool_name"] == "rag_search_tool"
    assert output["errors"] == []


def test_mcp_http_tool_executor_returns_error_payload_without_fallback() -> None:
    executor = MCPHTTPToolExecutor(
        url="http://mcp.test/mcp",
        async_caller=failing_async_caller,
        max_attempts=2,
        fallback_executor=None,
    )

    output = executor("rag_search_tool", {"query": "S0", "top_k": 3})

    assert output["tool_name"] == "rag_search_tool"
    assert output["errors"][0]["stage"] == "mcp_http_client"
    assert output["errors"][0]["error_type"] == "TimeoutError"
    assert "2 attempt" in output["errors"][0]["message"]


def test_mcp_http_tool_executor_validates_policy_values() -> None:
    with pytest.raises(ValueError, match="timeout_seconds"):
        MCPHTTPToolExecutor(timeout_seconds=0)

    with pytest.raises(ValueError, match="max_attempts"):
        MCPHTTPToolExecutor(max_attempts=0)
