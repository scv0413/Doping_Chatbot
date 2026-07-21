import argparse
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

from app.chat.evals.cases import DEFAULT_CASES, EvalCase, case_to_inputs, case_to_outputs
from app.chat.evals.langsmith_graph_eval import build_graph_retrieval_target
from app.chat.evals.langsmith_retrieval_eval import (
    build_retrieval_target,
    context_budget_evaluator,
    retrieval_quality_evaluator,
    route_match_evaluator,
    source_hit_evaluator,
    term_hit_evaluator,
)
from app.chat.evals.retrieval_token_experiment import ExperimentConfig

DEFAULT_OUTPUT_PATH = Path("app/chat/docs/langsmith-retrieval-vs-graph-comparison.md")


@dataclass(frozen=True)
class EvalScoreSet:
    route_match: float
    source_hit: float
    term_hit: float
    context_budget: float
    retrieval_quality: float


@dataclass(frozen=True)
class ComparisonRow:
    case_id: str
    query: str
    baseline_route: str
    graph_route: str
    baseline_chunks: list[str]
    graph_chunks: list[str]
    baseline_scores: EvalScoreSet
    graph_scores: EvalScoreSet


def score_outputs(outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> EvalScoreSet:
    return EvalScoreSet(
        route_match=float(route_match_evaluator(outputs, reference_outputs)["score"]),
        source_hit=float(source_hit_evaluator(outputs, reference_outputs)["score"]),
        term_hit=float(term_hit_evaluator(outputs, reference_outputs)["score"]),
        context_budget=float(context_budget_evaluator(outputs, reference_outputs)["score"]),
        retrieval_quality=float(retrieval_quality_evaluator(outputs, reference_outputs)["score"]),
    )


def build_comparison_rows(
    top_k: int = 3,
    rewrite_enabled: bool = True,
    cases: list[EvalCase] | None = None,
) -> list[ComparisonRow]:
    resolved_cases = cases or DEFAULT_CASES
    baseline_target = build_retrieval_target(
        ExperimentConfig(top_k=top_k, rewrite_enabled=rewrite_enabled)
    )
    graph_target = build_graph_retrieval_target(top_k=top_k, use_llm=False)

    rows: list[ComparisonRow] = []
    for case in resolved_cases:
        inputs = case_to_inputs(case)
        references = case_to_outputs(case)
        baseline_outputs = baseline_target(inputs)
        graph_outputs = graph_target(inputs)
        rows.append(
            ComparisonRow(
                case_id=case.case_id,
                query=case.query,
                baseline_route=str(baseline_outputs.get("actual_route")),
                graph_route=str(graph_outputs.get("actual_route")),
                baseline_chunks=list(baseline_outputs.get("chunk_ids", [])),
                graph_chunks=list(graph_outputs.get("chunk_ids", [])),
                baseline_scores=score_outputs(baseline_outputs, references),
                graph_scores=score_outputs(graph_outputs, references),
            )
        )

    return rows


def average_scores(rows: list[ComparisonRow], side: str) -> EvalScoreSet:
    scores = [row.baseline_scores if side == "baseline" else row.graph_scores for row in rows]
    return EvalScoreSet(
        route_match=mean(score.route_match for score in scores),
        source_hit=mean(score.source_hit for score in scores),
        term_hit=mean(score.term_hit for score in scores),
        context_budget=mean(score.context_budget for score in scores),
        retrieval_quality=mean(score.retrieval_quality for score in scores),
    )


def format_score(score: float) -> str:
    return f"{score:.2f}"


def format_chunks(chunks: list[str], limit: int = 3) -> str:
    if not chunks:
        return "-"
    return ", ".join(chunks[:limit])


def build_markdown(rows: list[ComparisonRow], top_k: int, rewrite_enabled: bool) -> str:
    baseline_avg = average_scores(rows, "baseline")
    graph_avg = average_scores(rows, "graph")

    lines = [
        "# Retrieval Eval vs LangGraph Retrieval Eval",
        "",
        "## Purpose",
        "",
        "기존 retrieval-only eval과 LangGraph 기반 retrieval eval을 같은 10개 케이스와 같은 evaluator로 비교한다.",
        "목적은 LangGraph 도입 이후에도 검색 품질이 유지되는지 확인하는 것이다.",
        "",
        "## Configuration",
        "",
        f"- top_k: {top_k}",
        f"- baseline rewrite_enabled: {rewrite_enabled}",
        "- graph use_llm: False",
        "- evaluator: route_match, source_hit, term_hit, context_budget, retrieval_quality",
        "",
        "## Average Scores",
        "",
        "| Runner | route_match | source_hit | term_hit | context_budget | retrieval_quality |",
        "|---|---:|---:|---:|---:|---:|",
        (
            f"| baseline retrieval | {format_score(baseline_avg.route_match)} | "
            f"{format_score(baseline_avg.source_hit)} | {format_score(baseline_avg.term_hit)} | "
            f"{format_score(baseline_avg.context_budget)} | {format_score(baseline_avg.retrieval_quality)} |"
        ),
        (
            f"| LangGraph retrieval | {format_score(graph_avg.route_match)} | "
            f"{format_score(graph_avg.source_hit)} | {format_score(graph_avg.term_hit)} | "
            f"{format_score(graph_avg.context_budget)} | {format_score(graph_avg.retrieval_quality)} |"
        ),
        "",
        "## Case Details",
        "",
        "| Case | Baseline quality | Graph quality | Baseline chunks | Graph chunks |",
        "|---|---:|---:|---|---|",
    ]

    for row in rows:
        lines.append(
            f"| `{row.case_id}` | {format_score(row.baseline_scores.retrieval_quality)} | "
            f"{format_score(row.graph_scores.retrieval_quality)} | "
            f"{format_chunks(row.baseline_chunks)} | {format_chunks(row.graph_chunks)} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "LangGraph는 기존 pipeline 기능을 graph node로 감싼 1차 구조이며, 이 비교에서는 agentic retry나 추가 tool loop를 사용하지 않는다.",
            "따라서 점수가 유지된다는 것은 orchestration layer를 LangGraph로 바꾸어도 검색 품질이 유지된다는 근거가 된다.",
            "",
            "다음 단계에서는 이 결과를 기준선으로 삼고, 검색 결과가 비거나 품질이 낮을 때만 1회 재시도하는 최소 agentic graph를 설계한다.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_comparison_report(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    top_k: int = 3,
    rewrite_enabled: bool = True,
) -> list[ComparisonRow]:
    rows = build_comparison_rows(top_k=top_k, rewrite_enabled=rewrite_enabled)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_markdown(rows, top_k, rewrite_enabled), encoding="utf-8")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--rewrite", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args()

    rows = write_comparison_report(
        output_path=args.output_path,
        top_k=args.top_k,
        rewrite_enabled=args.rewrite,
    )
    baseline_avg = average_scores(rows, "baseline")
    graph_avg = average_scores(rows, "graph")
    print(f"cases: {len(rows)}")
    print(f"baseline retrieval_quality: {baseline_avg.retrieval_quality:.2f}")
    print(f"graph retrieval_quality: {graph_avg.retrieval_quality:.2f}")
    print(f"saved: {args.output_path}")


if __name__ == "__main__":
    main()
