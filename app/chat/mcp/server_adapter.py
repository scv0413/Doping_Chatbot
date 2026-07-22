import json
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.chat.tools.mcp_registry import MCPToolDependencies, execute_mcp_tool, list_mcp_tools


class MCPContent(BaseModel):
    type: str = "text"
    text: str


class MCPListToolsResponse(BaseModel):
    tools: list[dict[str, Any]] = Field(default_factory=list)


class MCPCallToolResponse(BaseModel):
    content: list[MCPContent]
    structured_content: dict[str, Any] | None = Field(default=None, alias="structuredContent")
    is_error: bool = Field(default=False, alias="isError")

    model_config = {"populate_by_name": True}


def list_tools() -> MCPListToolsResponse:
    return MCPListToolsResponse(tools=list_mcp_tools())


def call_tool(
    name: str,
    arguments: dict[str, Any],
    dependencies: MCPToolDependencies | None = None,
) -> MCPCallToolResponse:
    try:
        output = execute_mcp_tool(name=name, arguments=arguments, dependencies=dependencies)
    except (ValidationError, ValueError) as exc:
        error_payload = build_adapter_error_payload(name=name, exc=exc)
        return MCPCallToolResponse(
            content=[MCPContent(text=json.dumps(error_payload, ensure_ascii=False))],
            structuredContent=error_payload,
            isError=True,
        )

    is_error = bool(output.get("errors"))
    return MCPCallToolResponse(
        content=[MCPContent(text=json.dumps(output, ensure_ascii=False))],
        structuredContent=output,
        isError=is_error,
    )


def build_adapter_error_payload(name: str, exc: Exception) -> dict[str, Any]:
    return {
        "tool_name": name,
        "errors": [
            {
                "stage": "mcp_adapter",
                "message": str(exc),
                "error_type": type(exc).__name__,
            }
        ],
    }
