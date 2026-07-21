from app.chat.pharmacology.schemas import PharmacologyInfoStatus
from app.chat.pharmacology.service import search_pharmacology_info, should_run_pharmacology_info


def test_should_run_pharmacology_info_for_half_life_question() -> None:
    assert should_run_pharmacology_info("슈도에페드린 반감기가 얼마나 돼?") is True
    assert should_run_pharmacology_info("도핑 검사관 신분 확인 방법") is False


def test_search_pharmacology_info_finds_pseudoephedrine() -> None:
    result = search_pharmacology_info("슈도에페드린 반감기가 얼마나 돼?")

    assert result.status is PharmacologyInfoStatus.FOUND
    assert result.substance_name == "pseudoephedrine"
    assert result.half_life is not None
    assert "4-8시간" in result.half_life.typical_range
    assert result.sources
    assert "복용 허가" in " ".join(result.safety_notes)


def test_search_pharmacology_info_returns_not_found_for_unknown_substance() -> None:
    result = search_pharmacology_info("처음 보는 성분 반감기 알려줘")

    assert result.status is PharmacologyInfoStatus.NOT_FOUND
    assert result.substance_name is None
    assert "성분명" in result.recommended_action
