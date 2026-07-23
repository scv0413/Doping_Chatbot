from app.chat.domain.drug_search.formatter import format_drug_search_answer
from app.chat.domain.drug_search.schemas import (
    CompetitionPeriod,
    DrugCandidate,
    DrugRiskStatus,
    DrugSearchInput,
    DrugSearchResult,
    DrugSearchSource,
    MatchType,
)


def test_formatter_renders_product_selection_answer() -> None:
    result = DrugSearchResult(
        status=DrugRiskStatus.NEEDS_VERIFICATION,
        input=DrugSearchInput(
            query="타이레놀 먹어도 돼?",
            product_name="타이레놀",
            competition_period=CompetitionPeriod.IN_COMPETITION,
        ),
        matched_candidates=[
            DrugCandidate(
                name="타이레놀8시간이알서방정",
                match_type=MatchType.PRODUCT,
                ingredient_names=["Acetaminophen 325mg"],
                manufacturer="한국존슨앤드존슨판매",
            )
        ],
        requires_product_selection=True,
        recommended_action="검색 결과가 여러 개입니다. 정확한 제품을 선택하고 성분표를 확인하세요.",
        sources=[DrugSearchSource(title="KADA 금지약물 검색서비스", url="https://kada.health.kr")],
    )

    answer = format_drug_search_answer(result)

    assert "## 현재 입력 정보" in answer
    assert "위험 상태: 확인 필요" in answer
    assert "정확한 제품을 선택해야 합니다." in answer
    assert "타이레놀8시간이알서방정" in answer


def test_formatter_renders_prohibited_possible_answer() -> None:
    result = DrugSearchResult(
        status=DrugRiskStatus.PROHIBITED_POSSIBLE,
        input=DrugSearchInput(
            query="슈도에페드린 경기기간 중 먹어도 돼?",
            ingredient_name="슈도에페드린",
            competition_period=CompetitionPeriod.IN_COMPETITION,
        ),
        matched_substances=["슈도에페드린", "pseudoephedrine"],
        prohibited_categories=["S6_120"],
        requires_dose_confirmation=True,
        recommended_action="금지 가능성이 확인됩니다. 사용 전 KADA, 팀 닥터, 약사 또는 도핑 담당자에게 확인하세요.",
        sources=[DrugSearchSource(title="KADA 금지약물 검색서비스", url="https://kada.health.kr")],
        notes=["조회 결과가 없다는 것은 금지가 아님을 의미하지 않습니다."],
    )

    answer = format_drug_search_answer(result)

    assert "위험 상태: 금지 가능성 있음" in answer
    assert "관련 금지 분류 후보: S6_120" in answer
    assert "용량 또는 농도 기준을 확인해야 합니다." in answer
    assert "금지 가능성이 확인됩니다." in answer


def test_formatter_renders_unknown_competition_period_confirmation() -> None:
    result = DrugSearchResult(
        status=DrugRiskStatus.NEEDS_VERIFICATION,
        input=DrugSearchInput(query="알 수 없는 약"),
        recommended_action="조회 결과가 없습니다. 금지가 아님을 의미하지 않으므로 제품명과 성분명을 다시 확인하세요.",
    )

    answer = format_drug_search_answer(result)

    assert "경기기간 여부: 모름" in answer
    assert "경기기간 중인지 경기기간 외인지 확인해야 합니다." in answer
    assert "정확한 제품명 또는 성분명을 다시 확인해야 합니다." in answer
    assert "검색 후보: 없음" in answer
