from app.chat.domain.retrieval.retriever import (
    rerank_section_matches,
    SECTION_REFERENCE_PATTERN,
    rerank_urine_requirement_matches,
    resolve_candidate_k,
)
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


def test_rerank_urine_requirement_matches_prioritizes_isti_definition() -> None:
    procedural_match = RetrievalMatch(
        rank=1,
        chunk_id="wada_isti_2023_en:p71:c0",
        distance=0.2,
        metadata=RetrievalMetadata(source_id="wada_isti_2023_en", page=71),
        text="ANNEX E - URINE SAMPLES - INSUFFICIENT VOLUME",
    )
    definition_match = RetrievalMatch(
        rank=2,
        chunk_id="wada_isti_2023_en:p16:c0",
        distance=0.4,
        metadata=RetrievalMetadata(source_id="wada_isti_2023_en", page=16),
        text=(
            "Suitable Specific Gravity for Analysis: 1.005 or higher. "
            "Suitable Volume of Urine for Analysis: A minimum of 90 mL."
        ),
    )

    ranked = rerank_urine_requirement_matches(
        [procedural_match, definition_match],
        "urine Sample Suitable Volume of Urine for Analysis 90 mL specific gravity",
    )

    assert [match.chunk_id for match in ranked] == [
        "wada_isti_2023_en:p16:c0",
        "wada_isti_2023_en:p71:c0",
    ]


def test_resolve_candidate_k_expands_pool_for_urine_requirement_questions() -> None:
    candidate_k = resolve_candidate_k(
        top_k=3,
        query="urine Sample Suitable Volume of Urine for Analysis 90 mL specific gravity",
    )

    assert candidate_k == 75


def test_section_reference_pattern_does_not_treat_specific_gravity_as_section_reference() -> None:
    assert SECTION_REFERENCE_PATTERN.findall("specific gravity 1.005") == []


def test_resolve_candidate_k_expands_pool_for_specific_gravity_explanations() -> None:
    candidate_k = resolve_candidate_k(
        top_k=3,
        query="urine Sample refractometer specific gravity 1.003",
    )

    assert candidate_k == 75
