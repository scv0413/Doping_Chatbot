from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

from app.chat.evals.cases import DEFAULT_CASES, case_to_inputs, case_to_outputs
from app.chat.evals.langsmith_retrieval_eval import (
    retrieval_quality_evaluator,
    route_match_evaluator,
    source_hit_evaluator,
    term_hit_evaluator,
)
from app.chat.evals.langsmith_tool_eval import build_graph_tool_target, tool_contract_evaluator

Target = Callable[[dict[str, Any]], dict[str, Any]]


class GateThresholds(BaseModel):
    required_exact_metrics: tuple[str, ...] = ("route_match", "tool_contract")
    min_source_hit: float = 0.9
    min_term_hit: float = 0.9
    min_retrieval_quality: float = 0.9


class ReleaseQualityCaseResult(BaseModel):
    case_id: str
    metrics: dict[str, float]
    errors: list[dict[str, Any]] = Field(default_factory=list)


class ReleaseQualityReport(BaseModel):
    passed: bool
    metric_averages: dict[str, float]
    failed_metrics: list[str] = Field(default_factory=list)
    case_results: list[ReleaseQualityCaseResult]

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)


def default_gate_cases() -> list[dict[str, dict[str, Any]]]:
    return [
        {
            "inputs": case_to_inputs(case),
            "outputs": case_to_outputs(case),
        }
        for case in DEFAULT_CASES
    ]


def build_release_quality_report(
    cases: list[dict[str, dict[str, Any]]] | None = None,
    target: Target | None = None,
    thresholds: GateThresholds | None = None,
) -> ReleaseQualityReport:
    resolved_cases = cases or default_gate_cases()
    resolved_target = target or build_graph_tool_target(top_k=3, use_llm=False)
    resolved_thresholds = thresholds or GateThresholds()
    case_results: list[ReleaseQualityCaseResult] = []

    for case in resolved_cases:
        inputs = case["inputs"]
        reference_outputs = case["outputs"]
        outputs = resolved_target(inputs)
        evaluators = (
            route_match_evaluator,
            source_hit_evaluator,
            term_hit_evaluator,
            retrieval_quality_evaluator,
            tool_contract_evaluator,
        )
        metrics = {
            evaluation["key"]: float(evaluation["score"])
            for evaluator in evaluators
            for evaluation in [evaluator(outputs, reference_outputs)]
        }
        case_results.append(
            ReleaseQualityCaseResult(
                case_id=str(inputs["case_id"]),
                metrics=metrics,
                errors=list(outputs.get("errors", [])),
            )
        )

    metric_averages = average_metrics(case_results)
    failed_metrics = find_failed_metrics(metric_averages, resolved_thresholds)
    has_case_errors = any(result.errors for result in case_results)
    return ReleaseQualityReport(
        passed=not failed_metrics and not has_case_errors,
        metric_averages=metric_averages,
        failed_metrics=failed_metrics,
        case_results=case_results,
    )


def average_metrics(case_results: list[ReleaseQualityCaseResult]) -> dict[str, float]:
    if not case_results:
        return {}

    metric_names = sorted({name for result in case_results for name in result.metrics})
    return {
        metric_name: sum(result.metrics.get(metric_name, 0.0) for result in case_results)
        / len(case_results)
        for metric_name in metric_names
    }


def find_failed_metrics(
    metric_averages: dict[str, float],
    thresholds: GateThresholds,
) -> list[str]:
    failed: list[str] = []
    for metric_name in thresholds.required_exact_metrics:
        if metric_averages.get(metric_name, 0.0) < 1.0:
            failed.append(metric_name)

    minimums = {
        "source_hit": thresholds.min_source_hit,
        "term_hit": thresholds.min_term_hit,
        "retrieval_quality": thresholds.min_retrieval_quality,
    }
    for metric_name, minimum in minimums.items():
        if metric_averages.get(metric_name, 0.0) < minimum:
            failed.append(metric_name)
    return failed


def main() -> None:
    report = build_release_quality_report()
    print(report.to_json())
    if not report.passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
