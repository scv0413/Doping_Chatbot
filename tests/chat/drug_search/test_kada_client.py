from app.chat.drug_search.kada_client import parse_kada_search_result
from app.chat.drug_search.schemas import CompetitionPeriod, DrugRiskStatus, DrugSearchInput


def test_parse_kada_result_requests_product_selection_for_multiple_products() -> None:
    search_input = DrugSearchInput(
        query="타이레놀 먹어도 돼?",
        product_name="타이레놀",
        competition_period=CompetitionPeriod.IN_COMPETITION,
    )

    result = parse_kada_search_result(
        search_input=search_input,
        product_payload={
            "page": {"total": 2},
            "list": [
                {
                    "drug_name": "어린이타이레놀현탁액",
                    "list_sunb_name": "Acetaminophen 3.2g/100mL",
                    "firm_name": "한국존슨앤드존슨판매",
                },
                {
                    "drug_name": "타이레놀8시간이알서방정",
                    "list_sunb_name": "Acetaminophen 325mg",
                    "firm_name": "한국존슨앤드존슨판매",
                },
            ],
        },
        substance_payload={
            "page": {"total": 1},
            "list": [
                {
                    "sunb_ename": "Acetaminophen",
                    "sunb_name": "아세트아미노펜",
                    "ingame": None,
                    "outgame": None,
                }
            ],
        },
        retrieved_at="2026-07-17T00:00:00+00:00",
    )

    assert result.status is DrugRiskStatus.LOW_RISK
    assert result.requires_product_selection is True
    assert len(result.matched_candidates) == 3
    assert "아세트아미노펜" in result.matched_substances


def test_parse_kada_result_marks_in_competition_banned_substance() -> None:
    search_input = DrugSearchInput(
        query="슈도에페드린",
        ingredient_name="슈도에페드린",
        competition_period=CompetitionPeriod.IN_COMPETITION,
    )

    result = parse_kada_search_result(
        search_input=search_input,
        product_payload={"page": {"total": 0}, "list": []},
        substance_payload={
            "page": {"total": 1},
            "list": [
                {
                    "sunb_ename": "pseudoephedrine",
                    "sunb_name": "슈도에페드린",
                    "ingame": "금지",
                    "outgame": "허용",
                }
            ],
        },
    )

    assert result.status is DrugRiskStatus.PROHIBITED_POSSIBLE
    assert result.requires_product_selection is False
    assert result.requires_dose_confirmation is True
    assert "금지 가능성" in result.recommended_action


def test_parse_kada_result_marks_out_of_competition_limited_substance_as_caution() -> None:
    search_input = DrugSearchInput(
        query="슈도에페드린",
        ingredient_name="슈도에페드린",
        competition_period=CompetitionPeriod.OUT_OF_COMPETITION,
    )

    result = parse_kada_search_result(
        search_input=search_input,
        product_payload={"page": {"total": 0}, "list": []},
        substance_payload={
            "page": {"total": 1},
            "list": [
                {
                    "sunb_ename": "pseudoephedrine",
                    "sunb_name": "슈도에페드린",
                    "ingame": "금지",
                    "outgame": "허용",
                }
            ],
        },
    )

    assert result.status is DrugRiskStatus.CAUTION
    assert result.requires_dose_confirmation is True


def test_parse_kada_result_marks_always_banned_substance() -> None:
    search_input = DrugSearchInput(
        query="테스토스테론",
        ingredient_name="테스토스테론",
        competition_period=CompetitionPeriod.OUT_OF_COMPETITION,
    )

    result = parse_kada_search_result(
        search_input=search_input,
        product_payload={"page": {"total": 0}, "list": []},
        substance_payload={
            "page": {"total": 1},
            "list": [
                {
                    "sunb_ename": "1-testosterone",
                    "sunb_name": "1-테스토스테론",
                    "ingame": "금지",
                    "outgame": "금지",
                    "mapid": "S1_007",
                }
            ],
        },
    )

    assert result.status is DrugRiskStatus.PROHIBITED_POSSIBLE
    assert result.prohibited_categories == ["S1_007"]


def test_parse_kada_result_marks_no_result_as_needs_verification() -> None:
    search_input = DrugSearchInput(query="알수없는약")

    result = parse_kada_search_result(
        search_input=search_input,
        product_payload={"page": {"total": 0}, "list": []},
        substance_payload={"page": {"total": 0}, "list": []},
    )

    assert result.status is DrugRiskStatus.NEEDS_VERIFICATION
    assert result.matched_candidates == []
    assert "조회 결과가 없습니다" in result.recommended_action
