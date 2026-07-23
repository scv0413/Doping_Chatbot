from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.chat.domain.drug_search.kada_client import search_kada_drugs
from app.chat.domain.drug_search.schemas import DrugSearchInput, DrugSearchResult
from app.chat.domain.pharmacology.schemas import PharmacologyInfoResult
from app.chat.domain.pharmacology.service import search_pharmacology_info
from app.chat.domain.retrieval.retriever import search
from app.chat.domain.retrieval.schemas import RetrievalMatch
from app.chat.tools.drug_search_tool import run_drug_search_tool
from app.chat.tools.mcp_schema import get_mcp_tool_definition, get_mcp_tool_definitions
from app.chat.tools.pharmacology_info_tool import run_pharmacology_info_tool
from app.chat.tools.rag_search_tool import run_rag_search_tool
from app.chat.tools.schemas import DrugSearchToolRequest, PharmacologyInfoToolRequest, RagSearchRequest

RagRetriever = Callable[[str, int], list[RetrievalMatch]]
DrugSearcher = Callable[[DrugSearchInput], DrugSearchResult]
PharmacologySearcher = Callable[[str], PharmacologyInfoResult]


@dataclass(frozen=True)
class MCPToolDependencies:
    rag_retriever: RagRetriever = search
    drug_searcher: DrugSearcher = search_kada_drugs
    pharmacology_searcher: PharmacologySearcher = search_pharmacology_info


def list_mcp_tools() -> list[dict[str, Any]]:
    return [definition.model_dump(by_alias=True) for definition in get_mcp_tool_definitions()]


def get_mcp_tool(name: str) -> dict[str, Any]:
    return get_mcp_tool_definition(name).model_dump(by_alias=True)


def execute_mcp_tool(
    name: str,
    arguments: dict[str, Any],
    dependencies: MCPToolDependencies | None = None,
) -> dict[str, Any]:
    dependencies = dependencies or MCPToolDependencies()

    if name == "rag_search_tool":
        request = RagSearchRequest.model_validate(arguments)
        output = run_rag_search_tool(request, retriever=dependencies.rag_retriever)
        return output.model_dump(mode="json")

    if name == "drug_search_tool":
        request = DrugSearchToolRequest.model_validate(arguments)
        output = run_drug_search_tool(request, drug_searcher=dependencies.drug_searcher)
        return output.model_dump(mode="json")

    if name == "pharmacology_info_tool":
        request = PharmacologyInfoToolRequest.model_validate(arguments)
        output = run_pharmacology_info_tool(request, pharmacology_searcher=dependencies.pharmacology_searcher)
        return output.model_dump(mode="json")

    msg = f"Unknown MCP tool: {name}"
    raise ValueError(msg)
