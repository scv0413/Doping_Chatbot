from app.chat.runtime import (
    ChatEngine,
    ChatRequest,
    ChatResponse,
    CitationSummary,
    DrugCandidateSummary,
    KADADrugDetail,
    PharmacologyIngredientSummary,
)
from app.chat.interfaces.ui.gradio_app import (
    build_demo,
    format_citations,
    format_metadata,
    format_product_candidate_choices,
    build_selected_product_request,
    format_answer_for_ui,
    format_drug_detail_card,
    format_product_pharmacology_card,
    respond,
)


def fake_runner(request: ChatRequest) -> ChatResponse:
    assert request.query == "S0 비승인약물이 뭐야?"
    assert request.top_k is None
    assert request.use_llm is None
    assert request.engine is None
    return ChatResponse(
        answer="S0은 비승인 약물입니다.",
        route="rag",
        query=request.query,
        engine=ChatEngine.GRAPH,
        top_k=3,
        use_llm=False,
        citations=[
            CitationSummary(
                chunk_id="wada_prohibited_list_2026_ko:p5:c0",
                source_id="wada_prohibited_list_2026_ko",
                title="금지목록 국제표준",
                page=5,
                distance=0.2,
            )
        ],
        retrieval_attempts=1,
    )


def test_respond_returns_answer_and_citations_with_runtime_policy_defaults() -> None:
    answer, citations = respond(" S0 비승인약물이 뭐야? ", runner=fake_runner)

    assert "S0" in answer
    assert citations == ""



def test_format_answer_for_ui_prioritizes_kada_herbal_unavailable_warning() -> None:
    response = ChatResponse(
        answer="일반 약물 결과",
        route="drug_search",
        query="감초 먹어도 돼?",
        engine=ChatEngine.GRAPH,
        herbal_verification_unavailable=True,
        product_candidates=[
            DrugCandidateSummary(name="작약감초탕", drug_code="herbal-1"),
        ],
    )

    answer = format_answer_for_ui(response)

    assert "생약성분 포함 의약품 금지여부 확인 불가" in answer
    assert "경기기간 중: 허용" not in answer
    assert "일반 약물 결과" not in answer


def test_format_product_candidate_choices_uses_product_and_ingredient_details() -> None:
    response = ChatResponse(
        answer="답변",
        route="drug_search",
        query="타이레놀 먹어도 돼?",
        engine=ChatEngine.GRAPH,
        requires_product_selection=True,
        product_candidates=[
            DrugCandidateSummary(
                name="타이레놀8시간이알서방정",
                ingredient_names=["Acetaminophen 325mg"],
                manufacturer="한국존슨앤드존슨판매",
            )
        ],
    )

    assert format_product_candidate_choices(response) == [
        ("타이레놀8시간이알서방정 | Acetaminophen 325mg | 한국존슨앤드존슨판매", "타이레놀8시간이알서방정")
    ]

def test_respond_handles_empty_query() -> None:
    answer, citations = respond("   ", runner=fake_runner)

    assert answer == "질문을 입력해주세요."
    assert citations == ""


def test_format_helpers_handle_no_citations() -> None:
    response = ChatResponse(
        answer="답변",
        route="drug_search",
        query="타이레놀 먹어도 돼?",
        engine=ChatEngine.GRAPH,
    )

    assert format_citations(response) == "검색된 문서 근거가 없습니다."
    assert "drug_search" in format_metadata(response)


def test_build_demo_creates_gradio_blocks() -> None:
    demo = build_demo(runner=fake_runner)

    assert demo is not None
    assert hasattr(demo, "launch")


def test_respond_does_not_expose_internal_runtime_metadata() -> None:
    answer, citations = respond("S0 비승인약물이 뭐야?", runner=fake_runner)
    combined = answer + "\n" + citations

    assert "engine" not in combined
    assert "top_k" not in combined
    assert "use_llm" not in combined
    assert "retrieval_attempts" not in combined


def test_format_citations_shows_official_source_for_reviewed_manual() -> None:
    response = ChatResponse(
        answer="답변",
        route="rag",
        query="통지 절차",
        engine=ChatEngine.GRAPH,
        citations=[
            CitationSummary(
                chunk_id="wada_isti_ko_human_reviewed:5.3.5:c0",
                source_id="wada_isti_ko_human_reviewed",
                title="ISTI Korean Human-Reviewed Guide",
                page=42,
                distance=0.1,
                official_source_id="wada_isti_2023_en",
                official_source_page=42,
            )
        ],
    )

    citations = format_citations(response)

    assert "ISTI Korean Human-Reviewed Guide, p.42" in citations
    assert "원문: `wada_isti_2023_en`, p.42" in citations


def test_selected_product_request_keeps_kada_drug_code() -> None:
    candidate = DrugCandidateSummary(
        name="스트렙실오렌지트로키",
        ingredient_names=["Flurbiprofen 8.75mg"],
        drug_code="2009092800048",
    )

    request = build_selected_product_request("경기 중 스트랩실 먹어도 돼?", candidate)

    assert request.product_name == "스트렙실오렌지트로키"
    assert request.drug_code == "2009092800048"


