from app.chat.domain.drug_search.schemas import DrugSearchInput, DrugSearchResult, DrugRiskStatus
from app.chat.mcp import call_tool, list_tools
from app.chat.domain.retrieval.schemas import RetrievalMatch, RetrievalMetadata
from app.chat.tools import MCPToolDependencies


def fake_retriever(query: str, top_k: int) -> list[RetrievalMatch]:
    return [
        RetrievalMatch(
            rank=1,
            chunk_id="manual:p1:c0",
            distance=0.2,
            metadata=RetrievalMetadata(
                source_id="manual",
                title="Manual",
                chunk_id="manual:p1:c0",
            ),
            text=f"{query} top_k={top_k}",
        )
    ]


def fake_drug_searcher(search_input: DrugSearchInput) -> DrugSearchResult:
    return DrugSearchResult(
        status=DrugRiskStatus.NEEDS_VERIFICATION,
        input=search_input,
        recommended_action="제품명과 성분명을 확인하세요.",
    )


def test_mcp_adapter_lists_tool_definitions() -> None:
    response = list_tools()
    payload = response.model_dump(mode="json")

    assert {tool["name"] for tool in payload["tools"]} == {
        "rag_search_tool",
        "drug_search_tool",
        "pharmacology_info_tool",
    }
    assert all("inputSchema" in tool for tool in payload["tools"])


def test_mcp_adapter_calls_rag_tool_with_structured_content() -> None:
    response = call_tool(
        "rag_search_tool",
        {"query": "S0 비승인약물이 뭐야?", "top_k": 3},
        dependencies=MCPToolDependencies(rag_retriever=fake_retriever),
    )
    payload = response.model_dump(mode="json", by_alias=True)

    assert payload["isError"] is False
    assert payload["structuredContent"]["tool_name"] == "rag_search_tool"
    assert payload["structuredContent"]["results"][0]["chunk_id"] == "manual:p1:c0"
    assert payload["content"][0]["type"] == "text"
    assert "rag_search_tool" in payload["content"][0]["text"]


def test_mcp_adapter_marks_tool_runtime_errors_as_is_error() -> None:
    def broken_retriever(query: str, top_k: int) -> list[RetrievalMatch]:
        raise RuntimeError("vector store unavailable")

    response = call_tool(
        "rag_search_tool",
        {"query": "S0", "top_k": 3},
        dependencies=MCPToolDependencies(rag_retriever=broken_retriever),
    )
    payload = response.model_dump(mode="json", by_alias=True)

    assert payload["isError"] is True
    assert payload["structuredContent"]["errors"][0]["error_type"] == "RuntimeError"


def test_mcp_adapter_returns_adapter_error_for_invalid_arguments() -> None:
    response = call_tool("rag_search_tool", {"query": "S0", "top_k": 0})
    payload = response.model_dump(mode="json", by_alias=True)

    assert payload["isError"] is True
    assert payload["structuredContent"]["tool_name"] == "rag_search_tool"
    assert payload["structuredContent"]["errors"][0]["stage"] == "mcp_adapter"
    assert payload["structuredContent"]["errors"][0]["error_type"] == "ValidationError"


def test_mcp_adapter_returns_adapter_error_for_unknown_tool() -> None:
    response = call_tool("missing_tool", {"query": "S0"})
    payload = response.model_dump(mode="json", by_alias=True)

    assert payload["isError"] is True
    assert payload["structuredContent"]["tool_name"] == "missing_tool"
    assert payload["structuredContent"]["errors"][0]["error_type"] == "ValueError"
