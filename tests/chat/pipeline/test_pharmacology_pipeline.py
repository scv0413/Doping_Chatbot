from app.chat.domain.drug_search.schemas import DrugRiskStatus, DrugSearchInput, DrugSearchResult
from app.chat.pipeline.chat_pipeline import run_chat_pipeline
from app.chat.domain.retrieval.schemas import RetrievalMatch, RetrievalMetadata
from app.chat.router.intent_router import ChatRoute


def fake_drug_searcher(search_input: DrugSearchInput) -> DrugSearchResult:
    return DrugSearchResult(
        status=DrugRiskStatus.PROHIBITED_POSSIBLE,
        input=search_input,
        matched_substances=["pseudoephedrine"],
        prohibited_categories=["S6_120"],
        requires_dose_confirmation=True,
        recommended_action="용량과 소변 농도 기준 확인 필요",
    )


def fake_retriever(query: str, top_k: int) -> list[RetrievalMatch]:
    assert "슈도에페드린" in query
    assert top_k == 3
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
            text="Pseudoephedrine is related to S6 stimulants and urinary threshold checks.",
        )
    ]


def test_pipeline_combines_drug_search_pharmacology_and_rag_manual() -> None:
    result = run_chat_pipeline(
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
    assert result.pharmacology_result.substance_name == "pseudoephedrine"
    assert result.retrieval_matches[0].source_id == "wada_prohibited_list_2026_ko"
    assert "## 반감기 참고" in result.answer
    assert "## 지금 확인해야 할 정보" in result.answer
    assert "## 도핑 규정상 주의" in result.answer
    assert "일반적 반감기 참고" in result.answer
    assert "검출 가능 시간이나 출전 가능 여부" in result.answer
    assert "추가로 알려주면 더 정확히 도와줄 정보" in result.answer
    assert "PubChem" in result.answer
