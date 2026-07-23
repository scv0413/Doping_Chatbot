from typing import NotRequired, TypedDict

from app.chat.domain.drug_search.schemas import DrugSearchInput, DrugSearchResult
from app.chat.orchestration.agent import AgentToolPlan
from app.chat.domain.pharmacology.schemas import PharmacologyInfoResult
from app.chat.orchestration.pipeline.chat_pipeline import PipelineError
from app.chat.domain.retrieval.schemas import RetrievalMatch
from app.chat.orchestration.router.intent_router import RouteDecision
from app.chat.tools.schemas import DrugSearchToolOutput, PharmacologyInfoToolOutput, RagSearchToolOutput


class ChatGraphState(TypedDict):
    query: str
    top_k: NotRequired[int]
    use_llm: NotRequired[bool]

    search_input: NotRequired[DrugSearchInput]
    decision: NotRequired[RouteDecision]
    agent_plan: NotRequired[AgentToolPlan]
    drug_result: NotRequired[DrugSearchResult | None]
    drug_search_tool_output: NotRequired[DrugSearchToolOutput | None]
    pharmacology_result: NotRequired[PharmacologyInfoResult | None]
    pharmacology_info_tool_output: NotRequired[PharmacologyInfoToolOutput | None]
    retrieval_query: NotRequired[str | None]
    rewritten_query: NotRequired[str | None]
    rag_search_output: NotRequired[RagSearchToolOutput | None]
    retrieval_matches: NotRequired[list[RetrievalMatch]]
    retrieval_attempts: NotRequired[int]
    retrieval_retry_reason: NotRequired[str | None]
    answer: NotRequired[str]
    errors: NotRequired[list[PipelineError]]
