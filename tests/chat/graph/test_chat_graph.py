from app.chat.drug_search.schemas import DrugRiskStatus, DrugSearchInput, DrugSearchResult
from app.chat.graph.graph import run_chat_graph
from app.chat.graph.nodes import (
    ChatGraphDependencies,
    build_answer_node,
    build_drug_search_node,
    build_retrieve_node,
    build_rewrite_node,
    build_route_node,
)
from app.chat.pipeline.chat_pipeline import run_chat_pipeline
from app.chat.retrieval.schemas import RetrievalMatch, RetrievalMetadata
from app.chat.router.intent_router import ChatRoute


def fake_drug_searcher(search_input: DrugSearchInput) -> DrugSearchResult:
    if "슈도에페드린" in search_input.query:
        return DrugSearchResult(
            status=DrugRiskStatus.PROHIBITED_POSSIBLE,
            input=search_input,
            matched_substances=["슈도에페드린"],
            prohibited_categories=["S6_120"],
            requires_dose_confirmation=True,
            recommended_action="용량 기준 확인 필요",
        )

    return DrugSearchResult(
        status=DrugRiskStatus.NEEDS_VERIFICATION,
        input=search_input,
        recommended_action="제품명 확인 필요",
    )


def fake_retriever(query: str, top_k: int) -> list[RetrievalMatch]:
    return [
        RetrievalMatch(
            rank=1,
            chunk_id="field_response_manual:s1:c0" if "검사관" in query else "wada_prohibited_list_2026_ko:p17:c3",
            distance=0.2,
            metadata=RetrievalMetadata(
                source_id="field_response_manual" if "검사관" in query else "wada_prohibited_list_2026_ko",
                title="현장 대응 매뉴얼" if "검사관" in query else "금지목록 국제표준",
                page=17,
            ),
            text=(
                "검사관 신분 확인, 기록, 동석 요청. 검사 통지 후 즉시 충돌하거나 현장을 이탈하지 않고 "
                "신분증, 소속, 권한, 절차 설명을 차분히 확인해야 한다. 통역 또는 팀 관계자 동석을 "
                "요청하고 우려 사항을 기록해야 한다."
                if "검사관" in query
                else "슈도에페드린 S6 흥분제 소변 농도 기준. 경기기간 중에는 성분명, 제품명, 용량, "
                "소변 농도 기준을 함께 확인해야 하며 공식 금지목록과 KADA 약물검색을 확인해야 한다."
            ),
        )
    ][:top_k]


def identity_rewriter(query: str) -> str:
    return query


def chunk_ids(result) -> list[str]:
    return [match.chunk_id for match in result.retrieval_matches]


def test_graph_nodes_run_rag_flow() -> None:
    dependencies = ChatGraphDependencies(
        retriever=fake_retriever,
        query_rewriter=identity_rewriter,
    )
    state = {
        "query": "도핑 검사관 신분이 불분명하면 어떻게 확인해야 해?",
        "top_k": 3,
        "use_llm": False,
        "errors": [],
    }

    state.update(build_route_node(dependencies)(state))
    assert state["decision"].route is ChatRoute.RAG

    state.update(build_rewrite_node(dependencies)(state))
    assert state["retrieval_query"] == state["query"]

    state.update(build_retrieve_node(dependencies)(state))
    assert state["rag_search_output"].tool_name == "rag_search_tool"
    assert state["rag_search_output"].results[0].chunk_id == "field_response_manual:s1:c0"
    assert state["retrieval_matches"][0].chunk_id == "field_response_manual:s1:c0"

    state.update(build_answer_node(dependencies)(state))
    assert "확인, 기록, 동석 요청" in state["answer"]


def test_drug_search_node_uses_fallback_error_path() -> None:
    def broken_drug_searcher(search_input: DrugSearchInput) -> DrugSearchResult:
        raise RuntimeError("temporary failure")

    dependencies = ChatGraphDependencies(drug_searcher=broken_drug_searcher)
    state = {
        "query": "타이레놀 먹어도 돼?",
        "top_k": 3,
        "use_llm": False,
        "errors": [],
    }
    state.update(build_route_node(dependencies)(state))
    state.update(build_drug_search_node(dependencies)(state))

    assert state["drug_search_tool_output"].tool_name == "drug_search_tool"
    assert state["drug_search_tool_output"].result is None
    assert state["drug_search_tool_output"].errors[0].stage == "drug_search"
    assert state["drug_result"].status is DrugRiskStatus.NEEDS_VERIFICATION
    assert state["errors"][0].stage == "drug_search"
    assert state["errors"][0].error_type == "RuntimeError"


