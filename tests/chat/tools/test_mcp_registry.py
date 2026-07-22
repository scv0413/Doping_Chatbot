import pytest

from app.chat.drug_search.schemas import DrugRiskStatus, DrugSearchInput, DrugSearchResult
from app.chat.pharmacology.schemas import PharmacologyInfoResult, PharmacologyInfoStatus
from app.chat.retrieval.schemas import RetrievalMatch, RetrievalMetadata
from app.chat.tools import MCPToolDependencies, execute_mcp_tool, get_mcp_tool, list_mcp_tools


def fake_retriever(query: str, top_k: int) -> list[RetrievalMatch]:
    return [
        RetrievalMatch(
            rank=1,
            chunk_id="wada_prohibited_list_2026_ko:p5:c0",
            distance=0.1,
            metadata=RetrievalMetadata(
                source_id="wada_prohibited_list_2026_ko",
                title="WADA Prohibited List 2026",
                page=5,
                chunk_id="wada_prohibited_list_2026_ko:p5:c0",
            ),
            text=f"query={query}, top_k={top_k}, S0 비승인약물",
        )
    ]


def fake_drug_searcher(search_input: DrugSearchInput) -> DrugSearchResult:
    return DrugSearchResult(
        status=DrugRiskStatus.NEEDS_VERIFICATION,
        input=search_input,
        matched_substances=[search_input.ingredient_name or search_input.query],
        recommended_action="제품명과 성분명을 확인하세요.",
    )


def fake_pharmacology_searcher(query: str) -> PharmacologyInfoResult:
    return PharmacologyInfoResult(
        status=PharmacologyInfoStatus.NOT_FOUND,
        query=query,
        recommended_action="정확한 성분명을 확인하세요.",
    )


def test_list_mcp_tools_exposes_three_tool_schemas() -> None:
    tools = list_mcp_tools()
    names = {tool["name"] for tool in tools}

    assert names == {"rag_search_tool", "drug_search_tool", "pharmacology_info_tool"}
    rag_tool = get_mcp_tool("rag_search_tool")
    assert rag_tool["inputSchema"]["properties"]["query"]["minLength"] == 1
    assert rag_tool["inputSchema"]["properties"]["top_k"]["maximum"] == 10


def test_execute_mcp_rag_search_tool_returns_json_output() -> None:
    output = execute_mcp_tool(
        "rag_search_tool",
        {"query": "S0 비승인약물이 뭐야?", "top_k": 3, "request_id": "mcp-rag-1"},
        dependencies=MCPToolDependencies(rag_retriever=fake_retriever),
    )

    assert output["tool_name"] == "rag_search_tool"
    assert output["request_id"] == "mcp-rag-1"
    assert output["errors"] == []
    assert output["results"][0]["chunk_id"] == "wada_prohibited_list_2026_ko:p5:c0"


def test_execute_mcp_drug_and_pharmacology_tools_return_json_outputs() -> None:
    dependencies = MCPToolDependencies(
        drug_searcher=fake_drug_searcher,
        pharmacology_searcher=fake_pharmacology_searcher,
    )

    drug_output = execute_mcp_tool(
        "drug_search_tool",
        {"query": "타이레놀 먹어도 돼?", "ingredient_name": "acetaminophen"},
        dependencies=dependencies,
    )
    pharmacology_output = execute_mcp_tool(
        "pharmacology_info_tool",
        {"query": "슈도에페드린 반감기가 얼마나 돼?"},
        dependencies=dependencies,
    )

    assert drug_output["tool_name"] == "drug_search_tool"
    assert drug_output["result"]["status"] == "needs_verification"
    assert pharmacology_output["tool_name"] == "pharmacology_info_tool"
    assert pharmacology_output["result"]["status"] == "not_found"


def test_execute_mcp_tool_rejects_unknown_tool() -> None:
    with pytest.raises(ValueError, match="Unknown MCP tool"):
        execute_mcp_tool("missing_tool", {"query": "S0"})
