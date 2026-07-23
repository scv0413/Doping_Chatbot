from app.chat.domain.drug_search.query_parser import (
    DrugQueryExtraction,
    extract_drug_query,
)
from app.chat.domain.drug_search.schemas import AdministrationRoute, CompetitionPeriod


def test_extract_drug_query_parses_natural_language_product_question() -> None:
    extraction = extract_drug_query("경기중 스트랩실 먹어도 돼?")

    assert extraction.product_name == "스트랩실"
    assert extraction.ingredient_name is None
    assert extraction.competition_period is CompetitionPeriod.IN_COMPETITION
    assert extraction.route is AdministrationRoute.ORAL
    assert extraction.intent == "drug_use_check"
    assert extraction.source == "rule"


def test_extract_drug_query_recognizes_product_before_spray_use_expression() -> None:
    extraction = extract_drug_query("코앤쿨 뿌려도 돼?")

    assert extraction.product_name == "코앤쿨"
    assert extraction.ingredient_name is None
    assert extraction.route is None
    assert extraction.intent == "drug_use_check"
    assert extraction.source == "rule"


def test_extract_drug_query_uses_unknown_single_term_as_kada_candidate() -> None:
    extraction = extract_drug_query("지르텍")

    assert extraction.product_name == "지르텍"
    assert extraction.source == "rule"


def test_extract_drug_query_uses_unknown_ingredient_or_herbal_term_as_kada_candidate() -> None:
    ingredient = extract_drug_query("세리티진염산염 계열의 약")
    herbal = extract_drug_query("감초 성분")

    assert ingredient.product_name == "세리티진염산염"
    assert herbal.product_name == "감초"


def test_extract_drug_query_does_not_treat_competition_period_as_a_product() -> None:
    extraction = extract_drug_query("약물 반감기로 경기기간 복용 가능 여부를 판단해도 돼?")

    assert extraction.product_name is None
    assert extraction.ingredient_name is None


def test_extract_drug_query_keeps_known_ingredient_as_ingredient() -> None:
    extraction = extract_drug_query("경기기간 중 아세트아미노펜 복용해도 돼?")

    assert extraction.ingredient_name == "아세트아미노펜"
    assert extraction.product_name is None
    assert extraction.competition_period is CompetitionPeriod.IN_COMPETITION


def test_extract_drug_query_rejects_llm_candidate_not_present_in_question() -> None:
    extraction = extract_drug_query(
        "경기 중 이 감기약 먹어도 돼?",
        llm_extractor=lambda _query: DrugQueryExtraction(
            product_name="존재하지않는약",
            intent="drug_use_check",
            source="llm",
        ),
    )

    assert extraction.product_name is None
    assert extraction.ingredient_name is None
    assert extraction.source == "none"


def test_extract_drug_query_accepts_verbatim_llm_product_candidate() -> None:
    extraction = extract_drug_query(
        "경기 중 이 제품 사용해도 돼? 제품명은 메디콜드야.",
        llm_extractor=lambda _query: DrugQueryExtraction(
            product_name="메디콜드",
            intent="drug_use_check",
            source="llm",
        ),
    )

    assert extraction.product_name == "메디콜드"
    assert extraction.source == "llm"
    assert extraction.competition_period is CompetitionPeriod.IN_COMPETITION
