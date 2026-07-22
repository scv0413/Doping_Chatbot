from typing import NotRequired, TypedDict

from app.chat.drug_search.schemas import DrugSearchInput, DrugSearchResult
from app.chat.pharmacology.schemas import PharmacologyInfoResult
from app.chat.pipeline.chat_pipeline import PipelineError
from app.chat.retrieval.schemas import RetrievalMatch
from app.chat.router.intent_router import RouteDecision
from app.chat.tools.schemas import DrugSearchToolOutput, RagSearchToolOutput


class ChatGraphState(TypedDict):
    query: str
    top_k: NotRequired[int]
    use_llm: NotRequired[bool]

    search_input: NotRequired[DrugSearchInput]
    decision: NotRequired[RouteDecision]
    drug_result: NotRequired[DrugSearchResult | None]
    drug_search_tool_output: NotRequired[DrugSearchToolOutput | None]
    pharmacology_result: NotRequired[PharmacologyInfoResult | None]
    retrieval_query: NotRequired[str | None]
    rewritten_query: NotRequired[str | None]
    rag_search_output: NotRequired[RagSearchToolOutput | None]
    retrieval_matches: NotRequired[list[RetrievalMatch]]
    retrieval_attempts: NotRequired[int]
    retrieval_retry_reason: NotRequired[str | None]
    answer: NotRequired[str]
    errors: NotRequired[list[PipelineError]]
