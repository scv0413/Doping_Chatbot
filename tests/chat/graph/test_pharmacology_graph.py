from app.chat.drug_search.schemas import DrugRiskStatus, DrugSearchInput, DrugSearchResult
from app.chat.graph.graph import run_chat_graph
from app.chat.pharmacology.schemas import PharmacologyInfoResult
from app.chat.retrieval.schemas import RetrievalMatch, RetrievalMetadata
from app.chat.router.intent_router import ChatRoute


def fake_drug_searcher(search_input: DrugSearchInput) -> DrugSearchResult:
    return DrugSearchResult(
        status=DrugRiskStatus.PROHIBITED_POSSIBLE,
        input=search_input,
        matched_substances=["pseudoephedrine"],
        prohibited_categories=["S6_120"],
        requires_dose_confirmation=True,
        recommended_action="용량 확인 필요",
    )


def fake_retriever(query: str, top_k: int) -> list[RetrievalMatch]:
    return [
        RetrievalMatch(
            rank=1,
            chunk_id="wada_prohibited_list_2026_ko:p17:c3",
            distance=0.2,
            metadata=RetrievalMetadata(
                source_id="wada_prohibited_list_2026_ko",
                title="금지목록 국제표준",
                page=17,
            ),
            text=(
                "Pseudoephedrine is listed in the S6 stimulant context and requires urinary threshold, "
                "dose, timing, product, and ingredient confirmation during the in-competition period."
            ),
        )
    ]


def test_graph_combines_drug_search_pharmacology_and_rag_manual() -> None:
    result = run_chat_graph(
        "슈도에페드린 반감기가 얼마나 돼?",
        top_k=3,
        use_llm=False,
        drug_searcher=fake_drug_searcher,
        retriever=fake_retriever,
        query_rewriter=lambda query: query,
    )

    assert result.decision.route is ChatRoute.DRUG_SEARCH_WITH_RAG
    assert result.drug_result is not None
    assert result.pharmacology_result is not None
    assert result.pharmacology_info_tool_output is not None
    assert result.pharmacology_info_tool_output.tool_name == "pharmacology_info_tool"
    assert result.pharmacology_info_tool_output.result is not None
    assert result.pharmacology_result.substance_name == "pseudoephedrine"
    assert result.retrieval_attempts == 1
    assert "반감기" in result.answer


def test_graph_preserves_pharmacology_tool_error_stage() -> None:
    def broken_pharmacology_searcher(query: str) -> PharmacologyInfoResult:
        raise RuntimeError("pharmacology unavailable")

    result = run_chat_graph(
        "슈도에페드린 반감기가 얼마나 돼?",
        top_k=3,
        use_llm=False,
        drug_searcher=fake_drug_searcher,
        retriever=fake_retriever,
        query_rewriter=lambda query: query,
        pharmacology_searcher=broken_pharmacology_searcher,
    )

    assert result.pharmacology_result is None
    assert result.pharmacology_info_tool_output is not None
    assert result.pharmacology_info_tool_output.result is None
    assert result.pharmacology_info_tool_output.errors[0].stage == "pharmacology_info"
    assert result.errors[0].stage == "pharmacology_info"
    assert result.errors[0].error_type == "RuntimeError"
