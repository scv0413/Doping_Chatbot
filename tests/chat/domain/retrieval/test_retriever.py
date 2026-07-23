from app.chat.domain.retrieval.retriever import rerank_section_matches
from app.chat.domain.retrieval.schemas import RetrievalMatch, RetrievalMetadata


def build_match(chunk_id: str, distance: float, section: str | None) -> RetrievalMatch:
    return RetrievalMatch(
        rank=1,
        chunk_id=chunk_id,
        distance=distance,
        metadata=RetrievalMetadata(source_id="source", section=section),
        text="retrieval text",
    )


def test_rerank_section_matches_prioritizes_explicit_article_reference() -> None:
    generic = build_match("generic", 0.2, None)
    article = build_match("isti:5.4.4:c0", 0.5, "5.4.4")

    matches = rerank_section_matches([generic, article], "Article 5.4.4 delay")

    assert [match.chunk_id for match in matches] == ["isti:5.4.4:c0", "generic"]


def test_rerank_section_matches_preserves_vector_order_without_article_reference() -> None:
    first = build_match("first", 0.2, "5.4.4")
    second = build_match("second", 0.3, None)

    matches = rerank_section_matches([first, second], "도핑검사 통지 지연")

    assert [match.chunk_id for match in matches] == ["first", "second"]
