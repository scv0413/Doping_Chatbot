import pytest
from pydantic import ValidationError

from app.chat.domain.retrieval.schemas import RetrievalMatch, RetrievalMetadata
from app.chat.tools import RagSearchRequest, run_rag_search_tool


def fake_retriever(query: str, top_k: int) -> list[RetrievalMatch]:
    assert query == "S0 비승인약물이 뭐야?"
    assert top_k == 3
    return [
        RetrievalMatch(
            rank=1,
            chunk_id="wada_prohibited_list_2026_ko:p5:c0",
            distance=0.12,
            metadata=RetrievalMetadata(
                source_id="wada_prohibited_list_2026_ko",
                title="2026 WADA Prohibited List",
                page=5,
                section="S0",
                authority="WADA",
                source_type="pdf",
                chunk_id="wada_prohibited_list_2026_ko:p5:c0",
            ),
            text="S0 비승인약물은 상시 금지됩니다.",
        )
    ]


def test_run_rag_search_tool_returns_structured_results() -> None:
    request = RagSearchRequest(
        query="S0 비승인약물이 뭐야?",
        top_k=3,
        request_id="tool-request-1",
    )

    output = run_rag_search_tool(request, retriever=fake_retriever)

    assert output.ok is True
    assert output.tool_name == "rag_search_tool"
    assert output.query == request.query
    assert output.top_k == 3
    assert output.request_id == "tool-request-1"
    assert output.errors == []
    assert len(output.results) == 1

    result = output.results[0]
    assert result.rank == 1
    assert result.chunk_id == "wada_prohibited_list_2026_ko:p5:c0"
    assert result.source_id == "wada_prohibited_list_2026_ko"
    assert result.title == "2026 WADA Prohibited List"
    assert result.page == 5
    assert result.section == "S0"
    assert result.authority == "WADA"
    assert result.source_type == "pdf"
    assert "상시 금지" in result.text


def test_run_rag_search_tool_returns_tool_error_when_retriever_fails() -> None:
    def broken_retriever(query: str, top_k: int) -> list[RetrievalMatch]:
        raise RuntimeError("vector store unavailable")

    request = RagSearchRequest(query="S0 비승인약물이 뭐야?")

    output = run_rag_search_tool(request, retriever=broken_retriever)

    assert output.ok is False
    assert output.results == []
    assert len(output.errors) == 1
    assert output.errors[0].stage == "rag_search"
    assert output.errors[0].error_type == "RuntimeError"
    assert "vector store unavailable" in output.errors[0].message


def test_rag_search_request_rejects_invalid_top_k() -> None:
    with pytest.raises(ValidationError):
        RagSearchRequest(query="S0", top_k=0)

    with pytest.raises(ValidationError):
        RagSearchRequest(query="S0", top_k=11)


def test_rag_search_tool_preserves_official_source_citation() -> None:
    def reviewed_manual_retriever(query: str, top_k: int) -> list[RetrievalMatch]:
        return [
            RetrievalMatch(
                rank=1,
                chunk_id="wada_isti_ko_human_reviewed:5.3.5:c0",
                distance=0.1,
                metadata=RetrievalMetadata(
                    source_id="wada_isti_ko_human_reviewed",
                    title="ISTI Korean Human-Reviewed Guide",
                    official_source_id="wada_isti_2023_en",
                    official_source_page=42,
                ),
                text="검수된 한국어 안내문입니다.",
            )
        ]

    output = run_rag_search_tool(
        RagSearchRequest(query="ISTI 통지 절차"),
        retriever=reviewed_manual_retriever,
    )

    assert output.results[0].official_source_id == "wada_isti_2023_en"
    assert output.results[0].official_source_page == 42
