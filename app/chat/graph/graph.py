from typing import Any, cast

from langgraph.graph import END, START, StateGraph

from app.chat.answer.types import AnswerLLM
from app.chat.drug_search.schemas import DrugSearchInput
from app.chat.pipeline.chat_pipeline import (
    ChatPipelineResult,
    DrugSearcher,
    PharmacologySearcher,
    QueryRewriter,
    QuestionRouter,
    Retriever,
)
from app.chat.graph.nodes import (
    ChatGraphDependencies,
    build_answer_node,
    build_drug_search_node,
    build_pharmacology_node,
    build_retrieve_node,
    build_rewrite_node,
    build_route_node,
    exit_node,
    next_after_drug_search,
    next_after_pharmacology,
    next_after_retrieve,
    next_after_route,
    retry_rewrite_node,
)
from app.chat.graph.state import ChatGraphState

DEFAULT_RECURSION_LIMIT = 10


def compile_chat_graph(dependencies: ChatGraphDependencies | None = None) -> Any:
    dependencies = dependencies or ChatGraphDependencies()

    builder = StateGraph(ChatGraphState)
    builder.add_node("route", build_route_node(dependencies))
    builder.add_node("drug_search", build_drug_search_node(dependencies))
    builder.add_node("pharmacology", build_pharmacology_node(dependencies))
    builder.add_node("rewrite", build_rewrite_node(dependencies))
    builder.add_node("retrieve", build_retrieve_node(dependencies))
    builder.add_node("retry_rewrite", retry_rewrite_node)
    builder.add_node("answer", build_answer_node(dependencies))
    builder.add_node("exit", exit_node)

    builder.add_edge(START, "route")
    builder.add_conditional_edges(
        "route",
        next_after_route,
        {"drug_search": "drug_search", "pharmacology": "pharmacology", "rewrite": "rewrite"},
    )
    builder.add_conditional_edges(
        "drug_search",
        next_after_drug_search,
        {"pharmacology": "pharmacology", "rewrite": "rewrite", "answer": "answer"},
    )
    builder.add_conditional_edges(
        "pharmacology",
        next_after_pharmacology,
        {"rewrite": "rewrite", "answer": "answer"},
    )
    builder.add_edge("rewrite", "retrieve")
    builder.add_conditional_edges(
        "retrieve",
        next_after_retrieve,
        {"retry_rewrite": "retry_rewrite", "answer": "answer"},
    )
    builder.add_edge("retry_rewrite", "retrieve")
    builder.add_edge("answer", "exit")
    builder.add_edge("exit", END)
    return builder.compile()


def run_chat_graph(
    search_input: DrugSearchInput | str,
    top_k: int = 3,
    use_llm: bool = True,
    llm: AnswerLLM | None = None,
    router: QuestionRouter | None = None,
    drug_searcher: DrugSearcher | None = None,
    retriever: Retriever | None = None,
    query_rewriter: QueryRewriter | None = None,
    pharmacology_searcher: PharmacologySearcher | None = None,
    recursion_limit: int = DEFAULT_RECURSION_LIMIT,
) -> ChatPipelineResult:
    query = search_input.query if isinstance(search_input, DrugSearchInput) else search_input
    initial_state: ChatGraphState = {
        "query": query,
        "top_k": top_k,
        "use_llm": use_llm,
        "retrieval_attempts": 0,
        "retrieval_retry_reason": None,
        "errors": [],
    }

    dependency_kwargs: dict[str, Any] = {"llm": llm}
    if router is not None:
        dependency_kwargs["router"] = router
    if drug_searcher is not None:
        dependency_kwargs["drug_searcher"] = drug_searcher
    if retriever is not None:
        dependency_kwargs["retriever"] = retriever
    if query_rewriter is not None:
        dependency_kwargs["query_rewriter"] = query_rewriter
    if pharmacology_searcher is not None:
        dependency_kwargs["pharmacology_searcher"] = pharmacology_searcher

    graph = compile_chat_graph(ChatGraphDependencies(**dependency_kwargs))
    final_state = cast(
        ChatGraphState,
        graph.invoke(initial_state, config={"recursion_limit": recursion_limit}),
    )
    return state_to_pipeline_result(final_state)


def state_to_pipeline_result(state: ChatGraphState) -> ChatPipelineResult:
    return ChatPipelineResult(
        search_input=state["search_input"],
        decision=state["decision"],
        drug_result=state.get("drug_result"),
        drug_search_tool_output=state.get("drug_search_tool_output"),
        pharmacology_result=state.get("pharmacology_result"),
        pharmacology_info_tool_output=state.get("pharmacology_info_tool_output"),
        retrieval_query=state.get("retrieval_query"),
        rewritten_query=state.get("rewritten_query"),
        rag_search_output=state.get("rag_search_output"),
        retrieval_matches=state.get("retrieval_matches", []),
        retrieval_attempts=state.get("retrieval_attempts", 0),
        retrieval_retry_reason=state.get("retrieval_retry_reason"),
        answer=state.get("answer", ""),
        errors=state.get("errors", []),
    )
