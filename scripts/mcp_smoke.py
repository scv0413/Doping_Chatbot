from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

DEFAULT_URL = "http://127.0.0.1:8012/mcp"
EXPECTED_TOOLS = {"rag_search_tool", "drug_search_tool", "pharmacology_info_tool"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke test the doping chatbot MCP server.")
    parser.add_argument("--url", default=DEFAULT_URL, help="Streamable HTTP MCP endpoint URL.")
    parser.add_argument(
        "--call-pharmacology",
        action="store_true",
        help="Also call pharmacology_info_tool with a harmless not-found query.",
    )
    return parser.parse_args()


async def run_smoke(url: str, call_pharmacology: bool = False) -> dict[str, Any]:
    async with streamablehttp_client(url) as (read_stream, write_stream, get_session_id):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools_response = await session.list_tools()
            tool_names = sorted(tool.name for tool in tools_response.tools)
            missing_tools = sorted(EXPECTED_TOOLS - set(tool_names))

            summary: dict[str, Any] = {
                "url": url,
                "session_id": get_session_id(),
                "tool_names": tool_names,
                "missing_tools": missing_tools,
                "ok": not missing_tools,
            }

            if call_pharmacology:
                call_result = await session.call_tool(
                    "pharmacology_info_tool",
                    {"query": "처음 보는 성분 반감기 알려줘", "request_id": "mcp-smoke"},
                )
                summary["pharmacology_call"] = {
                    "is_error": call_result.isError,
                    "structured_content": call_result.structuredContent,
                }
                summary["ok"] = summary["ok"] and not call_result.isError

            return summary


def main() -> None:
    args = parse_args()
    result = asyncio.run(run_smoke(args.url, args.call_pharmacology))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
