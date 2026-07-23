from app.chat.domain.drug_search.schemas import (
    CompetitionPeriod,
    DrugCandidate,
    DrugRiskStatus,
    DrugSearchInput,
    DrugSearchResult,
    MatchType,
    build_needs_verification_result,
)


def test_drug_search_input_accepts_natural_language_query() -> None:
    search_input = DrugSearchInput(
        query="타이레놀 먹어도 돼?",
        product_name="타이레놀",
        competition_period=CompetitionPeriod.IN_COMPETITION,
    )

    assert search_input.query == "타이레놀 먹어도 돼?"
    assert search_input.product_name == "타이레놀"
    assert search_input.competition_period is CompetitionPeriod.IN_COMPETITION


def test_result_marks_product_selection_when_candidates_are_multiple() -> None:
    search_input = DrugSearchInput(query="타이레놀", product_name="타이레놀")

    result = DrugSearchResult(
        status=DrugRiskStatus.NEEDS_VERIFICATION,
        input=search_input,
        matched_candidates=[
            DrugCandidate(name="타이레놀정 500mg", match_type=MatchType.PRODUCT),
            DrugCandidate(name="타이레놀 8시간 이알서방정", match_type=MatchType.PRODUCT),
        ],
        requires_product_selection=True,
        recommended_action="정확한 제품을 선택하세요.",
    )

    assert result.requires_product_selection is True


def test_build_needs_verification_result_uses_safe_default_status() -> None:
    search_input = DrugSearchInput(query="코감기 스프레이 써도 돼?")

    result = build_needs_verification_result(search_input)

    assert result.status is DrugRiskStatus.NEEDS_VERIFICATION
    assert result.recommended_action
    assert result.notes
