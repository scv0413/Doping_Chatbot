"""Tool contracts for future LangGraph agent and MCP exposure."""

from app.chat.tools.drug_search_tool import run_drug_search_tool
from app.chat.tools.mcp_registry import MCPToolDependencies, execute_mcp_tool, get_mcp_tool, list_mcp_tools
from app.chat.tools.mcp_schema import MCPToolDefinition, get_mcp_tool_definitions
from app.chat.tools.pharmacology_info_tool import run_pharmacology_info_tool
from app.chat.tools.rag_search_tool import run_rag_search_tool
from app.chat.tools.schemas import DrugSearchToolOutput, DrugSearchToolRequest, PharmacologyInfoToolOutput, PharmacologyInfoToolRequest, RagSearchRequest, RagSearchResult, RagSearchToolOutput

__all__ = [
    "DrugSearchToolOutput",
    "DrugSearchToolRequest",
    "MCPToolDefinition",
    "MCPToolDependencies",
    "PharmacologyInfoToolOutput",
    "PharmacologyInfoToolRequest",
    "RagSearchRequest",
    "RagSearchResult",
    "RagSearchToolOutput",
    "execute_mcp_tool",
    "get_mcp_tool",
    "get_mcp_tool_definitions",
    "list_mcp_tools",
    "run_drug_search_tool",
    "run_pharmacology_info_tool",
    "run_rag_search_tool",
]