def test_graph_matches_pipeline_for_rag_flow() -> None:
    query = "도핑 검사관 신분이 불분명하면 어떻게 확인해야 해?"
    pipeline_result = run_chat_pipeline(
        query,
        top_k=3,
        use_llm=False,
        retriever=fake_retriever,
        query_rewriter=identity_rewriter,
    )
    graph_result = run_chat_graph(
        query,
        top_k=3,
        use_llm=False,
        retriever=fake_retriever,
        query_rewriter=identity_rewriter,
    )

    assert graph_result.decision.route == pipeline_result.decision.route
    assert chunk_ids(graph_result) == chunk_ids(pipeline_result)
    assert graph_result.errors == pipeline_result.errors
    assert graph_result.retrieval_attempts == 1
    assert "## 답변 요약" in graph_result.answer


def test_graph_matches_pipeline_for_drug_search_only_flow() -> None:
    query = "타이레놀 먹어도 돼?"
    pipeline_result = run_chat_pipeline(
        query,
        top_k=3,
        use_llm=False,
        drug_searcher=fake_drug_searcher,
    )
    graph_result = run_chat_graph(
        query,
        top_k=3,
        use_llm=False,
        drug_searcher=fake_drug_searcher,
    )

    assert graph_result.decision.route == pipeline_result.decision.route
    assert graph_result.drug_result is not None
    assert pipeline_result.drug_result is not None
    assert graph_result.drug_result.status == pipeline_result.drug_result.status
    assert graph_result.drug_search_tool_output is not None
    assert graph_result.drug_search_tool_output.tool_name == "drug_search_tool"
    assert graph_result.drug_search_tool_output.result is not None
    assert graph_result.retrieval_matches == []
    assert graph_result.errors == []


def test_graph_matches_pipeline_for_drug_search_with_rag_flow() -> None:
    query = "슈도에페드린 경기기간 중 먹어도 돼?"
    pipeline_result = run_chat_pipeline(
        query,
        top_k=3,
        use_llm=False,
        drug_searcher=fake_drug_searcher,
        retriever=fake_retriever,
        query_rewriter=identity_rewriter,
    )
    graph_result = run_chat_graph(
        query,
        top_k=3,
        use_llm=False,
        drug_searcher=fake_drug_searcher,
        retriever=fake_retriever,
        query_rewriter=identity_rewriter,
    )

    assert graph_result.decision.route == pipeline_result.decision.route
    assert graph_result.drug_result is not None
    assert pipeline_result.drug_result is not None
    assert graph_result.drug_result.status == pipeline_result.drug_result.status
    assert graph_result.drug_search_tool_output is not None
    assert graph_result.drug_search_tool_output.tool_name == "drug_search_tool"
    assert graph_result.drug_search_tool_output.result is not None
    assert chunk_ids(graph_result) == chunk_ids(pipeline_result)
    assert graph_result.errors == []


def test_graph_retries_retrieval_once_when_results_are_empty() -> None:
    calls: list[str] = []

    def flaky_retriever(query: str, top_k: int) -> list[RetrievalMatch]:
        calls.append(query)
        if len(calls) == 1:
            return []
        return fake_retriever(query, top_k)

    result = run_chat_graph(
        "도핑 검사관 신분이 불분명하면 어떻게 확인해야 해?",
        top_k=3,
        use_llm=False,
        retriever=flaky_retriever,
        query_rewriter=identity_rewriter,
    )

    assert len(calls) == 2
    assert "공식 근거" in calls[1]
    assert result.retrieval_matches
    assert result.retrieval_attempts == 2
    assert result.retrieval_retry_reason is None
    assert result.errors == []


def test_graph_stops_after_one_retry_when_results_stay_empty() -> None:
    calls: list[str] = []

    def empty_retriever(query: str, top_k: int) -> list[RetrievalMatch]:
        calls.append(query)
        return []

    result = run_chat_graph(
        "도핑 검사관 신분이 불분명하면 어떻게 확인해야 해?",
        top_k=3,
        use_llm=False,
        retriever=empty_retriever,
        query_rewriter=identity_rewriter,
    )

    assert len(calls) == 2
    assert result.retrieval_matches == []
    assert result.retrieval_attempts == 2
    assert result.retrieval_retry_reason == "empty_results"
    assert result.errors == []
    assert "공식 문서와 manual source" in result.answer
