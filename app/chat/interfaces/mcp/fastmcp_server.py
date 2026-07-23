from typing import Any

from mcp.server.fastmcp import FastMCP

from app.chat.interfaces.mcp.server_adapter import call_tool

SERVER_NAME = "doping-chatbot-mcp"
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8012
SERVER_INSTRUCTIONS = (
    "Tools for anti-doping evidence retrieval, medication risk lookup, and pharmacology safety context. "
    "Tool outputs are evidence/context only and must not be treated as final medical, legal, or anti-doping clearance."
)


def create_mcp_server() -> FastMCP:
    mcp = FastMCP(
        name=SERVER_NAME,
        instructions=SERVER_INSTRUCTIONS,
        host=SERVER_HOST,
        port=SERVER_PORT,
        stateless_http=True,
        json_response=True,
    )

    @mcp.tool(
        name="rag_search_tool",
        description=(
            "Search anti-doping rule/manual chunks and return cited evidence. "
            "Use for regulation, field procedure, TUE, sample collection, and safety manual questions."
        ),
        structured_output=True,
    )
    def rag_search_tool(query: str, top_k: int = 3, request_id: str | None = None) -> dict[str, Any]:
        """Search anti-doping source chunks and return cited evidence."""
        return tool_structured_content(
            "rag_search_tool",
            {"query": query, "top_k": top_k, "request_id": request_id},
        )

    @mcp.tool(
        name="drug_search_tool",
        description=(
            "Search a medication or ingredient risk record. Use for product/ingredient questions before medication use. "
            "Do not use as a final permission decision without safety context."
        ),
        structured_output=True,
    )
    def drug_search_tool(
        query: str,
        product_name: str | None = None,
        ingredient_name: str | None = None,
        competition_period: str = "unknown",
        route: str | None = None,
        sport: str | None = None,
        dose: str | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """Look up medication or ingredient risk context."""
        return tool_structured_content(
            "drug_search_tool",
            {
                "query": query,
                "product_name": product_name,
                "ingredient_name": ingredient_name,
                "competition_period": competition_period,
                "route": route,
                "sport": sport,
                "dose": dose,
                "request_id": request_id,
            },
        )

    @mcp.tool(
        name="pharmacology_info_tool",
        description=(
            "Look up pharmacology reference information such as half-life, metabolism, and elimination caveats. "
            "Use only as contextual safety guidance, not as an anti-doping clearance decision."
        ),
        structured_output=True,
    )
    def pharmacology_info_tool(query: str, request_id: str | None = None) -> dict[str, Any]:
        """Look up half-life and pharmacology context."""
        return tool_structured_content(
            "pharmacology_info_tool",
            {"query": query, "request_id": request_id},
        )

    return mcp


def tool_structured_content(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    response = call_tool(name, arguments)
    payload = response.structured_content or {}
    if response.is_error:
        return {
            "tool_name": name,
            "errors": payload.get("errors", []),
        }
    return payload


mcp = create_mcp_server()


def main() -> None:
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
