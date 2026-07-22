from app.chat.drug_search.schemas import DrugSearchInput
from app.chat.evals.langsmith_tool_eval import build_graph_tool_target, tool_contract_evaluator
from app.chat.pipeline.chat_pipeline import ChatPipelineResult
from app.chat.retrieval.schemas import RetrievalMatch, RetrievalMetadata
from app.chat.router.intent_router import ChatRoute, RouteDecision
from app.chat.tools.schemas import RagSearchResult, RagSearchToolOutput


def fake_tool_graph_runner(query: str, top_k: int, use_llm: bool, query_rewriter) -> ChatPipelineResult:
    assert query == "S0 비승인약물이 뭐야?"
    assert top_k == 3
    assert use_llm is False
    rewritten_query = query_rewriter(query)
    assert "상시 금지" in rewritten_query

    match = RetrievalMatch(
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
    tool_output = RagSearchToolOutput(
        query="S0 비승인약물 상시 금지",
        top_k=3,
        results=[
            RagSearchResult(
                rank=1,
                chunk_id=match.chunk_id,
                source_id=match.source_id,
                title=match.title,
                text=match.text,
                distance=match.distance,
                page=match.metadata.page,
            )
        ],
    )

    return ChatPipelineResult(
        search_input=DrugSearchInput(query=query),
        decision=RouteDecision(route=ChatRoute.RAG, reason="test", matched_terms=["S0"]),
        retrieval_query=query,
        rewritten_query="S0 비승인약물 상시 금지",
        rag_search_output=tool_output,
        retrieval_matches=[match],
        answer="S0은 비승인 약물입니다.",
        errors=[],
    )


def test_graph_tool_target_returns_tool_eval_shape() -> None:
    target = build_graph_tool_target(
        top_k=3,
        use_llm=False,
        graph_runner=fake_tool_graph_runner,
    )

    outputs = target({"query": "S0 비승인약물이 뭐야?", "retrieval_terms": ["상시 금지"]})

    assert outputs["actual_route"] == "rag"
    assert outputs["tool_name"] == "rag_search_tool"
    assert outputs["tool_result_count"] == 1
    assert outputs["tool_errors"] == []
    assert outputs["tool_chunk_ids"] == ["wada_prohibited_list_2026_ko:p5:c0"]
    assert outputs["chunk_ids"] == outputs["tool_chunk_ids"]
    assert outputs["source_ids"] == ["wada_prohibited_list_2026_ko"]


def test_tool_contract_evaluator_scores_tool_backed_rag_output() -> None:
    outputs = {
        "actual_route": "rag",
        "tool_name": "rag_search_tool",
        "tool_result_count": 1,
        "tool_errors": [],
        "chunk_ids": ["a:p1:c0"],
        "tool_chunk_ids": ["a:p1:c0"],
    }

    result = tool_contract_evaluator(outputs, {})

    assert result["key"] == "tool_contract"
    assert result["score"] == 1


def test_tool_contract_evaluator_fails_when_tool_chunks_diverge() -> None:
    outputs = {
        "actual_route": "rag",
        "tool_name": "rag_search_tool",
        "tool_result_count": 1,
        "tool_errors": [],
        "chunk_ids": ["a:p1:c0"],
        "tool_chunk_ids": ["b:p1:c0"],
    }

    result = tool_contract_evaluator(outputs, {})

    assert result["score"] == 0


def test_tool_contract_evaluator_accepts_drug_search_without_rag_tool() -> None:
    outputs = {
        "actual_route": "drug_search",
        "tool_name": None,
        "tool_result_count": 0,
        "tool_errors": [],
        "chunk_ids": [],
        "tool_chunk_ids": [],
    }

    result = tool_contract_evaluator(outputs, {})

    assert result["score"] == 1
