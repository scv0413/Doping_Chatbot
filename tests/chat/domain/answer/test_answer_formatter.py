from app.chat.domain.answer.formatter import format_answer
from app.chat.domain.drug_search.schemas import (
    CompetitionPeriod,
    DrugRiskStatus,
    DrugSearchInput,
    DrugSearchResult,
)
from app.chat.domain.retrieval.schemas import RetrievalMatch, RetrievalMetadata
from app.chat.orchestration.router.intent_router import ChatRoute, RouteDecision


def test_format_answer_combines_drug_result_and_retrieval_citations() -> None:
    search_input = DrugSearchInput(
        query="슈도에페드린 경기기간 중 먹어도 돼?",
        ingredient_name="슈도에페드린",
        competition_period=CompetitionPeriod.IN_COMPETITION,
    )
    drug_result = DrugSearchResult(
        status=DrugRiskStatus.PROHIBITED_POSSIBLE,
        input=search_input,
        matched_substances=["슈도에페드린", "pseudoephedrine"],
        prohibited_categories=["S6_120"],
        requires_dose_confirmation=True,
        recommended_action="금지 가능성이 확인됩니다.",
        notes=["조회 결과가 없다는 것은 금지가 아님을 의미하지 않습니다."],
    )
    answer = format_answer(
        query=search_input.query,
        decision=RouteDecision(route=ChatRoute.DRUG_SEARCH_WITH_RAG, reason="drug with rag"),
        drug_result=drug_result,
        retrieval_matches=[
            RetrievalMatch(
                rank=1,
                chunk_id="wada_prohibited_list_2026_ko:p17:c3",
                distance=0.3,
                metadata=RetrievalMetadata(
                    source_id="wada_prohibited_list_2026_ko",
                    title="WADA Prohibited List 2026",
                    page=17,
                ),
                text="Pseudoephedrine is prohibited when its concentration in urine is greater than 150 micrograms per millilitre.",
            )
        ],
    )

    assert "금지 가능성 있음" in answer
    assert "S6_120" in answer
    assert "용량 또는 농도 기준을 확인해야 합니다." in answer
    assert "Pseudoephedrine is prohibited" not in answer


def test_format_answer_handles_drug_search_only_product_selection() -> None:
    search_input = DrugSearchInput(
        query="타이레놀 먹어도 돼?",
        product_name="타이레놀",
        competition_period=CompetitionPeriod.IN_COMPETITION,
    )
    drug_result = DrugSearchResult(
        status=DrugRiskStatus.NEEDS_VERIFICATION,
        input=search_input,
        requires_product_selection=True,
        recommended_action="정확한 제품을 선택하세요.",
    )
    answer = format_answer(
        query=search_input.query,
        decision=RouteDecision(route=ChatRoute.DRUG_SEARCH, reason="drug only"),
        drug_result=drug_result,
    )

    assert "확인 필요" in answer
    assert "정확한 제품명과 성분표를 확인해야 합니다." in answer
    assert "검색된 RAG 문서 근거 없음" not in answer


def test_format_answer_handles_rag_only() -> None:
    answer = format_answer(
        query="TUE 신청 방법 알려줘",
        decision=RouteDecision(route=ChatRoute.RAG, reason="rag only"),
        retrieval_matches=[
            RetrievalMatch(
                rank=1,
                chunk_id="field_response_manual:s6:c0",
                distance=0.2,
                metadata=RetrievalMetadata(
                    source_id="field_response_manual",
                    title="Field Response Manual",
                ),
                text="TUE 신청 방법과 대리 신청 가능 여부를 묻는 경우",
            )
        ],
    )

    assert "공식 문서 근거를 바탕으로 안내합니다." in answer
    assert "TUE는 치료목적사용면책" in answer
    assert "공식 판정을 대체하지 않습니다" in answer
    assert "공식 문서에서 관련 근거 1개를 확인했습니다." in answer
    assert "경기기간 중 약물 사용" not in answer


def test_formatter_marks_english_source_as_korean_explanation() -> None:
    answer = format_answer(
        query="통지 절차를 설명해줘",
        decision=RouteDecision(route=ChatRoute.RAG, reason="rag"),
        retrieval_matches=[
            RetrievalMatch(rank=1, chunk_id="wada_isti_2023_en:p42:c0", distance=0.1,
                metadata=RetrievalMetadata(source_id="wada_isti_2023_en", title="ISTI", page=42, source_language="en"),
                text="The DCO shall establish the location of the selected Athlete.")
        ],
    )
    assert "WADA 영문 원문을 기준으로 한국어로 안내" in answer
    assert "The DCO shall establish" not in answer


def test_formatter_cites_official_source_for_human_reviewed_manual() -> None:
    answer = format_answer(
        query="ISTI 통지 절차를 설명해줘",
        decision=RouteDecision(route=ChatRoute.RAG, reason="rag"),
        retrieval_matches=[
            RetrievalMatch(
                rank=1,
                chunk_id="wada_isti_ko_human_reviewed:5.3.5:c0",
                distance=0.1,
                metadata=RetrievalMetadata(
                    source_id="wada_isti_ko_human_reviewed",
                    title="ISTI Korean Human-Reviewed Guide",
                    page=42,
                    section="5.3.5",
                    official_source_id="wada_isti_2023_en",
                    official_source_page=42,
                ),
                text="검수된 한국어 안내문입니다.",
            )
        ],
    )

    assert "검수된 한국어 안내문입니다." not in answer
    assert "wada_isti_ko_human_reviewed:5.3.5:c0" not in answer
