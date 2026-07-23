from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from app.chat.tools.mcp_registry import MCPToolDependencies, execute_mcp_tool

DEFAULT_MCP_URL = "http://127.0.0.1:8012/mcp"
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_MAX_ATTEMPTS = 2
AsyncMCPToolCaller = Callable[[str, str, dict[str, Any]], Awaitable[dict[str, Any]]]
SyncMCPToolExecutor = Callable[[str, dict[str, Any], MCPToolDependencies | None], dict[str, Any]]


async def call_mcp_tool(url: str, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    async with streamablehttp_client(url) as (read_stream, write_stream, _get_session_id):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments)

    structured_content = result.structuredContent or {}
    if result.isError:
        if structured_content:
            return structured_content
        return build_mcp_client_error_payload(
            name=name,
            message="MCP tool call returned an error without structured content.",
            error_type="MCPToolCallError",
        )

    return structured_content


class MCPHTTPToolExecutor:
    """Graph-compatible tool executor backed by a streamable HTTP MCP server.

    The executor is intentionally resilient: HTTP MCP is tried first, then the
    internal registry executor can be used as a fallback so user-facing graph
    execution does not fail only because the external MCP transport is down.
    """

    def __init__(
        self,
        url: str = DEFAULT_MCP_URL,
        async_caller: AsyncMCPToolCaller = call_mcp_tool,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        fallback_executor: SyncMCPToolExecutor | None = execute_mcp_tool,
    ) -> None:
        if timeout_seconds <= 0:
            msg = "timeout_seconds must be greater than 0."
            raise ValueError(msg)
        if max_attempts < 1:
            msg = "max_attempts must be at least 1."
            raise ValueError(msg)

        self.url = url
        self.async_caller = async_caller
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts
        self.fallback_executor = fallback_executor

    def __call__(
        self,
        name: str,
        arguments: dict[str, Any],
        dependencies: MCPToolDependencies | None = None,
    ) -> dict[str, Any]:
        ensure_no_running_event_loop()

        last_exc: Exception | None = None
        for _attempt in range(self.max_attempts):
            try:
                return asyncio.run(
                    asyncio.wait_for(
                        self.async_caller(self.url, name, arguments),
                        timeout=self.timeout_seconds,
                    )
                )
            except Exception as exc:  # pragma: no cover - exact transport errors are integration-dependent
                last_exc = exc

        if self.fallback_executor is not None:
            return self.fallback_executor(name, arguments, dependencies)

        assert last_exc is not None
        return build_mcp_client_error_payload(
            name=name,
            message=f"MCP HTTP tool call failed after {self.max_attempts} attempt(s): {last_exc}",
            error_type=type(last_exc).__name__,
        )


def ensure_no_running_event_loop() -> None:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return

    msg = (
        "MCPHTTPToolExecutor is synchronous and cannot be used inside an already running event loop. "
        "Use the default registry executor in async API paths, or add an async graph runner."
    )
    raise RuntimeError(msg)


def build_mcp_client_error_payload(name: str, message: str, error_type: str) -> dict[str, Any]:
    return {
        "tool_name": name,
        "errors": [
            {
                "stage": "mcp_http_client",
                "message": message,
                "error_type": error_type,
            }
        ],
    }
