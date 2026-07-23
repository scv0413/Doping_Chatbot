from app.chat.domain.drug_search.schemas import DrugSearchInput
from app.chat.evals.langsmith_graph_eval import build_graph_retrieval_target
from app.chat.orchestration.pipeline.chat_pipeline import ChatPipelineResult
from app.chat.domain.retrieval.schemas import RetrievalMatch, RetrievalMetadata
from app.chat.orchestration.router.intent_router import ChatRoute, RouteDecision


def fake_graph_runner(query: str, top_k: int, use_llm: bool, query_rewriter) -> ChatPipelineResult:
    assert query == "S0 비승인약물이 뭐야?"
    assert top_k == 3
    assert use_llm is False
    rewritten_query = query_rewriter(query)
    assert "S0" in rewritten_query

    return ChatPipelineResult(
        search_input=DrugSearchInput(query=query),
        decision=RouteDecision(route=ChatRoute.RAG, reason="test", matched_terms=["S0"]),
        retrieval_query=query,
        rewritten_query="S0 비승인약물 상시 금지",
        retrieval_matches=[
            RetrievalMatch(
                rank=1,
                chunk_id="wada_prohibited_list_2026_ko:p5:c0",
                distance=0.2,
                metadata=RetrievalMetadata(
                    source_id="wada_prohibited_list_2026_ko",
                    title="금지목록 국제표준",
                    page=5,
                ),
                text="S0 비승인 약물 상시 금지",
            )
        ],
        answer=(
            "## 답변 요약\n"
            "S0은 비승인 약물입니다.\n"
            "## 근거\n"
            "- `wada_prohibited_list_2026_ko:p5:c0`"
        ),
        errors=[],
    )


def test_graph_retrieval_target_returns_langsmith_eval_shape() -> None:
    target = build_graph_retrieval_target(
        top_k=3,
        use_llm=False,
        graph_runner=fake_graph_runner,
    )

    outputs = target({"query": "S0 비승인약물이 뭐야?", "retrieval_terms": ["상시 금지"]})

    assert outputs["actual_route"] == "rag"
    assert outputs["source_ids"] == ["wada_prohibited_list_2026_ko"]
    assert outputs["chunk_ids"] == ["wada_prohibited_list_2026_ko:p5:c0"]
    assert outputs["context_chars"] > 0
    assert outputs["answer_chars"] > 0
    assert outputs["errors"] == []
    assert outputs["error"] is None
