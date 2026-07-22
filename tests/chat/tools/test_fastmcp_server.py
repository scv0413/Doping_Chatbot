import asyncio

from app.chat.mcp.fastmcp_server import (
    SERVER_HOST,
    SERVER_NAME,
    SERVER_PORT,
    create_mcp_server,
    tool_structured_content,
)


def test_create_fastmcp_server_registers_three_tools() -> None:
    server = create_mcp_server()
    tools = asyncio.run(server.list_tools())
    names = {tool.name for tool in tools}

    assert server.name == SERVER_NAME
    assert server.settings.host == SERVER_HOST
    assert server.settings.port == SERVER_PORT
    assert server.settings.stateless_http is True
    assert server.settings.json_response is True
    assert server.settings.streamable_http_path == "/mcp"
    assert names == {"rag_search_tool", "drug_search_tool", "pharmacology_info_tool"}


def test_fastmcp_tool_structured_content_uses_adapter_core() -> None:
    output = tool_structured_content(
        "pharmacology_info_tool",
        {"query": "처음 보는 성분 반감기 알려줘", "request_id": "mcp-test-1"},
    )

    assert output["tool_name"] == "pharmacology_info_tool"
    assert output["request_id"] == "mcp-test-1"
    assert output["result"]["status"] == "not_found"
    assert output["errors"] == []


def test_fastmcp_tool_structured_content_wraps_adapter_errors() -> None:
    output = tool_structured_content("rag_search_tool", {"query": "S0", "top_k": 0})

    assert output["tool_name"] == "rag_search_tool"
    assert output["errors"][0]["stage"] == "mcp_adapter"
