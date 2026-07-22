from app.chat.evals.release_quality_gate import (
    GateThresholds,
    build_release_quality_report,
)


def passing_target(inputs: dict[str, object]) -> dict[str, object]:
    return {
        "actual_route": "rag",
        "source_ids": ["source_1"],
        "retrieved_text": "required-term",
        "context_chars": 200,
        "match_count": 1,
        "error": None,
        "rag_tool_name": "rag_search_tool",
        "rag_tool_result_count": 1,
        "rag_tool_chunk_ids": ["source_1:p1:c0"],
        "chunk_ids": ["source_1:p1:c0"],
        "rag_tool_errors": [],
        "drug_tool_name": None,
        "pharmacology_tool_name": None,
        "query": inputs["query"],
    }


def test_release_quality_gate_passes_when_metrics_meet_thresholds() -> None:
    report = build_release_quality_report(
        cases=[
            {
                "inputs": {"case_id": "case_1", "query": "question"},
                "outputs": {
                    "expected_route": "rag",
                    "expected_sources": ["source_1"],
                    "must_include_terms": ["required-term"],
                },
            }
        ],
        target=passing_target,
        thresholds=GateThresholds(min_retrieval_quality=1.0),
    )

    assert report.passed is True
    assert report.metric_averages["route_match"] == 1.0
    assert report.metric_averages["tool_contract"] == 1.0


def test_release_quality_gate_fails_when_required_route_metric_drops() -> None:
    def failing_target(inputs: dict[str, object]) -> dict[str, object]:
        result = passing_target(inputs)
        result["actual_route"] = "drug_search"
        return result

    report = build_release_quality_report(
        cases=[
            {
                "inputs": {"case_id": "case_1", "query": "question"},
                "outputs": {
                    "expected_route": "rag",
                    "expected_sources": ["source_1"],
                    "must_include_terms": ["required-term"],
                },
            }
        ],
        target=failing_target,
    )

    assert report.passed is False
    assert "route_match" in report.failed_metrics
