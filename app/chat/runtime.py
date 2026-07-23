from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.chat.domain.answer.types import AnswerLLM
from app.chat.domain.drug_search.schemas import (
    AdministrationRoute,
    CompetitionPeriod,
    DrugSearchInput,
    KADADrugDetail,
    MatchType,
)
from app.chat.orchestration.graph.graph import run_chat_graph
from app.chat.orchestration.pipeline.chat_pipeline import (
    ChatPipelineResult,
    DrugSearcher,
    PharmacologySearcher,
    QueryRewriter,
    QuestionRouter,
    Retriever,
    run_chat_pipeline,
)
from app.chat.domain.policy.runtime_policy import RuntimePolicyDecision, RuntimeEngine, decide_runtime_policy


class ChatEngine(StrEnum):
    GRAPH = "graph"
    PIPELINE = "pipeline"


class ChatRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=10)
    use_llm: bool | None = None
    engine: ChatEngine | None = None
    recursion_limit: int | None = Field(default=None, ge=1, le=50)
    product_name: str | None = None
    ingredient_name: str | None = None
    competition_period: CompetitionPeriod = CompetitionPeriod.UNKNOWN
    route: AdministrationRoute | None = None
    sport: str | None = None
    dose: str | None = None
    drug_code: str | None = None


class CitationSummary(BaseModel):
    chunk_id: str
    source_id: str
    title: str
    page: int | None = None
    distance: float
    official_source_id: str | None = None
    official_source_page: int | None = None


class DrugCandidateSummary(BaseModel):
    name: str
    ingredient_names: list[str] = Field(default_factory=list)
    manufacturer: str | None = None
    drug_code: str | None = None


class PharmacologyIngredientSummary(BaseModel):
    substance_name: str
    typical_range: str | None = None
    wider_range: str | None = None
    interpretation_notes: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    route: str
    query: str
    engine: ChatEngine
    top_k: int = 3
    use_llm: bool = False
    policy_reason: str | None = None
    policy_matched_rules: list[str] = Field(default_factory=list)
    citations: list[CitationSummary] = Field(default_factory=list)
    drug_status: str | None = None
    product_candidates: list[DrugCandidateSummary] = Field(default_factory=list)
    requires_product_selection: bool = False
    herbal_verification_unavailable: bool = False
    drug_detail: KADADrugDetail | None = None
    pharmacology_status: str | None = None
    pharmacology_substance: str | None = None
    pharmacology_ingredients: list[PharmacologyIngredientSummary] = Field(default_factory=list)
    retrieval_attempts: int = 0
    retrieval_retry_reason: str | None = None
    planned_tool_names: list[str] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)


