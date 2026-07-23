from collections.abc import Callable

from app.chat.domain.retrieval.retriever import search
from app.chat.domain.retrieval.schemas import RetrievalMatch, RetrievalMetadata
from app.chat.tools.schemas import RagSearchRequest, RagSearchResult, RagSearchToolOutput, ToolError

RagRetriever = Callable[[str, int], list[RetrievalMatch]]


def run_rag_search_tool(
    request: RagSearchRequest,
    retriever: RagRetriever = search,
) -> RagSearchToolOutput:
    try:
        matches = retriever(request.query, request.top_k)
    except Exception as exc:
        return RagSearchToolOutput(
            query=request.query,
            top_k=request.top_k,
            request_id=request.request_id,
            errors=[
                ToolError(
                    stage="rag_search",
                    message=str(exc),
                    error_type=type(exc).__name__,
                )
            ],
        )

    return RagSearchToolOutput(
        query=request.query,
        top_k=request.top_k,
        request_id=request.request_id,
        results=[match_to_tool_result(match) for match in matches],
    )


def match_to_tool_result(match: RetrievalMatch) -> RagSearchResult:
    metadata = match.metadata
    return RagSearchResult(
        rank=match.rank,
        chunk_id=match.chunk_id,
        source_id=metadata.source_id,
        title=match.title,
        text=match.text,
        distance=match.distance,
        page=metadata.page,
        section=metadata.section,
        authority=metadata.authority,
        source_type=metadata.source_type,
    )


def tool_output_to_retrieval_matches(output: RagSearchToolOutput) -> list[RetrievalMatch]:
    return [tool_result_to_retrieval_match(result) for result in output.results]


def tool_result_to_retrieval_match(result: RagSearchResult) -> RetrievalMatch:
    return RetrievalMatch(
        rank=result.rank,
        chunk_id=result.chunk_id,
        distance=result.distance,
        metadata=RetrievalMetadata(
            source_id=result.source_id,
            title=result.title,
            page=result.page,
            section=result.section,
            authority=result.authority,
            source_type=result.source_type,
            chunk_id=result.chunk_id,
        ),
        text=result.text,
    )
