import pytest
from pydantic import ValidationError

from app.chat.domain.drug_search.schemas import DrugCandidate, DrugRiskStatus, DrugSearchInput, DrugSearchResult, MatchType
from app.chat.domain.retrieval.schemas import RetrievalMatch, RetrievalMetadata
from app.chat.runtime import ChatEngine, ChatRequest, ChatRuntimeDependencies, run_chat


def fake_retriever(query: str, top_k: int) -> list[RetrievalMatch]:
    assert top_k == 2
    return [
        RetrievalMatch(
            rank=1,
            chunk_id="field_response_manual:s1:c0",
            distance=0.2,
            metadata=RetrievalMetadata(
                source_id="field_response_manual",
                title="현장 대응 매뉴얼",
                page=None,
            ),
            text=(
                "검사관 신분 확인, 소속 확인, 절차 설명 요청, 기록, 동석 요청. "
                "공식 절차 확인 전에는 무단 거부로 보일 행동을 피해야 한다. "
                "선수는 검사관의 신분증과 통지 내용을 정중히 확인하고, 통역이나 팀 관계자 동석을 요청할 수 있다."
            ),
        )
    ]


def identity_rewriter(query: str) -> str:
    return query


def test_run_chat_uses_graph_engine_by_default() -> None:
    response = run_chat(
        ChatRequest(
            query="도핑 검사관 신분이 불분명하면 어떻게 확인해야 해?",
            top_k=2,
            use_llm=False,
        ),
        dependencies=ChatRuntimeDependencies(
            retriever=fake_retriever,
            query_rewriter=identity_rewriter,
        ),
    )

    assert response.engine is ChatEngine.GRAPH
    assert response.route == "rag"
    assert response.citations[0].chunk_id == "field_response_manual:s1:c0"
    assert response.retrieval_attempts == 1
    assert response.errors == []
    assert "확인" in response.answer


def test_run_chat_exposes_kada_herbal_verification_unavailable() -> None:
    def herbal_searcher(search_input: DrugSearchInput) -> DrugSearchResult:
        return DrugSearchResult(
            status=DrugRiskStatus.NEEDS_VERIFICATION,
            input=search_input,
            herbal_verification_unavailable=True,
            recommended_action="생약성분 포함 의약품 금지여부 확인 불가",
        )

    response = run_chat(
        ChatRequest(query="감초 먹어도 돼?", use_llm=False),
        dependencies=ChatRuntimeDependencies(drug_searcher=herbal_searcher),
    )

    assert response.herbal_verification_unavailable is True
    assert response.drug_detail is None


def test_run_chat_applies_runtime_policy_when_options_are_omitted() -> None:
    response = run_chat(
        ChatRequest(query="슈도에페드린 반감기가 얼마나 돼? 경기 전날 먹었으면 괜찮아?"),
        dependencies=ChatRuntimeDependencies(
            retriever=fake_retriever,
            query_rewriter=identity_rewriter,
        ),
    )

    assert response.engine is ChatEngine.GRAPH
    assert response.top_k == 3
    assert response.use_llm is False
    assert "half_life_safety_baseline_formatter" in response.policy_matched_rules
    assert response.planned_tool_names == [
        "drug_search_tool",
        "pharmacology_info_tool",
        "rag_search_tool",
    ]


def test_run_chat_can_use_pipeline_engine() -> None:
    response = run_chat(
        ChatRequest(
            query="도핑 검사관 신분이 불분명하면 어떻게 확인해야 해?",
            top_k=2,
            use_llm=False,
            engine=ChatEngine.PIPELINE,
        ),
        dependencies=ChatRuntimeDependencies(
            retriever=fake_retriever,
            query_rewriter=identity_rewriter,
        ),
    )

    assert response.engine is ChatEngine.PIPELINE
    assert response.route == "rag"
    assert response.retrieval_attempts == 1
    assert response.citations[0].source_id == "field_response_manual"


def test_run_chat_accepts_plain_string_and_drug_search_input() -> None:
    string_response = run_chat(
        "도핑 검사관 신분이 불분명하면 어떻게 확인해야 해?",
        dependencies=ChatRuntimeDependencies(
            retriever=fake_retriever,
            query_rewriter=identity_rewriter,
        ),
    )
    input_response = run_chat(
        DrugSearchInput(query="도핑 검사관 신분이 불분명하면 어떻게 확인해야 해?"),
        dependencies=ChatRuntimeDependencies(
            retriever=fake_retriever,
            query_rewriter=identity_rewriter,
        ),
    )

    assert string_response.query == input_response.query
    assert string_response.route == input_response.route



