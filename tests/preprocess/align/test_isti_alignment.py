from app.preprocess.align.isti import extract_section_numbers, build_alignment_candidates


def test_extracts_legal_section_numbers() -> None:
    assert extract_section_numbers("5.3.5 The DCO shall notify. 13.1 Blood samples") == {"5.3.5", "13.1"}


def test_records_only_unambiguous_shared_sections() -> None:
    candidates = build_alignment_candidates(
        english_pages={83: "5.3.5 The DCO shall notify."},
        korean_pages={84: "5.3.5 시료채취요원은 통지한다."},
        korean_quality={84: "needs_review"},
    )
    assert len(candidates) == 1
    assert candidates[0].english_page == 83
    assert candidates[0].korean_page == 84
    assert candidates[0].section_numbers == ["5.3.5"]
    assert candidates[0].review_only is True
    assert candidates[0].usable_for_retrieval is False


def test_omits_ambiguous_or_missing_section_matches() -> None:
    candidates = build_alignment_candidates(
        english_pages={83: "5.3.5 text", 85: "5.3.5 repeated"},
        korean_pages={84: "5.3.5 한국어"},
        korean_quality={84: "needs_review"},
    )
    assert candidates == []


def test_uses_only_clause_numbers_not_page_adjacency() -> None:
    candidates = build_alignment_candidates(
        english_pages={83: "5.3.5 text"},
        korean_pages={84: "13.1 한국어"},
        korean_quality={84: "needs_review"},
    )

    assert candidates == []
