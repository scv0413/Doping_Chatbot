from app.chat.domain.drug_search.schemas import (
    AdministrationRoute,
    CompetitionPeriod,
    DrugRiskStatus,
    DrugSearchInput,
    DrugSearchResult,
)
from app.chat.tools import DrugSearchToolRequest, run_drug_search_tool
from app.chat.tools.drug_search_tool import request_to_drug_search_input


def fake_drug_searcher(search_input: DrugSearchInput) -> DrugSearchResult:
    assert search_input.query == "슈도에페드린 먹어도 돼?"
    assert search_input.ingredient_name == "슈도에페드린"
    assert search_input.competition_period is CompetitionPeriod.IN_COMPETITION
    assert search_input.route is AdministrationRoute.ORAL
    return DrugSearchResult(
        status=DrugRiskStatus.PROHIBITED_POSSIBLE,
        input=search_input,
        matched_substances=["슈도에페드린"],
        prohibited_categories=["S6_120"],
        requires_dose_confirmation=True,
        recommended_action="금지 가능성이 확인됩니다. 사용 전 KADA 또는 팀 닥터에게 확인하세요.",
    )


def test_run_drug_search_tool_returns_structured_result() -> None:
    request = DrugSearchToolRequest(
        query="슈도에페드린 먹어도 돼?",
        ingredient_name="슈도에페드린",
        competition_period=CompetitionPeriod.IN_COMPETITION,
        route=AdministrationRoute.ORAL,
        request_id="drug-tool-request-1",
    )

    output = run_drug_search_tool(request, drug_searcher=fake_drug_searcher)

    assert output.ok is True
    assert output.tool_name == "drug_search_tool"
    assert output.query == request.query
    assert output.request_id == "drug-tool-request-1"
    assert output.errors == []
    assert output.result is not None
    assert output.result.status is DrugRiskStatus.PROHIBITED_POSSIBLE
    assert output.result.matched_substances == ["슈도에페드린"]
    assert output.result.requires_dose_confirmation is True


def test_run_drug_search_tool_returns_tool_error_when_searcher_fails() -> None:
    def broken_searcher(search_input: DrugSearchInput) -> DrugSearchResult:
        raise RuntimeError("KADA search unavailable")

    request = DrugSearchToolRequest(query="타이레놀 먹어도 돼?")

    output = run_drug_search_tool(request, drug_searcher=broken_searcher)

    assert output.ok is False
    assert output.result is None
    assert len(output.errors) == 1
    assert output.errors[0].stage == "drug_search"
    assert output.errors[0].error_type == "RuntimeError"
    assert "KADA search unavailable" in output.errors[0].message


def test_request_to_drug_search_input_preserves_optional_fields() -> None:
    request = DrugSearchToolRequest(
        query="코감기약 비강 스프레이 써도 돼?",
        product_name="코감기약",
        competition_period=CompetitionPeriod.UNKNOWN,
        route=AdministrationRoute.NASAL,
        sport="cycling",
        dose="1 spray",
    )

    search_input = request_to_drug_search_input(request)

    assert search_input.query == request.query
    assert search_input.product_name == "코감기약"
    assert search_input.route is AdministrationRoute.NASAL
    assert search_input.sport == "cycling"
    assert search_input.dose == "1 spray"
