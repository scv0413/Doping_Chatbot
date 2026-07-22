from typing import Any

from pydantic import BaseModel, Field

from app.chat.drug_search.schemas import DrugSearchResult
from app.chat.pharmacology.service import should_run_pharmacology_info
from app.chat.pipeline.chat_pipeline import (
    QueryRewriter,
    build_retrieval_query,
    normalize_pipeline_input,
    should_run_drug_search,
    should_run_retrieval,
)
from app.chat.retrieval.query_rewriter import rewrite_query
from app.chat.router.intent_router import route_question
from app.chat.tools.mcp_registry import MCPToolDependencies, execute_mcp_tool


class ToolCallRecord(BaseModel):
    tool_name: str
    arguments: dict[str, Any]
    output: dict[str, Any]


class AgentToolRunResult(BaseModel):
    query: str
    route: str
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)

    @property
    def called_tool_names(self) -> list[str]:
        return [call.tool_name for call in self.tool_calls]


def run_agent_tool_plan(
    query: str,
    top_k: int = 3,
    dependencies: MCPToolDependencies | None = None,
    query_rewriter: QueryRewriter = rewrite_query,
) -> AgentToolRunResult:
    """Run a controlled multi-tool plan using MCP-compatible tool boundaries.

    This is not a free-form LLM agent. It is the first agentic step: route the
    question, call only the tools required by that route/intent, and keep every
    tool input/output traceable.
    """

    dependencies = dependencies or MCPToolDependencies()
    search_input = normalize_pipeline_input(query)
    decision = route_question(search_input.query)
    tool_calls: list[ToolCallRecord] = []
    drug_result: DrugSearchResult | None = None

    if should_run_drug_search(decision):
        arguments = {
            "query": search_input.query,
            "product_name": search_input.product_name,
            "ingredient_name": search_input.ingredient_name,
            "competition_period": search_input.competition_period.value,
            "route": search_input.route.value if search_input.route else None,
            "sport": search_input.sport,
            "dose": search_input.dose,
        }
        output = execute_mcp_tool("drug_search_tool", arguments, dependencies=dependencies)
        tool_calls.append(ToolCallRecord(tool_name="drug_search_tool", arguments=arguments, output=output))
        if output.get("result"):
            drug_result = DrugSearchResult.model_validate(output["result"])

    if should_run_pharmacology_info(search_input.query):
        arguments = {"query": search_input.query}
        output = execute_mcp_tool("pharmacology_info_tool", arguments, dependencies=dependencies)
        tool_calls.append(ToolCallRecord(tool_name="pharmacology_info_tool", arguments=arguments, output=output))

    if should_run_retrieval(decision):
        retrieval_query = build_retrieval_query(
            search_input=search_input,
            decision=decision,
            drug_result=drug_result,
        )
        arguments = {
            "query": query_rewriter(retrieval_query),
            "top_k": top_k,
        }
        output = execute_mcp_tool("rag_search_tool", arguments, dependencies=dependencies)
        tool_calls.append(ToolCallRecord(tool_name="rag_search_tool", arguments=arguments, output=output))

    return AgentToolRunResult(
        query=search_input.query,
        route=decision.route.value,
        tool_calls=tool_calls,
    )
