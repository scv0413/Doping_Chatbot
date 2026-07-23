from collections.abc import Callable

from pydantic import BaseModel, Field

from app.chat.domain.answer.chain import generate_answer
from app.chat.domain.answer.types import AnswerLLM
from app.chat.domain.drug_search.kada_client import search_kada_drugs
from app.chat.domain.pharmacology.schemas import PharmacologyInfoResult
from app.chat.domain.pharmacology.service import (
    search_pharmacology_info,
    should_run_pharmacology_info,
)
from app.chat.domain.drug_search.query_parser import DrugQueryLLM, extract_drug_query
from app.chat.domain.drug_search.schemas import (
    DrugSearchInput,
    DrugSearchResult,
    build_needs_verification_result,
)
from app.chat.domain.retrieval.query_rewriter import rewrite_query
from app.chat.domain.retrieval.retriever import search
from app.chat.domain.retrieval.schemas import RetrievalMatch
from app.chat.orchestration.router.intent_router import ChatRoute, RouteDecision, route_question, route_search_input
from app.chat.tools.schemas import DrugSearchToolOutput, PharmacologyInfoToolOutput, RagSearchToolOutput


CATEGORY_RETRIEVAL_TERMS = {
    "S1": ["S1", "동화작용제", "anabolic agents", "상시 금지"],
    "S2": ["S2", "펩티드호르몬", "peptide hormones", "상시 금지"],
    "S3": ["S3", "베타-2 작용제", "beta-2 agonists"],
    "S4": ["S4", "호르몬 및 대사 변조제", "hormone and metabolic modulators"],
    "S5": ["S5", "이뇨제", "은폐제", "diuretics", "masking agents"],
    "S6": ["S6", "흥분제", "stimulants", "경기기간 중 금지"],
    "S7": ["S7", "마약", "narcotics", "경기기간 중 금지"],
    "S8": ["S8", "카나비노이드", "cannabinoids", "경기기간 중 금지"],
    "S9": ["S9", "글루코코르티코이드", "glucocorticoids", "경기기간 중 금지"],
    "M1": ["M1", "혈액", "blood manipulation", "상시 금지"],
    "M2": ["M2", "화학적 물리적 조작", "chemical and physical manipulation"],
    "M3": ["M3", "유전자", "gene doping"],
}

DrugSearcher = Callable[[DrugSearchInput], DrugSearchResult]
Retriever = Callable[[str, int], list[RetrievalMatch]]
QuestionRouter = Callable[[str], RouteDecision]
QueryRewriter = Callable[[str], str]
PharmacologySearcher = Callable[[str], PharmacologyInfoResult]


class PipelineError(BaseModel):
    stage: str
    error_type: str
    message: str


class ChatPipelineResult(BaseModel):
    search_input: DrugSearchInput
    decision: RouteDecision
    drug_result: DrugSearchResult | None = None
    drug_search_tool_output: DrugSearchToolOutput | None = None
    pharmacology_result: PharmacologyInfoResult | None = None
    pharmacology_info_tool_output: PharmacologyInfoToolOutput | None = None
    retrieval_query: str | None = None
    rewritten_query: str | None = None
    rag_search_output: RagSearchToolOutput | None = None
    retrieval_matches: list[RetrievalMatch] = Field(default_factory=list)
    retrieval_attempts: int = 0
    retrieval_retry_reason: str | None = None
    planned_tool_names: list[str] = Field(default_factory=list)
    answer: str
    errors: list[PipelineError] = Field(default_factory=list)


def run_chat_pipeline(
    search_input: DrugSearchInput | str,
    top_k: int = 5,
    use_llm: bool = True,
    llm: AnswerLLM | None = None,
    router: QuestionRouter = route_question,
    drug_searcher: DrugSearcher = search_kada_drugs,
    retriever: Retriever = search,
    query_rewriter: QueryRewriter = rewrite_query,
    pharmacology_searcher: PharmacologySearcher = search_pharmacology_info,
    drug_query_extractor: DrugQueryLLM | None = None,
) -> ChatPipelineResult:
    resolved_input = normalize_pipeline_input(search_input, llm_extractor=drug_query_extractor)
    decision = route_search_input(resolved_input) if router is route_question else router(resolved_input.query)
    errors: list[PipelineError] = []

    drug_result: DrugSearchResult | None = None
    drug_search_tool_output: DrugSearchToolOutput | None = None
    if should_run_drug_search(decision):
        drug_result = run_drug_search_step(
            search_input=resolved_input,
            drug_searcher=drug_searcher,
            errors=errors,
        )

    pharmacology_result: PharmacologyInfoResult | None = None
    pharmacology_info_tool_output: PharmacologyInfoToolOutput | None = None
    if should_run_pharmacology_info(resolved_input.query):
        pharmacology_result = run_pharmacology_step(
            query=build_pharmacology_query(resolved_input, drug_result),
            pharmacology_searcher=pharmacology_searcher,
            errors=errors,
        )

    retrieval_query: str | None = None
    rewritten_query: str | None = None
    retrieval_matches: list[RetrievalMatch] = []
    if should_run_retrieval(decision):
        retrieval_query = build_retrieval_query(
            search_input=resolved_input,
            decision=decision,
            drug_result=drug_result,
        )
        rewritten_query = run_query_rewrite_step(
            query=retrieval_query,
            query_rewriter=query_rewriter,
            errors=errors,
        )
        retrieval_matches = run_retrieval_step(
            query=rewritten_query,
            top_k=top_k,
            retriever=retriever,
            errors=errors,
        )
        retrieval_attempts = 1

    answer = generate_answer(
        query=resolved_input.query,
        decision=decision,
        drug_result=drug_result,
        pharmacology_result=pharmacology_result,
        retrieval_matches=retrieval_matches,
        llm=llm,
        use_llm=use_llm,
    )

    return ChatPipelineResult(
        search_input=resolved_input,
        decision=decision,
        drug_result=drug_result,
        pharmacology_result=pharmacology_result,
        retrieval_query=retrieval_query,
        rewritten_query=rewritten_query,
        retrieval_matches=retrieval_matches,
        retrieval_attempts=locals().get("retrieval_attempts", 0),
        answer=answer,
        errors=errors,
    )


