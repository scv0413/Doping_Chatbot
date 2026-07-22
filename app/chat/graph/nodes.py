from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.chat.answer.chain import generate_answer
from app.chat.answer.types import AnswerLLM
from app.chat.drug_search.kada_client import search_kada_drugs
from app.chat.pharmacology.service import search_pharmacology_info, should_run_pharmacology_info
from app.chat.drug_search.schemas import build_needs_verification_result
from app.chat.pipeline.chat_pipeline import (
    DrugSearcher,
    PharmacologySearcher,
    QueryRewriter,
    QuestionRouter,
    Retriever,
    build_pipeline_error,
    build_retrieval_query,
    normalize_pipeline_input,
    run_pharmacology_step,
    run_query_rewrite_step,
    should_run_drug_search,
    should_run_retrieval,
)
from app.chat.retrieval.query_rewriter import rewrite_query
from app.chat.retrieval.retriever import search
from app.chat.router.intent_router import route_question
from app.chat.tools.drug_search_tool import run_drug_search_tool
from app.chat.tools.rag_search_tool import run_rag_search_tool, tool_output_to_retrieval_matches
from app.chat.tools.schemas import DrugSearchToolRequest, RagSearchRequest, ToolError
from app.chat.graph.state import ChatGraphState

DEFAULT_TOP_K = 3
MAX_RETRIEVAL_ATTEMPTS = 2
MIN_RETRIEVAL_CONTEXT_CHARS = 80
MAX_ACCEPTABLE_BEST_DISTANCE = 0.85


@dataclass(frozen=True)
class ChatGraphDependencies:
    router: QuestionRouter = route_question
    drug_searcher: DrugSearcher = search_kada_drugs
    retriever: Retriever = search
    query_rewriter: QueryRewriter = rewrite_query
    pharmacology_searcher: PharmacologySearcher = search_pharmacology_info
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
        search_input = state["search_input"]
        drug_search_tool_output = run_drug_search_tool(
            DrugSearchToolRequest(
                query=search_input.query,
                product_name=search_input.product_name,
                ingredient_name=search_input.ingredient_name,
                competition_period=search_input.competition_period,
                route=search_input.route,
                sport=search_input.sport,
                dose=search_input.dose,
            ),
            drug_searcher=dependencies.drug_searcher,
        )
        errors.extend(tool_errors_to_pipeline_errors(drug_search_tool_output.errors, stage="drug_search"))
        drug_result = drug_search_tool_output.result or build_needs_verification_result(
            search_input=search_input,
            recommended_action="약물검색 중 오류가 발생했습니다. 제품명과 성분명을 확인한 뒤 다시 조회하거나 KADA 공식 자료를 확인하세요.",
        )
        return {
            "drug_result": drug_result,
            "drug_search_tool_output": drug_search_tool_output,
            "errors": errors,
        }

    return node


def build_pharmacology_node(dependencies: ChatGraphDependencies) -> Callable[[ChatGraphState], dict[str, Any]]:
    def node(state: ChatGraphState) -> dict[str, Any]:
        errors = list(state.get("errors", []))
        search_input = state["search_input"]
        pharmacology_result = run_pharmacology_step(
            query=search_input.query,
            pharmacology_searcher=dependencies.pharmacology_searcher,
            errors=errors,
        )
        return {"pharmacology_result": pharmacology_result, "errors": errors}

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
        rag_search_output = run_rag_search_tool(
            RagSearchRequest(
                query=state["rewritten_query"] or "",
                top_k=top_k,
            ),
            retriever=dependencies.retriever,
        )
        errors.extend(tool_errors_to_pipeline_errors(rag_search_output.errors, stage="retrieval"))
        retrieval_matches = tool_output_to_retrieval_matches(rag_search_output)
        retry_reason = assess_retrieval_retry_reason(retrieval_matches)
        return {
            "rag_search_output": rag_search_output,
            "retrieval_matches": retrieval_matches,
            "retrieval_attempts": int(state.get("retrieval_attempts", 0)) + 1,
            "retrieval_retry_reason": retry_reason,
            "errors": errors,
        }

    return node


def retry_rewrite_node(state: ChatGraphState) -> dict[str, Any]:
    retry_query = build_retry_query(state)
    return {
        "rewritten_query": retry_query,
        "retrieval_retry_reason": None,
    }


def tool_errors_to_pipeline_errors(tool_errors: list[ToolError], stage: str) -> list:
    return [
        build_pipeline_error(
            stage=stage,
            exc=RuntimeError(error.message),
        ).model_copy(update={"error_type": error.error_type or "ToolError"})
        for error in tool_errors
    ]


def assess_retrieval_retry_reason(matches: list) -> str | None:
    if not matches:
        return "empty_results"

    context_chars = sum(len(match.text) for match in matches)
    if context_chars < MIN_RETRIEVAL_CONTEXT_CHARS:
        return "low_context"

    best_distance = min(match.distance for match in matches)
    if best_distance > MAX_ACCEPTABLE_BEST_DISTANCE:
        return "weak_similarity"

    return None


def build_retry_query(state: ChatGraphState) -> str:
    base_query = state.get("rewritten_query") or state.get("retrieval_query") or state["query"]
    retry_terms = [
        "공식 근거",
        "규정",
        "절차",
        "주의",
        "금지목록",
        "KADA",
        "WADA",
    ]
    return "\n".join(dict.fromkeys([base_query, *retry_terms]))


def build_answer_node(dependencies: ChatGraphDependencies) -> Callable[[ChatGraphState], dict[str, Any]]:
    def node(state: ChatGraphState) -> dict[str, Any]:
        search_input = state["search_input"]
        answer = generate_answer(
            query=search_input.query,
            decision=state["decision"],
            drug_result=state.get("drug_result"),
            pharmacology_result=state.get("pharmacology_result"),
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
    if should_run_pharmacology_info(state["search_input"].query):
        return "pharmacology"
    return "rewrite"


def next_after_drug_search(state: ChatGraphState) -> str:
    if should_run_pharmacology_info(state["search_input"].query):
        return "pharmacology"
    if should_run_retrieval(state["decision"]):
        return "rewrite"
    return "answer"


def next_after_pharmacology(state: ChatGraphState) -> str:
    if should_run_retrieval(state["decision"]):
        return "rewrite"
    return "answer"


def next_after_retrieve(state: ChatGraphState) -> str:
    if should_retry_retrieval(state):
        return "retry_rewrite"
    return "answer"


def should_retry_retrieval(state: ChatGraphState) -> bool:
    if not should_run_retrieval(state["decision"]):
        return False

    attempts = int(state.get("retrieval_attempts", 0))
    return attempts < MAX_RETRIEVAL_ATTEMPTS and bool(state.get("retrieval_retry_reason"))
