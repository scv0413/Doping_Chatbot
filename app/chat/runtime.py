from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.chat.domain.answer.types import AnswerLLM
from app.chat.domain.drug_search.schemas import DrugSearchInput
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


class CitationSummary(BaseModel):
    chunk_id: str
    source_id: str
    title: str
    page: int | None = None
    distance: float
    official_source_id: str | None = None
    official_source_page: int | None = None


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
    pharmacology_status: str | None = None
    pharmacology_substance: str | None = None
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
    if runtime_policy.engine is RuntimeEngine.GRAPH:
        result = run_chat_graph(
            resolved_request.query,
            top_k=runtime_policy.top_k,
            use_llm=runtime_policy.use_llm,
            recursion_limit=runtime_policy.recursion_limit,
            **runner_kwargs,
        )
    else:
        result = run_chat_pipeline(
            resolved_request.query,
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
        pharmacology_status=result.pharmacology_result.status.value if result.pharmacology_result else None,
        pharmacology_substance=result.pharmacology_result.substance_name if result.pharmacology_result else None,
        retrieval_attempts=result.retrieval_attempts,
        retrieval_retry_reason=result.retrieval_retry_reason,
        planned_tool_names=result.planned_tool_names,
        errors=[error.model_dump() for error in result.errors],
    )


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
