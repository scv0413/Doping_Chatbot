from app.chat.domain.drug_search.mock_searcher import search_mock_drugs
from app.chat.domain.drug_search.schemas import (
    CompetitionPeriod,
    DrugRiskStatus,
    DrugSearchInput,
)


def test_mock_searcher_requests_selection_for_multiple_tylenol_products() -> None:
    search_input = DrugSearchInput(
        query="타이레놀 먹어도 돼?",
        product_name="타이레놀",
        competition_period=CompetitionPeriod.IN_COMPETITION,
    )

    result = search_mock_drugs(search_input)

    assert result.status is DrugRiskStatus.LOW_RISK
    assert result.requires_product_selection is True
    assert len(result.matched_candidates) >= 2
    assert result.matched_substances == ["아세트아미노펜"]


def test_mock_searcher_marks_unknown_competition_period_as_needs_verification() -> None:
    search_input = DrugSearchInput(
        query="아세트아미노펜 먹어도 돼?",
        ingredient_name="아세트아미노펜",
    )

    result = search_mock_drugs(search_input)

    assert result.status is DrugRiskStatus.NEEDS_VERIFICATION
    assert result.requires_product_selection is True


def test_mock_searcher_marks_pseudoephedrine_as_caution() -> None:
    search_input = DrugSearchInput(
        query="슈도에페드린 감기약 먹어도 돼?",
        ingredient_name="슈도에페드린",
        competition_period=CompetitionPeriod.IN_COMPETITION,
    )

    result = search_mock_drugs(search_input)

    assert result.status is DrugRiskStatus.CAUTION
    assert result.requires_route_confirmation is True
    assert result.requires_dose_confirmation is True


def test_mock_searcher_falls_back_when_no_candidate_matches() -> None:
    search_input = DrugSearchInput(query="처음 보는 약")

    result = search_mock_drugs(search_input)

    assert result.status is DrugRiskStatus.NEEDS_VERIFICATION
    assert result.matched_candidates == []
    assert result.recommended_action