def test_format_drug_detail_card_shows_only_kada_product_fields() -> None:
    detail = KADADrugDetail(
        drug_code="2009092800048",
        product_name="스트렙실오렌지트로키",
        ingredients=["플루르비프로펜 8.75mg"],
        in_competition_status="허용",
        out_of_competition_status="허용",
        pill_image_url="https://example.com/pill.jpg",
        package_image_url="https://example.com/package.jpg",
        dosage="필요시 3~6시간 간격으로 복용",
        doping_notices=["코 스프레이로 사용하는 것은 예외적으로 허용됩니다."],
        source_url="https://kada.health.kr/result_drug_kpic?drug_code=2009092800048&herbal=0",
        retrieved_at="2026-07-23T00:00:00+00:00",
    )

    card = format_drug_detail_card(detail)

    assert "스트렙실오렌지트로키" in card
    assert "경기기간 중: 허용" in card
    assert "경기기간 외: 허용" in card
    assert "https://example.com/pill.jpg" in card
    assert "복용법 · 용량" in card
    assert "필요시 3~6시간 간격으로 복용" in card
    assert "정보확인" in card
    assert "코 스프레이로 사용하는 것은 예외적으로 허용됩니다." in card
    assert "제조사" not in card


def test_format_drug_detail_card_uses_status_specific_badges() -> None:
    detail = KADADrugDetail(
        drug_code="test",
        product_name="옥시메타졸린염산염",
        in_competition_status="금지",
        out_of_competition_status="허용",
        source_url="https://kada.health.kr/result_drug_kpic?drug_code=test&herbal=0",
        retrieved_at="2026-07-23T00:00:00+00:00",
    )

    card = format_drug_detail_card(detail)

    assert "drug-card__status--prohibited" in card
    assert "drug-card__status--allowed" in card


def test_format_answer_for_ui_hides_rag_text_while_product_selection_is_needed() -> None:
    response = ChatResponse(
        answer="## 확인 결과와 근거 핵심\n- 긴 규정 원문",
        route="drug_search_with_rag",
        query="경기기간 중 스트렙실 먹어도 돼?",
        engine=ChatEngine.GRAPH,
        requires_product_selection=True,
        product_candidates=[
            DrugCandidateSummary(
                name="스트렙실오렌지트로키",
                drug_code="2009092800048",
            )
        ],
    )

    assert format_answer_for_ui(response) == ""


def test_format_answer_for_ui_hides_rag_text_after_selected_drug_card_is_available() -> None:
    response = ChatResponse(
        answer="## 행동 지침\n- 긴 규정 원문",
        route="drug_search_with_rag",
        query="경기기간 중 스트렙실 먹어도 돼?",
        engine=ChatEngine.GRAPH,
        drug_detail=KADADrugDetail(
            drug_code="2009092800048",
            product_name="스트렙실오렌지트로키",
            ingredients=["플루르비프로펜 8.75mg"],
            in_competition_status="허용",
            out_of_competition_status="허용",
            dosage="필요시 3~6시간 간격으로 복용",
            doping_notices=["코 스프레이로 사용하는 것은 예외적으로 허용됩니다."],
            source_url="https://kada.health.kr/result_drug_kpic?drug_code=2009092800048&herbal=0",
            retrieved_at="2026-07-23T00:00:00+00:00",
        ),
    )

    assert format_answer_for_ui(response) == ""


def test_format_product_pharmacology_card_shows_each_registered_ingredient() -> None:
    response = ChatResponse(
        answer="긴 RAG 원문",
        route="drug_search_with_rag",
        query="캐롤비콜드 반감기는?",
        engine=ChatEngine.GRAPH,
        drug_detail=KADADrugDetail(
            drug_code="2018062800008",
            product_name="캐롤비콜드연질캡슐",
            in_competition_status="금지",
            out_of_competition_status="허용",
            source_url="https://kada.health.kr/result_drug_kpic?drug_code=2018062800008&herbal=0",
            retrieved_at="2026-07-24T00:00:00+00:00",
        ),
        pharmacology_status="found",
        pharmacology_ingredients=[
            PharmacologyIngredientSummary(
                substance_name="pseudoephedrine",
                typical_range="대략 4-8시간 범위",
            ),
            PharmacologyIngredientSummary(
                substance_name="methylephedrine",
                typical_range="대략 3-6시간 범위",
            ),
        ],
    )

    card = format_product_pharmacology_card(response)

    assert "성분별 반감기 참고" in card
    assert "pseudoephedrine" in card
    assert "methylephedrine" in card
    assert "출전 가능 여부를 확정하지 않습니다" in card
    assert format_answer_for_ui(response) == ""


def test_format_product_pharmacology_card_explains_when_no_registered_data_exists() -> None:
    response = ChatResponse(
        answer="긴 RAG 원문",
        route="drug_search_with_rag",
        query="알 수 없는 제품 반감기는?",
        engine=ChatEngine.GRAPH,
        drug_detail=KADADrugDetail(
            drug_code="unknown",
            product_name="알 수 없는 제품",
            source_url="https://kada.health.kr/result_drug_kpic?drug_code=unknown&herbal=0",
            retrieved_at="2026-07-24T00:00:00+00:00",
        ),
        pharmacology_status="not_found",
    )

    card = format_product_pharmacology_card(response)

    assert "현재 등록된 성분별 반감기 근거가 없습니다" in card
    assert "긴 RAG 원문" not in card
