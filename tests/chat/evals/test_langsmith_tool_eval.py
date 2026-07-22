from app.chat.drug_search.schemas import DrugRiskStatus, DrugSearchInput, DrugSearchResult
from app.chat.evals.langsmith_tool_eval import build_graph_tool_target, tool_contract_evaluator
from app.chat.pipeline.chat_pipeline import ChatPipelineResult
from app.chat.retrieval.schemas import RetrievalMatch, RetrievalMetadata
from app.chat.router.intent_router import ChatRoute, RouteDecision
from app.chat.tools.schemas import DrugSearchToolOutput, RagSearchResult, RagSearchToolOutput


def build_sample_match() -> RetrievalMatch:
    return RetrievalMatch(
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


def build_sample_rag_output(match: RetrievalMatch) -> RagSearchToolOutput:
    return RagSearchToolOutput(
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


def build_sample_drug_output(query: str) -> DrugSearchToolOutput:
    search_input = DrugSearchInput(query=query, ingredient_name="슈도에페드린")
    return DrugSearchToolOutput(
        query=query,
        result=DrugSearchResult(
            status=DrugRiskStatus.PROHIBITED_POSSIBLE,
            input=search_input,
            matched_substances=["슈도에페드린"],
            prohibited_categories=["S6_120"],
            requires_dose_confirmation=True,
            recommended_action="금지 가능성이 확인됩니다.",
        ),
    )


def fake_tool_graph_runner(query: str, top_k: int, use_llm: bool, query_rewriter) -> ChatPipelineResult:
    assert top_k == 3
    assert use_llm is False
    rewritten_query = query_rewriter(query)
    match = build_sample_match()

    if "슈도에페드린" in query:
        return ChatPipelineResult(
            search_input=DrugSearchInput(query=query, ingredient_name="슈도에페드린"),
            decision=RouteDecision(
                route=ChatRoute.DRUG_SEARCH_WITH_RAG,
                reason="test",
                matched_terms=["슈도에페드린"],
            ),
            drug_result=build_sample_drug_output(query).result,
            drug_search_tool_output=build_sample_drug_output(query),
            retrieval_query=query,
            rewritten_query=rewritten_query,
            rag_search_output=build_sample_rag_output(match),
            retrieval_matches=[match],
            answer="슈도에페드린은 경기기간 중 주의가 필요합니다.",
            errors=[],
        )

    return ChatPipelineResult(
        search_input=DrugSearchInput(query=query),
        decision=RouteDecision(route=ChatRoute.RAG, reason="test", matched_terms=["S0"]),
        retrieval_query=query,
        rewritten_query=rewritten_query,
        rag_search_output=build_sample_rag_output(match),
        retrieval_matches=[match],
        answer="S0은 비승인 약물입니다.",
        errors=[],
    )


def test_graph_tool_target_returns_rag_and_drug_tool_eval_shape() -> None:
    target = build_graph_tool_target(
        top_k=3,
        use_llm=False,
        graph_runner=fake_tool_graph_runner,
    )

    outputs = target({"query": "슈도에페드린 경기기간 중 먹어도 돼?", "retrieval_terms": ["상시 금지"]})

    assert outputs["actual_route"] == "drug_search_with_rag"
    assert outputs["rag_tool_name"] == "rag_search_tool"
    assert outputs["rag_tool_result_count"] == 1
    assert outputs["rag_tool_errors"] == []
    assert outputs["rag_tool_chunk_ids"] == ["wada_prohibited_list_2026_ko:p5:c0"]
    assert outputs["chunk_ids"] == outputs["rag_tool_chunk_ids"]
    assert outputs["drug_tool_name"] == "drug_search_tool"
    assert outputs["drug_tool_status"] == "prohibited_possible"
    assert outputs["drug_tool_matched_substances"] == ["슈도에페드린"]
    assert outputs["drug_tool_prohibited_categories"] == ["S6_120"]


def test_tool_contract_evaluator_scores_rag_only_output() -> None:
    outputs = {
        "actual_route": "rag",
        "rag_tool_name": "rag_search_tool",
        "rag_tool_result_count": 1,
        "rag_tool_errors": [],
        "chunk_ids": ["a:p1:c0"],
        "rag_tool_chunk_ids": ["a:p1:c0"],
        "drug_tool_name": None,
        "drug_tool_status": None,
        "drug_tool_errors": [],
    }

    result = tool_contract_evaluator(outputs, {})

    assert result["key"] == "tool_contract"
    assert result["score"] == 1


def test_tool_contract_evaluator_scores_drug_search_only_output() -> None:
    outputs = {
        "actual_route": "drug_search",
        "rag_tool_name": None,
        "rag_tool_result_count": 0,
        "rag_tool_errors": [],
        "chunk_ids": [],
        "rag_tool_chunk_ids": [],
        "drug_tool_name": "drug_search_tool",
        "drug_tool_status": "needs_verification",
        "drug_tool_errors": [],
    }

    result = tool_contract_evaluator(outputs, {})

    assert result["score"] == 1


def test_tool_contract_evaluator_scores_drug_search_with_rag_output() -> None:
    outputs = {
        "actual_route": "drug_search_with_rag",
        "rag_tool_name": "rag_search_tool",
        "rag_tool_result_count": 1,
        "rag_tool_errors": [],
        "chunk_ids": ["a:p1:c0"],
        "rag_tool_chunk_ids": ["a:p1:c0"],
        "drug_tool_name": "drug_search_tool",
        "drug_tool_status": "prohibited_possible",
        "drug_tool_errors": [],
    }

    result = tool_contract_evaluator(outputs, {})

    assert result["score"] == 1


def test_tool_contract_evaluator_fails_when_required_drug_tool_is_missing() -> None:
    outputs = {
        "actual_route": "drug_search",
        "rag_tool_name": None,
        "rag_tool_result_count": 0,
        "rag_tool_errors": [],
        "chunk_ids": [],
        "rag_tool_chunk_ids": [],
        "drug_tool_name": None,
        "drug_tool_status": None,
        "drug_tool_errors": [],
    }

    result = tool_contract_evaluator(outputs, {})

    assert result["score"] == 0


def test_tool_contract_evaluator_fails_when_rag_tool_chunks_diverge() -> None:
    outputs = {
        "actual_route": "rag",
        "rag_tool_name": "rag_search_tool",
        "rag_tool_result_count": 1,
        "rag_tool_errors": [],
        "chunk_ids": ["a:p1:c0"],
        "rag_tool_chunk_ids": ["b:p1:c0"],
        "drug_tool_name": None,
        "drug_tool_status": None,
        "drug_tool_errors": [],
    }

    result = tool_contract_evaluator(outputs, {})

    assert result["score"] == 0