class ChatRuntimeDependencies(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    llm: AnswerLLM | None = None
    router: QuestionRouter | None = None
    drug_searcher: DrugSearcher | None = None
    retriever: Retriever | None = None
    query_rewriter: QueryRewriter | None = None
    pharmacology_searcher: PharmacologySearcher | None = None


def run_chat(
    request: ChatRequest | DrugSearchInput | str,
    dependencies: ChatRuntimeDependencies | None = None,
) -> ChatResponse:
    resolved_request = normalize_chat_request(request)
    runtime_policy = resolve_runtime_policy(resolved_request)
    dependencies = dependencies or ChatRuntimeDependencies()

    runner_kwargs = build_runner_kwargs(dependencies)
    search_input = chat_request_to_drug_search_input(resolved_request)
    if runtime_policy.engine is RuntimeEngine.GRAPH:
        result = run_chat_graph(
            search_input,
            top_k=runtime_policy.top_k,
            use_llm=runtime_policy.use_llm,
            recursion_limit=runtime_policy.recursion_limit,
            **runner_kwargs,
        )
    else:
        result = run_chat_pipeline(
            search_input,
            top_k=runtime_policy.top_k,
            use_llm=runtime_policy.use_llm,
            **runner_kwargs,
        )

    return build_chat_response(
        result=result,
        engine=ChatEngine(runtime_policy.engine.value),
        runtime_policy=runtime_policy,
    )


def build_runner_kwargs(dependencies: ChatRuntimeDependencies) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    if dependencies.llm is not None:
        kwargs["llm"] = dependencies.llm
    if dependencies.router is not None:
        kwargs["router"] = dependencies.router
    if dependencies.drug_searcher is not None:
        kwargs["drug_searcher"] = dependencies.drug_searcher
    if dependencies.retriever is not None:
        kwargs["retriever"] = dependencies.retriever
    if dependencies.query_rewriter is not None:
        kwargs["query_rewriter"] = dependencies.query_rewriter
    if dependencies.pharmacology_searcher is not None:
        kwargs["pharmacology_searcher"] = dependencies.pharmacology_searcher
    return kwargs


def normalize_chat_request(request: ChatRequest | DrugSearchInput | str) -> ChatRequest:
    if isinstance(request, ChatRequest):
        return request
    if isinstance(request, DrugSearchInput):
        return ChatRequest(query=request.query)
    return ChatRequest(query=request)


def chat_request_to_drug_search_input(request: ChatRequest) -> DrugSearchInput:
    return DrugSearchInput(
        query=request.query,
        product_name=request.product_name,
        ingredient_name=request.ingredient_name,
        competition_period=request.competition_period,
        route=request.route,
        sport=request.sport,
        dose=request.dose,
        drug_code=request.drug_code,
    )

def resolve_runtime_policy(request: ChatRequest) -> RuntimePolicyDecision:
    return decide_runtime_policy(
        query=request.query,
        top_k=request.top_k,
        use_llm=request.use_llm,
        engine=RuntimeEngine(request.engine.value) if request.engine else None,
        recursion_limit=request.recursion_limit,
    )


def build_chat_response(
    result: ChatPipelineResult,
    engine: ChatEngine,
    runtime_policy: RuntimePolicyDecision,
) -> ChatResponse:
    return ChatResponse(
        answer=result.answer,
        route=result.decision.route.value,
        query=result.search_input.query,
        engine=engine,
        top_k=runtime_policy.top_k,
        use_llm=runtime_policy.use_llm,
        policy_reason=runtime_policy.reason,
        policy_matched_rules=runtime_policy.matched_rules,
        citations=[build_citation_summary(match) for match in result.retrieval_matches],
        drug_status=result.drug_result.status.value if result.drug_result else None,
        product_candidates=build_product_candidate_summaries(result.drug_result),
        requires_product_selection=bool(
            result.drug_result and result.drug_result.requires_product_selection
        ),
        herbal_verification_unavailable=bool(
            result.drug_result and result.drug_result.herbal_verification_unavailable
        ),
        drug_detail=result.drug_result.selected_product_detail if result.drug_result else None,
        pharmacology_status=result.pharmacology_result.status.value if result.pharmacology_result else None,
        pharmacology_substance=result.pharmacology_result.substance_name if result.pharmacology_result else None,
        pharmacology_ingredients=build_pharmacology_ingredient_summaries(result.pharmacology_result),
        retrieval_attempts=result.retrieval_attempts,
        retrieval_retry_reason=result.retrieval_retry_reason,
        planned_tool_names=result.planned_tool_names,
        errors=[error.model_dump() for error in result.errors],
    )


def build_pharmacology_ingredient_summaries(
    pharmacology_result,
) -> list[PharmacologyIngredientSummary]:
    if pharmacology_result is None:
        return []

    return [
        PharmacologyIngredientSummary(
            substance_name=item.substance_name,
            typical_range=item.half_life.typical_range if item.half_life else None,
            wider_range=item.half_life.wider_range if item.half_life else None,
            interpretation_notes=item.half_life.interpretation_notes if item.half_life else [],
        )
        for item in pharmacology_result.ingredient_results
    ]


def build_product_candidate_summaries(
    drug_result,
) -> list[DrugCandidateSummary]:
    if drug_result is None:
        return []

    return [
        DrugCandidateSummary(
            name=candidate.name,
            ingredient_names=candidate.ingredient_names,
            manufacturer=candidate.manufacturer,
            drug_code=candidate.drug_code,
        )
        for candidate in drug_result.matched_candidates
        if candidate.match_type is MatchType.PRODUCT
    ]

def build_citation_summary(match) -> CitationSummary:
    return CitationSummary(
        chunk_id=match.chunk_id,
        source_id=match.source_id,
        title=match.title,
        page=match.metadata.page,
        distance=match.distance,
        official_source_id=match.metadata.official_source_id,
        official_source_page=match.metadata.official_source_page,
    )
