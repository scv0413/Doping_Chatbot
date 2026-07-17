from app.chat.drug_search.drug_rag_inspector import build_retrieval_query
from app.chat.drug_search.schemas import (
    CompetitionPeriod,
    DrugRiskStatus,
    DrugSearchInput,
    DrugSearchResult,
)
from app.chat.router.intent_router import ChatRoute, RouteDecision


def test_build_retrieval_query_does_not_add_drug_terms_for_rag_only_route() -> None:
    search_input = DrugSearchInput(query="TUE 신청 방법과 대리 신청 가능 여부를 알려줘")
    decision = RouteDecision(route=ChatRoute.RAG, reason="rag only")

    query = build_retrieval_query(search_input=search_input, decision=decision)

    assert query == search_input.query
    assert "금지약물" not in query
    assert "용량" not in query


def test_build_retrieval_query_adds_kada_substance_and_category_terms() -> None:
    search_input = DrugSearchInput(
        query="슈도에페드린 경기기간 중 먹어도 돼?",
        ingredient_name="슈도에페드린",
        competition_period=CompetitionPeriod.IN_COMPETITION,
    )
    decision = RouteDecision(
        route=ChatRoute.DRUG_SEARCH_WITH_RAG,
        reason="drug with rag",
    )
    drug_result = DrugSearchResult(
        status=DrugRiskStatus.PROHIBITED_POSSIBLE,
        input=search_input,
        matched_substances=["슈도에페드린", "pseudoephedrine"],
        prohibited_categories=["S6_120"],
        recommended_action="금지 가능성이 확인됩니다.",
    )

    query = build_retrieval_query(
        search_input=search_input,
        decision=decision,
        drug_result=drug_result,
    )

    assert "슈도에페드린" in query
    assert "pseudoephedrine" in query
    assert "S6_120" in query
    assert "흥분제" in query
    assert "stimulants" in query
