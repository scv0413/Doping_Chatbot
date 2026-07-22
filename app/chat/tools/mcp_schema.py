from typing import Any

from pydantic import BaseModel, Field

from app.chat.tools.schemas import DrugSearchToolRequest, PharmacologyInfoToolRequest, RagSearchRequest


class MCPToolDefinition(BaseModel):
    """MCP-compatible tool metadata used before wiring a concrete MCP server."""

    name: str
    description: str
    input_schema: dict[str, Any] = Field(alias="inputSchema")

    model_config = {"populate_by_name": True}


TOOL_DESCRIPTIONS = {
    "rag_search_tool": (
        "Search anti-doping rule/manual chunks and return cited evidence. "
        "Use for regulation, field procedure, TUE, sample collection, and safety manual questions."
    ),
    "drug_search_tool": (
        "Search a medication or ingredient risk record. Use for product/ingredient questions before medication use. "
        "Do not use the result as a final permission decision without safety context."
    ),
    "pharmacology_info_tool": (
        "Look up pharmacology reference information such as half-life, metabolism, and elimination caveats. "
        "Use only as contextual safety guidance, not as an anti-doping clearance decision."
    ),
}


TOOL_REQUEST_MODELS = {
    "rag_search_tool": RagSearchRequest,
    "drug_search_tool": DrugSearchToolRequest,
    "pharmacology_info_tool": PharmacologyInfoToolRequest,
}


def build_mcp_tool_definition(name: str) -> MCPToolDefinition:
    request_model = TOOL_REQUEST_MODELS[name]
    return MCPToolDefinition(
        name=name,
        description=TOOL_DESCRIPTIONS[name],
        inputSchema=request_model.model_json_schema(),
    )


def get_mcp_tool_definitions() -> list[MCPToolDefinition]:
    return [build_mcp_tool_definition(name) for name in TOOL_REQUEST_MODELS]


def get_mcp_tool_definition(name: str) -> MCPToolDefinition:
    if name not in TOOL_REQUEST_MODELS:
        msg = f"Unknown MCP tool: {name}"
        raise ValueError(msg)
    return build_mcp_tool_definition(name)
