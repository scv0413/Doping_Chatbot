from app.chat.domain.answer.formatter import format_answer
from app.chat.domain.drug_search.schemas import (
    DrugCandidate,
    DrugRiskStatus,
    DrugSearchInput,
    DrugSearchResult,
    MatchType,
)
from app.chat.domain.retrieval.schemas import RetrievalMatch, RetrievalMetadata
from app.chat.orchestration.router.intent_router import ChatRoute, RouteDecision


def test_drug_answer_shows_product_candidates_in_combined_findings_section() -> None:
    result = DrugSearchResult(
        status=DrugRiskStatus.NEEDS_VERIFICATION,
        input=DrugSearchInput(query="타이레놀 먹어도 돼?", product_name="타이레놀"),
        matched_candidates=[
            DrugCandidate(
                name="타이레놀8시간이알서방정",
                match_type=MatchType.PRODUCT,
                ingredient_names=["Acetaminophen 325mg"],
                manufacturer="한국존슨앤드존슨판매",
            ),
        ],
        requires_product_selection=True,
        recommended_action="정확한 제품을 선택하세요.",
    )

    answer = format_answer(
        query=result.input.query,
        decision=RouteDecision(route=ChatRoute.DRUG_SEARCH, reason="drug"),
        drug_result=result,
    )

    assert "## 확인 결과와 근거 핵심" in answer
    assert "타이레놀8시간이알서방정" in answer
    assert "Acetaminophen 325mg" in answer
    assert "## 근거 핵심" not in answer
    assert "## 근거\n" not in answer


def test_rag_answer_does_not_show_internal_chunk_id_in_user_facing_findings() -> None:
    answer = format_answer(
        query="도핑검사를 거부하면 어떻게 돼?",
        decision=RouteDecision(route=ChatRoute.RAG, reason="rag"),
        retrieval_matches=[
            RetrievalMatch(
                rank=1,
                chunk_id="field_response_manual:s3:c0",
                distance=0.1,
                metadata=RetrievalMetadata(
                    source_id="field_response_manual",
                    title="현장 대응 매뉴얼",
                ),
                text="정당한 사유 없이 시료채취를 거부하면 규정 위반으로 이어질 수 있습니다.",
            )
        ],
    )

    assert "field_response_manual:s3:c0" not in answer
    assert "정당한 사유 없이 시료채취를 거부하면" not in answer
    assert "검사 거부 또는 방해로 오해될 수 있으므로 피합니다." in answer


def test_general_doping_control_answer_is_concise_without_raw_chunk_markdown() -> None:
    answer = format_answer(
        query="도핑검사할 때 뭐해?",
        decision=RouteDecision(route=ChatRoute.RAG, reason="rag"),
        retrieval_matches=[
            RetrievalMatch(
                rank=1,
                chunk_id="manual:s1:c0",
                distance=0.1,
                metadata=RetrievalMetadata(source_id="manual", title="현장 대응 매뉴얼"),
                text="### 사용자 질문 예시 - 도핑검사를 거부하면 어떤 불이익이 있나요?",
            )
        ],
    )

    assert "도핑검사는 선수의 소변 또는 혈액 등 시료를 채취하여" in answer
    assert "### 사용자 질문 예시" not in answer
    assert "manual source" not in answer


def test_urine_collection_answer_distinguishes_volume_and_hydration_rules() -> None:
    answer = format_answer(
        query="검사 전에 오줌을 눴는데 어떻게 해? 소변이 안 나오면?",
        decision=RouteDecision(route=ChatRoute.RAG, reason="rag"),
        retrieval_matches=[
            RetrievalMatch(
                rank=1,
                chunk_id="wada_isti_2023_en:p71:c2",
                distance=0.1,
                metadata=RetrievalMetadata(
                    source_id="wada_isti_2023_en",
                    title="WADA International Standard for Testing and Investigations 2023",
                ),
                text="The Athlete shall remain under continuous observation and be given the opportunity to hydrate.",
            )
        ],
    )

    assert "통지 후 소변을 이미 봤다면" in answer
    assert "임의로 물을 계속 마시지 말고" in answer
    assert "부분 시료" in answer
    assert "물을 계속 마시면 된다" not in answer


def test_bathroom_request_answer_requires_approval_and_continuous_observation() -> None:
    answer = format_answer(
        query="검사 도중 대변이 마려우면 어떻게 해야 해?",
        decision=RouteDecision(route=ChatRoute.RAG, reason="rag"),
        retrieval_matches=[
            RetrievalMatch(
                rank=1,
                chunk_id="wada_isti_2023_en:p50:c2",
                distance=0.1,
                metadata=RetrievalMetadata(
                    source_id="wada_isti_2023_en",
                    title="WADA International Standard for Testing and Investigations 2023",
                ),
                text="The Athlete must remain under continuous observation throughout.",
            )
        ],
    )

    assert "대변을 보고 싶으면 즉시 검사관에게 알립니다." in answer
    assert "검사관 승인" in answer
    assert "지속 관찰" in answer
    assert "혼자 현장을 떠나지 않습니다." in answer


def test_urine_requirements_answer_shows_volume_and_specific_gravity_thresholds() -> None:
    answer = format_answer(
        query="오줌은 몇 ml 이상 나와야 검사로 인정돼? 농도는?",
        decision=RouteDecision(route=ChatRoute.RAG, reason="rag"),
        retrieval_matches=[
            RetrievalMatch(
                rank=1,
                chunk_id="wada_isti_2023_en:p16:c0",
                distance=0.1,
                metadata=RetrievalMetadata(
                    source_id="wada_isti_2023_en",
                    title="WADA International Standard for Testing and Investigations 2023",
                ),
                text="Suitable Volume of Urine for Analysis: A minimum of 90 mL.",
            )
        ],
    )

    assert "선수는 이 숫자를 직접 재거나 외울 필요는 없습니다." in answer
    assert "소변 양이 적을수록 농도 기준이 더 엄격" in answer
    assert "1.005 이상" not in answer
    assert "1.010 이상" not in answer
    assert "1.003 이상" not in answer
    assert "B 용기에 최소 30 mL, A 용기에 최소 60 mL" in answer
    assert "최종 판단은 검사실 측정값" in answer


def test_specific_gravity_explanation_is_easy_to_understand() -> None:
    answer = format_answer(
        query="굴절계 기준 비중 1.003 이상이 뭐야?",
        decision=RouteDecision(route=ChatRoute.RAG, reason="rag"),
        retrieval_matches=[
            RetrievalMatch(
                rank=1,
                chunk_id="wada_isti_2023_en:p16:c0",
                distance=0.1,
                metadata=RetrievalMetadata(
                    source_id="wada_isti_2023_en",
                    title="WADA International Standard for Testing and Investigations 2023",
                ),
                text="For Samples with a volume of 150 mL and above, specific gravity measured at 1.003 or higher with a refractometer only.",
            )
        ],
    )

    assert "소변이 지나치게 묽지 않은지" in answer
    assert "150 mL 이상" in answer
    assert "1.003 이상" in answer
    assert "도핑 음성이나 사용 가능을 뜻하지는 않습니다." in answer