def normalize_pipeline_input(
    search_input: DrugSearchInput | str,
    llm_extractor: DrugQueryLLM | None = None,
) -> DrugSearchInput:
    if isinstance(search_input, DrugSearchInput):
        return search_input

    extraction = extract_drug_query(search_input, llm_extractor=llm_extractor)
    return DrugSearchInput(
        query=search_input,
        product_name=extraction.product_name,
        ingredient_name=extraction.ingredient_name,
        competition_period=extraction.competition_period,
        route=extraction.route,
    )


def should_run_drug_search(decision: RouteDecision) -> bool:
    return decision.route in {ChatRoute.DRUG_SEARCH, ChatRoute.DRUG_SEARCH_WITH_RAG}


def should_run_retrieval(decision: RouteDecision) -> bool:
    return decision.route in {ChatRoute.RAG, ChatRoute.DRUG_SEARCH_WITH_RAG}


def run_drug_search_step(
    search_input: DrugSearchInput,
    drug_searcher: DrugSearcher,
    errors: list[PipelineError],
) -> DrugSearchResult:
    try:
        return drug_searcher(search_input)
    except Exception as exc:
        errors.append(build_pipeline_error(stage="drug_search", exc=exc))
        return build_needs_verification_result(
            search_input=search_input,
            recommended_action="약물검색 중 오류가 발생했습니다. 제품명과 성분명을 확인한 뒤 다시 조회하거나 KADA 공식 자료를 확인하세요.",
        )


def run_pharmacology_step(
    query: str,
    pharmacology_searcher: PharmacologySearcher,
    errors: list[PipelineError],
) -> PharmacologyInfoResult | None:
    try:
        return pharmacology_searcher(query)
    except Exception as exc:
        errors.append(build_pipeline_error(stage="pharmacology_info", exc=exc))
        return None


def run_retrieval_step(
    query: str,
    top_k: int,
    retriever: Retriever,
    errors: list[PipelineError],
) -> list[RetrievalMatch]:
    try:
        return retriever(query, top_k)
    except Exception as exc:
        errors.append(build_pipeline_error(stage="retrieval", exc=exc))
        return []


def run_query_rewrite_step(
    query: str,
    query_rewriter: QueryRewriter,
    errors: list[PipelineError],
) -> str:
    try:
        return query_rewriter(query)
    except Exception as exc:
        errors.append(build_pipeline_error(stage="query_rewrite", exc=exc))
        return query


def build_pipeline_error(stage: str, exc: Exception) -> PipelineError:
    return PipelineError(
        stage=stage,
        error_type=type(exc).__name__,
        message=str(exc),
    )


def build_pharmacology_query(
    search_input: DrugSearchInput,
    drug_result: DrugSearchResult | None = None,
) -> str:
    """Use KADA detail ingredients only after a concrete product is selected."""

    detail = drug_result.selected_product_detail if drug_result else None
    if detail is None:
        return search_input.query

    return "\n".join(
        dict.fromkeys(
            value
            for value in [search_input.query, *detail.ingredients]
            if value
        )
    )


def build_retrieval_query(
    search_input: DrugSearchInput,
    decision: RouteDecision,
    drug_result: DrugSearchResult | None = None,
) -> str:
    parts = [search_input.query]

    if decision.route is ChatRoute.RAG:
        return "\n".join(parts)

    parts.extend([search_input.ingredient_name or "", search_input.product_name or ""])

    if drug_result:
        parts.extend(drug_result.matched_substances[:5])
        parts.extend(drug_result.prohibited_categories)
        for category in drug_result.prohibited_categories:
            parts.extend(CATEGORY_RETRIEVAL_TERMS.get(category.split("_")[0], []))

    parts.extend(["금지약물", "금지목록", "경기기간", "투여 경로", "용량", "종목"])
    return "\n".join(dict.fromkeys(part for part in parts if part))
