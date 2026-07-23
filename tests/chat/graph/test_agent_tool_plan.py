from app.chat.agent import run_agent_tool_plan
from app.chat.domain.drug_search.schemas import DrugRiskStatus, DrugSearchInput, DrugSearchResult
from app.chat.domain.pharmacology.schemas import PharmacologyInfoResult, PharmacologyInfoStatus
from app.chat.domain.retrieval.schemas import RetrievalMatch, RetrievalMetadata
from app.chat.tools import MCPToolDependencies


def fake_retriever(query: str, top_k: int) -> list[RetrievalMatch]:
    return [
        RetrievalMatch(
            rank=1,
            chunk_id="field_response_manual:s1:c0",
            distance=0.2,
            metadata=RetrievalMetadata(
                source_id="field_response_manual",
                title="현장 대응 매뉴얼",
                chunk_id="field_response_manual:s1:c0",
            ),
            text=f"{query} / top_k={top_k}",
        )
    ]


def fake_drug_searcher(search_input: DrugSearchInput) -> DrugSearchResult:
    return DrugSearchResult(
        status=DrugRiskStatus.PROHIBITED_POSSIBLE,
        input=search_input,
        matched_substances=[search_input.ingredient_name or search_input.query],
        prohibited_categories=["S6"],
        recommended_action="제품명과 성분명, 용량을 확인하세요.",
    )


def fake_pharmacology_searcher(query: str) -> PharmacologyInfoResult:
    return PharmacologyInfoResult(
        status=PharmacologyInfoStatus.NOT_FOUND,
        query=query,
        recommended_action="정확한 성분명을 확인하세요.",
    )


def dependencies() -> MCPToolDependencies:
    return MCPToolDependencies(
        rag_retriever=fake_retriever,
        drug_searcher=fake_drug_searcher,
        pharmacology_searcher=fake_pharmacology_searcher,
    )


def test_agent_tool_plan_calls_rag_only_for_field_question() -> None:
    result = run_agent_tool_plan(
        "도핑 검사관 신분이 불분명하면 어떻게 확인해야 해?",
        dependencies=dependencies(),
        query_rewriter=lambda query: query,
    )

    assert result.route == "rag"
    assert result.called_tool_names == ["rag_search_tool"]


def test_agent_tool_plan_calls_drug_only_for_simple_drug_question() -> None:
    result = run_agent_tool_plan(
        "타이레놀 먹어도 돼?",
        dependencies=dependencies(),
        query_rewriter=lambda query: query,
    )

    assert result.route == "drug_search"
    assert result.called_tool_names == ["drug_search_tool"]


def test_agent_tool_plan_calls_drug_pharmacology_and_rag_for_half_life_drug_question() -> None:
    result = run_agent_tool_plan(
        "슈도에페드린 반감기가 얼마나 돼? 경기 전날 먹었으면 괜찮아?",
        dependencies=dependencies(),
        query_rewriter=lambda query: query,
    )

    assert result.route == "drug_search_with_rag"
    assert result.called_tool_names == [
        "drug_search_tool",
        "pharmacology_info_tool",
        "rag_search_tool",
    ]
    assert result.tool_calls[0].output["tool_name"] == "drug_search_tool"
    assert result.tool_calls[1].output["tool_name"] == "pharmacology_info_tool"
    assert result.tool_calls[2].output["tool_name"] == "rag_search_tool"


def test_agent_tool_plan_declares_order_before_execution() -> None:
    from app.chat.agent import build_agent_tool_plan
    from app.chat.pipeline.chat_pipeline import normalize_pipeline_input
    from app.chat.router.intent_router import route_question

    search_input = normalize_pipeline_input("슈도에페드린 반감기가 얼마나 돼? 경기 전날 먹었으면 괜찮아?")
    plan = build_agent_tool_plan(search_input, route_question(search_input.query))

    assert plan.route == "drug_search_with_rag"
    assert plan.tool_names == [
        "drug_search_tool",
        "pharmacology_info_tool",
        "rag_search_tool",
    ]
