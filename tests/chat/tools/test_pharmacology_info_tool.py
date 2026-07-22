from app.chat.pharmacology.schemas import PharmacologyInfoResult, PharmacologyInfoStatus
from app.chat.tools import PharmacologyInfoToolRequest, run_pharmacology_info_tool


def test_run_pharmacology_info_tool_returns_found_result() -> None:
    request = PharmacologyInfoToolRequest(
        query="슈도에페드린 반감기가 얼마나 돼?",
        request_id="pharmacology-tool-request-1",
    )

    output = run_pharmacology_info_tool(request)

    assert output.ok is True
    assert output.tool_name == "pharmacology_info_tool"
    assert output.query == request.query
    assert output.request_id == "pharmacology-tool-request-1"
    assert output.errors == []
    assert output.result is not None
    assert output.result.status is PharmacologyInfoStatus.FOUND
    assert output.result.substance_name == "pseudoephedrine"
    assert output.result.half_life is not None
    assert "4-8시간" in output.result.half_life.typical_range


def test_run_pharmacology_info_tool_returns_not_found_result() -> None:
    request = PharmacologyInfoToolRequest(query="처음 보는 성분 반감기 알려줘")

    output = run_pharmacology_info_tool(request)

    assert output.ok is True
    assert output.result is not None
    assert output.result.status is PharmacologyInfoStatus.NOT_FOUND
    assert output.result.substance_name is None
    assert "성분명" in output.result.recommended_action


def test_run_pharmacology_info_tool_returns_tool_error_when_searcher_fails() -> None:
    def broken_searcher(query: str) -> PharmacologyInfoResult:
        raise RuntimeError("pharmacology knowledge base unavailable")

    request = PharmacologyInfoToolRequest(query="슈도에페드린 반감기")

    output = run_pharmacology_info_tool(request, pharmacology_searcher=broken_searcher)

    assert output.ok is False
    assert output.result is None
    assert len(output.errors) == 1
    assert output.errors[0].stage == "pharmacology_info"
    assert output.errors[0].error_type == "RuntimeError"
    assert "knowledge base unavailable" in output.errors[0].message