def test_run_chat_preserves_selected_product_for_graph_drug_search() -> None:
    seen_input: DrugSearchInput | None = None

    def fake_drug_searcher(search_input: DrugSearchInput):
        nonlocal seen_input
        seen_input = search_input
        from app.chat.domain.drug_search.schemas import DrugRiskStatus, DrugSearchResult

        return DrugSearchResult(
            status=DrugRiskStatus.NEEDS_VERIFICATION,
            input=search_input,
            recommended_action="KADA 결과를 확인하세요.",
        )

    run_chat(
        ChatRequest(
            query="경기 중 타이레놀 먹어도 돼?",
            product_name="타이레놀8시간이알서방정",
            use_llm=False,
        ),
        dependencies=ChatRuntimeDependencies(drug_searcher=fake_drug_searcher),
    )

    assert seen_input is not None
    assert seen_input.product_name == "타이레놀8시간이알서방정"


def test_run_chat_exposes_kada_product_candidates_for_ui_selection() -> None:
    from app.chat.domain.drug_search.schemas import DrugRiskStatus, DrugSearchResult

    def fake_drug_searcher(search_input: DrugSearchInput) -> DrugSearchResult:
        return DrugSearchResult(
            status=DrugRiskStatus.NEEDS_VERIFICATION,
            input=search_input,
            matched_candidates=[
                DrugCandidate(
                    name="타이레놀8시간이알서방정",
                    match_type=MatchType.PRODUCT,
                    ingredient_names=["Acetaminophen 325mg"],
                    manufacturer="한국존슨앤드존슨판매",
                )
            ],
            requires_product_selection=True,
            recommended_action="정확한 제품을 선택하세요.",
        )

    response = run_chat(
        ChatRequest(query="타이레놀 먹어도 돼?", use_llm=False),
        dependencies=ChatRuntimeDependencies(drug_searcher=fake_drug_searcher),
    )

    assert response.requires_product_selection is True
    assert response.product_candidates[0].name == "타이레놀8시간이알서방정"
    assert response.product_candidates[0].ingredient_names == ["Acetaminophen 325mg"]

def test_chat_request_validates_query_and_top_k() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(query="")

    with pytest.raises(ValidationError):
        ChatRequest(query="질문", top_k=0)

    with pytest.raises(ValidationError):
        ChatRequest(query="질문", top_k=11)


def test_run_chat_exposes_selected_kada_drug_detail_for_product_card() -> None:
    from app.chat.domain.drug_search.schemas import KADADrugDetail, DrugRiskStatus, DrugSearchResult

    def fake_drug_searcher(search_input: DrugSearchInput) -> DrugSearchResult:
        assert search_input.drug_code == "2009092800048"
        return DrugSearchResult(
            status=DrugRiskStatus.LOW_RISK,
            input=search_input,
            selected_product_detail=KADADrugDetail(
                drug_code="2009092800048",
                product_name="스트렙실허니앤레몬트로키, 스트렙실오렌지트로키",
                ingredients=["플루르비프로펜 8.75mg"],
                in_competition_status="허용",
                out_of_competition_status="허용",
                pill_image_url="https://example.com/pill.jpg",
                package_image_url="https://example.com/package.jpg",
                dosage="필요시 3~6시간 간격으로 복용",
                source_url="https://kada.health.kr/result_drug_kpic?drug_code=2009092800048&herbal=0",
                retrieved_at="2026-07-23T00:00:00+00:00",
            ),
            recommended_action="KADA 결과를 확인하세요.",
        )

    response = run_chat(
        ChatRequest(
            query="경기 중 스트렙실 먹어도 돼?",
            product_name="스트렙실허니앤레몬트로키",
            drug_code="2009092800048",
            use_llm=False,
        ),
        dependencies=ChatRuntimeDependencies(drug_searcher=fake_drug_searcher),
    )

    assert response.drug_detail is not None
    assert response.drug_detail.in_competition_status == "허용"
    assert response.drug_detail.pill_image_url == "https://example.com/pill.jpg"
