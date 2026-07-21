from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.chat.answer.chain import generate_answer
from app.chat.answer.types import AnswerLLM
from app.chat.drug_search.kada_client import search_kada_drugs
from app.chat.pipeline.chat_pipeline import (
    DrugSearcher,
    QueryRewriter,
    QuestionRouter,
    Retriever,
    build_pipeline_error,
    build_retrieval_query,
    normalize_pipeline_input,
    run_drug_search_step,
    run_query_rewrite_step,
    run_retrieval_step,
    should_run_drug_search,
    should_run_retrieval,
)
from app.chat.retrieval.query_rewriter import rewrite_query
from app.chat.retrieval.retriever import search
from app.chat.router.intent_router import route_question
from app.chat.graph.state import ChatGraphState

DEFAULT_TOP_K = 3


@dataclass(frozen=True)
class ChatGraphDependencies:
    router: QuestionRouter = route_question
    drug_searcher: DrugSearcher = search_kada_drugs
    retriever: Retriever = search
    query_rewriter: QueryRewriter = rewrite_query
    llm: AnswerLLM | None = None


def build_route_node(dependencies: ChatGraphDependencies) -> Callable[[ChatGraphState], dict[str, Any]]:
    def node(state: ChatGraphState) -> dict[str, Any]:
        search_input = normalize_pipeline_input(state["query"])
        decision = dependencies.router(search_input.query)
        return {
            "search_input": search_input,
            "decision": decision,
            "errors": list(state.get("errors", [])),
        }

    return node


def build_drug_search_node(dependencies: ChatGraphDependencies) -> Callable[[ChatGraphState], dict[str, Any]]:
    def node(state: ChatGraphState) -> dict[str, Any]:
        errors = list(state.get("errors", []))
        drug_result = run_drug_search_step(
            search_input=state["search_input"],
            drug_searcher=dependencies.drug_searcher,
            errors=errors,
        )
        return {"drug_result": drug_result, "errors": errors}

    return node


def build_rewrite_node(dependencies: ChatGraphDependencies) -> Callable[[ChatGraphState], dict[str, Any]]:
    def node(state: ChatGraphState) -> dict[str, Any]:
        errors = list(state.get("errors", []))
        retrieval_query = build_retrieval_query(
            search_input=state["search_input"],
            decision=state["decision"],
            drug_result=state.get("drug_result"),
        )
        rewritten_query = run_query_rewrite_step(
            query=retrieval_query,
            query_rewriter=dependencies.query_rewriter,
            errors=errors,
        )
        return {
            "retrieval_query": retrieval_query,
            "rewritten_query": rewritten_query,
            "errors": errors,
        }

    return node


def build_retrieve_node(dependencies: ChatGraphDependencies) -> Callable[[ChatGraphState], dict[str, Any]]:
    def node(state: ChatGraphState) -> dict[str, Any]:
        errors = list(state.get("errors", []))
        top_k = int(state.get("top_k", DEFAULT_TOP_K))
        retrieval_matches = run_retrieval_step(
            query=state["rewritten_query"] or "",
            top_k=top_k,
            retriever=dependencies.retriever,
            errors=errors,
        )
        return {"retrieval_matches": retrieval_matches, "errors": errors}

    return node


def build_answer_node(dependencies: ChatGraphDependencies) -> Callable[[ChatGraphState], dict[str, Any]]:
    def node(state: ChatGraphState) -> dict[str, Any]:
        search_input = state["search_input"]
        answer = generate_answer(
            query=search_input.query,
            decision=state["decision"],
            drug_result=state.get("drug_result"),
            retrieval_matches=state.get("retrieval_matches", []),
            llm=dependencies.llm,
            use_llm=bool(state.get("use_llm", True)),
        )
        return {"answer": answer}

    return node


def exit_node(state: ChatGraphState) -> dict[str, Any]:
    if state.get("answer"):
        return {}

    errors = list(state.get("errors", []))
    errors.append(
        build_pipeline_error(
            stage="exit",
            exc=RuntimeError("Graph finished without an answer."),
        )
    )
    return {
        "answer": "답변 생성에 실패했습니다. 질문을 다시 시도하거나 공식 자료를 확인하세요.",
        "errors": errors,
    }


def next_after_route(state: ChatGraphState) -> str:
    if should_run_drug_search(state["decision"]):
        return "drug_search"
    return "rewrite"


def next_after_drug_search(state: ChatGraphState) -> str:
    if should_run_retrieval(state["decision"]):
        return "rewrite"
    return "answer"
