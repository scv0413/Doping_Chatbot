from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from app.chat.tools.mcp_registry import MCPToolDependencies

DEFAULT_MCP_URL = "http://127.0.0.1:8012/mcp"
AsyncMCPToolCaller = Callable[[str, str, dict[str, Any]], Awaitable[dict[str, Any]]]


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
    """Graph-compatible tool executor backed by a streamable HTTP MCP server."""

    def __init__(
        self,
        url: str = DEFAULT_MCP_URL,
        async_caller: AsyncMCPToolCaller = call_mcp_tool,
    ) -> None:
        self.url = url
        self.async_caller = async_caller

    def __call__(
        self,
        name: str,
        arguments: dict[str, Any],
        dependencies: MCPToolDependencies | None = None,
    ) -> dict[str, Any]:
        del dependencies
        ensure_no_running_event_loop()
        return asyncio.run(self.async_caller(self.url, name, arguments))


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
