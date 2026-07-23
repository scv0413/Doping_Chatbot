from app.chat.domain.drug_search.schemas import (
    CompetitionPeriod,
    DrugRiskStatus,
    DrugSearchInput,
    DrugSearchResult,
)
from app.chat.orchestration.pipeline.chat_pipeline import (
    build_retrieval_query,
    run_chat_pipeline,
    should_run_drug_search,
    should_run_retrieval,
)
from app.chat.domain.retrieval.schemas import RetrievalMatch, RetrievalMetadata
from app.chat.orchestration.router.intent_router import ChatRoute, RouteDecision


def test_pipeline_runs_rag_only_flow_without_drug_search() -> None:
    drug_called = False

    def fake_drug_searcher(search_input: DrugSearchInput) -> DrugSearchResult:
        nonlocal drug_called
        drug_called = True
        raise AssertionError("drug search should not run")

    def fake_retriever(query: str, top_k: int) -> list[RetrievalMatch]:
        assert query == "도핑검사관 신분이 불분명하면 어떻게 확인해야 해?"
        assert top_k == 2
        return [
            RetrievalMatch(
                rank=1,
                chunk_id="field_response_manual:s1:c0",
                distance=0.2,
                metadata=RetrievalMetadata(
                    source_id="field_response_manual",
                    title="현장 대응 매뉴얼",
                ),
                text="검사관 신분이 불분명한 경우 확인, 기록, 동석 요청을 우선합니다.",
            )
        ]

    result = run_chat_pipeline(
        "도핑검사관 신분이 불분명하면 어떻게 확인해야 해?",
        top_k=2,
        use_llm=False,
        drug_searcher=fake_drug_searcher,
        retriever=fake_retriever,
        query_rewriter=lambda query: query,
    )

    assert result.decision.route is ChatRoute.RAG
    assert result.drug_result is None
    assert drug_called is False
    assert result.retrieval_matches[0].chunk_id == "field_response_manual:s1:c0"
    assert "확인, 기록, 동석 요청" in result.answer
    assert result.errors == []


def test_pipeline_runs_drug_search_with_rag_flow() -> None:
    search_input = DrugSearchInput(
        query="슈도에페드린 경기기간 중 먹어도 돼?",
        ingredient_name="슈도에페드린",
        competition_period=CompetitionPeriod.IN_COMPETITION,
    )

    def fake_drug_searcher(search_input: DrugSearchInput) -> DrugSearchResult:
        return DrugSearchResult(
            status=DrugRiskStatus.PROHIBITED_POSSIBLE,
            input=search_input,
            matched_substances=["pseudoephedrine"],
            prohibited_categories=["S6_120"],
            requires_dose_confirmation=True,
            recommended_action="용량 기준 확인 필요",
        )

    def fake_retriever(query: str, top_k: int) -> list[RetrievalMatch]:
        assert "pseudoephedrine" in query
        assert "S6_120" in query
        assert "흥분제" in query
        return [
            RetrievalMatch(
                rank=1,
                chunk_id="wada_prohibited_list_2026_ko:p17:c3",
                distance=0.3,
                metadata=RetrievalMetadata(
                    source_id="wada_prohibited_list_2026_ko",
                    title="금지목록 국제표준",
                    page=17,
                ),
                text="Pseudoephedrine is prohibited above a urinary threshold.",
            )
        ]

    result = run_chat_pipeline(
        search_input,
        use_llm=False,
        drug_searcher=fake_drug_searcher,
        retriever=fake_retriever,
        query_rewriter=lambda query: query,
    )

    assert result.decision.route is ChatRoute.DRUG_SEARCH_WITH_RAG
    assert result.drug_result is not None
    assert result.drug_result.requires_dose_confirmation is True
    assert result.retrieval_matches[0].chunk_id == "wada_prohibited_list_2026_ko:p17:c3"
    assert "금지 가능성 있음" in result.answer
    assert "용량 또는 농도 기준" in result.answer
    assert result.errors == []


def test_pipeline_keeps_answer_when_drug_search_fails() -> None:
    def broken_drug_searcher(search_input: DrugSearchInput) -> DrugSearchResult:
        raise RuntimeError("KADA temporary failure")

    result = run_chat_pipeline(
        DrugSearchInput(query="타이레놀 먹어도 돼?", product_name="타이레놀"),
        use_llm=False,
        drug_searcher=broken_drug_searcher,
    )

    assert result.decision.route is ChatRoute.DRUG_SEARCH
    assert result.drug_result is not None
    assert result.drug_result.status is DrugRiskStatus.NEEDS_VERIFICATION
    assert result.errors[0].stage == "drug_search"
    assert result.errors[0].error_type == "RuntimeError"
    assert "확인 필요" in result.answer


def test_pipeline_keeps_answer_when_retrieval_fails() -> None:
    def broken_retriever(query: str, top_k: int) -> list[RetrievalMatch]:
        raise RuntimeError("Chroma temporary failure")

    result = run_chat_pipeline(
        "TUE 신청 방법 알려줘",
        use_llm=False,
        retriever=broken_retriever,
    )

    assert result.decision.route is ChatRoute.RAG
    assert result.retrieval_matches == []
    assert result.errors[0].stage == "retrieval"
    assert "검색된 문서 근거가 없습니다" in result.answer


def test_pipeline_falls_back_to_raw_query_when_query_rewrite_fails() -> None:
    seen_query = ""

    def broken_query_rewriter(query: str) -> str:
        raise RuntimeError("rewrite temporary failure")

    def fake_retriever(query: str, top_k: int) -> list[RetrievalMatch]:
        nonlocal seen_query
        seen_query = query
        return [
            RetrievalMatch(
                rank=1,
                chunk_id="field_response_manual:s6:c0",
                distance=0.2,
                metadata=RetrievalMetadata(source_id="field_response_manual"),
                text="TUE 신청 방법",
            )
        ]

    result = run_chat_pipeline(
        "TUE 신청 방법 알려줘",
        use_llm=False,
        query_rewriter=broken_query_rewriter,
        retriever=fake_retriever,
    )

    assert seen_query == "TUE 신청 방법 알려줘"
    assert result.rewritten_query == "TUE 신청 방법 알려줘"
    assert result.errors[0].stage == "query_rewrite"
    assert "field_response_manual:s6:c0" in result.answer


def test_build_retrieval_query_only_expands_drug_routes() -> None:
    search_input = DrugSearchInput(query="TUE 신청 방법 알려줘")
    query = build_retrieval_query(
        search_input=search_input,
        decision=RouteDecision(route=ChatRoute.RAG, reason="rag"),
    )

    assert query == "TUE 신청 방법 알려줘"


def test_route_helpers() -> None:
    assert should_run_drug_search(RouteDecision(route=ChatRoute.DRUG_SEARCH, reason="drug"))
    assert should_run_drug_search(RouteDecision(route=ChatRoute.DRUG_SEARCH_WITH_RAG, reason="both"))
    assert not should_run_drug_search(RouteDecision(route=ChatRoute.RAG, reason="rag"))

    assert should_run_retrieval(RouteDecision(route=ChatRoute.RAG, reason="rag"))
    assert should_run_retrieval(RouteDecision(route=ChatRoute.DRUG_SEARCH_WITH_RAG, reason="both"))
    assert not should_run_retrieval(RouteDecision(route=ChatRoute.DRUG_SEARCH, reason="drug"))
