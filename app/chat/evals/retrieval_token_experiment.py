import argparse
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.chat.orchestration.pipeline.chat_pipeline import build_retrieval_query, normalize_pipeline_input
from app.chat.domain.retrieval.query_rewriter import rewrite_query
from app.chat.domain.retrieval.retriever import search
from app.chat.domain.retrieval.schemas import RetrievalMatch
from app.chat.orchestration.router.intent_router import ChatRoute, route_question
from app.chat.evals.cases import DEFAULT_CASES, EvalCase


@dataclass(frozen=True)
class ExperimentConfig:
    top_k: int
    rewrite_enabled: bool
    max_preview_chars: int = 400


def run_experiment(
    cases: list[EvalCase] | None = None,
    configs: list[ExperimentConfig] | None = None,
    retriever: Callable[[str, int], list[RetrievalMatch]] = search,
) -> list[dict[str, Any]]:
    cases = cases or DEFAULT_CASES
    configs = configs or build_default_configs()

    rows: list[dict[str, Any]] = []
    for case in cases:
        for config in configs:
            rows.append(evaluate_case(case=case, config=config, retriever=retriever))
    return rows


def build_default_configs() -> list[ExperimentConfig]:
    return [
        ExperimentConfig(top_k=3, rewrite_enabled=False),
        ExperimentConfig(top_k=3, rewrite_enabled=True),
        ExperimentConfig(top_k=5, rewrite_enabled=False),
        ExperimentConfig(top_k=5, rewrite_enabled=True),
    ]


def evaluate_case(
    case: EvalCase,
    config: ExperimentConfig,
    retriever: Callable[[str, int], list[RetrievalMatch]],
) -> dict[str, Any]:
    decision = route_question(case.query)
    route_match = decision.route.value == case.expected_route
    retrieval_query = build_eval_retrieval_query(case.query, decision.route)
    if retrieval_query and case.retrieval_terms:
        retrieval_query = "\n".join([retrieval_query, *case.retrieval_terms])
    final_query = rewrite_query(retrieval_query) if config.rewrite_enabled else retrieval_query

    matches: list[RetrievalMatch] = []
    error: str | None = None
    if should_retrieve(decision.route):
        try:
            matches = retriever(final_query, config.top_k)
        except Exception as exc:  # pragma: no cover - exercised by CLI/runtime validation
            error = f"{type(exc).__name__}: {exc}"

    source_ids = [match.source_id for match in matches]
    matched_text = "\n".join(match.text for match in matches)
    expected_source_hit = has_expected_source(source_ids, case.expected_sources)
    must_terms_hit = count_term_hits(matched_text, case.must_include_terms)
    context_chars = sum(len(match.text) for match in matches)

    return {
        "case_id": case.case_id,
        "query": case.query,
        "expected_route": case.expected_route,
        "actual_route": decision.route.value,
        "route_match": route_match,
        "top_k": config.top_k,
        "rewrite_enabled": config.rewrite_enabled,
        "retrieval_query": retrieval_query,
        "final_query": final_query,
        "match_count": len(matches),
        "source_ids": source_ids,
        "chunk_ids": [match.chunk_id for match in matches],
        "distances": [round(match.distance, 4) for match in matches],
        "expected_source_hit": expected_source_hit,
        "must_terms_total": len(case.must_include_terms),
        "must_terms_hit": must_terms_hit,
        "context_chars": context_chars,
        "quality_score": score_result(
            route_match=route_match,
            expected_source_hit=expected_source_hit,
            must_terms_hit=must_terms_hit,
            must_terms_total=len(case.must_include_terms),
            should_have_matches=should_retrieve(decision.route),
            match_count=len(matches),
            error=error,
        ),
        "previews": [preview_match(match, config.max_preview_chars) for match in matches],
        "error": error,
    }


def build_eval_retrieval_query(query: str, route: ChatRoute) -> str:
    if route is ChatRoute.DRUG_SEARCH:
        return ""

    search_input = normalize_pipeline_input(query)
    return build_retrieval_query(search_input=search_input, decision=route_question(query))


def should_retrieve(route: ChatRoute) -> bool:
    return route in {ChatRoute.RAG, ChatRoute.DRUG_SEARCH_WITH_RAG}


def has_expected_source(source_ids: list[str], expected_sources: tuple[str, ...]) -> bool:
    if not expected_sources:
        return True
    return any(source_id in expected_sources for source_id in source_ids)


def count_term_hits(text: str, terms: tuple[str, ...]) -> int:
    normalized_text = text.casefold()
    return sum(1 for term in terms if term.casefold() in normalized_text)


def score_result(
    route_match: bool,
    expected_source_hit: bool,
    must_terms_hit: int,
    must_terms_total: int,
    should_have_matches: bool,
    match_count: int,
    error: str | None,
) -> int:
    if error:
        return 0

    score = 0
    if route_match:
        score += 1
    if not should_have_matches or match_count > 0:
        score += 1
    if expected_source_hit and (must_terms_total == 0 or must_terms_hit > 0):
        score += 1
    return score


def preview_match(match: RetrievalMatch, max_chars: int) -> dict[str, Any]:
    return {
        "rank": match.rank,
        "chunk_id": match.chunk_id,
        "source_id": match.source_id,
        "page": match.metadata.page,
        "distance": round(match.distance, 4),
        "text": match.text[:max_chars].replace("\n", " "),
    }


def summarize_results(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[int, bool], list[dict[str, Any]]] = {}
    for row in rows:
        key = (row["top_k"], row["rewrite_enabled"])
        grouped.setdefault(key, []).append(row)

    summary: list[dict[str, Any]] = []
    for (top_k, rewrite_enabled), group_rows in sorted(grouped.items()):
        case_count = len(group_rows)
        summary.append(
            {
                "top_k": top_k,
                "rewrite_enabled": rewrite_enabled,
                "case_count": case_count,
                "avg_quality_score": round(
                    sum(row["quality_score"] for row in group_rows) / case_count,
                    2,
                ),
                "route_match_count": sum(1 for row in group_rows if row["route_match"]),
                "expected_source_hit_count": sum(1 for row in group_rows if row["expected_source_hit"]),
                "avg_context_chars": round(
                    sum(row["context_chars"] for row in group_rows) / case_count,
                    1,
                ),
                "error_count": sum(1 for row in group_rows if row["error"]),
            }
        )
    return summary


def select_recommended_config(summary: list[dict[str, Any]]) -> dict[str, Any]:
    return max(
        summary,
        key=lambda row: (
            row["avg_quality_score"],
            row["expected_source_hit_count"],
            -row["avg_context_chars"],
            row["rewrite_enabled"],
        ),
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False))
            file.write("\n")


def write_markdown_report(path: Path, rows: list[dict[str, Any]], summary: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    recommended = select_recommended_config(summary)
    lines = [
        "# Retrieval / Token Experiment Result",
        "",
        f"- generated_at: {datetime.now().isoformat(timespec='seconds')}",
        f"- cases: {len({row['case_id'] for row in rows})}",
        f"- runs: {len(rows)}",
        "",
        "## Summary",
        "",
        "| top_k | rewrite | avg_quality | route_match | source_hit | avg_context_chars | errors |",
        "|---:|:---:|---:|---:|---:|---:|---:|",
    ]

    for row in summary:
        lines.append(
            "| {top_k} | {rewrite_enabled} | {avg_quality_score} | {route_match_count} | "
            "{expected_source_hit_count} | {avg_context_chars} | {error_count} |".format(**row)
        )

    lines.extend(
        [
            "",
            "## Recommended Default",
            "",
            f"- top_k: {recommended['top_k']}",
            f"- rewrite_enabled: {recommended['rewrite_enabled']}",
            f"- avg_quality_score: {recommended['avg_quality_score']}",
            f"- avg_context_chars: {recommended['avg_context_chars']}",
            "",
            "## Case Details",
            "",
        ]
    )

    for row in rows:
        lines.extend(
            [
                f"### {row['case_id']} / top_k={row['top_k']} / rewrite={row['rewrite_enabled']}",
                "",
                f"- query: {row['query']}",
                f"- route: {row['actual_route']} / expected: {row['expected_route']} / match: {row['route_match']}",
                f"- source_hit: {row['expected_source_hit']}",
                f"- must_terms: {row['must_terms_hit']}/{row['must_terms_total']}",
                f"- context_chars: {row['context_chars']}",
                f"- quality_score: {row['quality_score']}",
                f"- chunks: {', '.join(row['chunk_ids']) if row['chunk_ids'] else 'none'}",
            ]
        )
        if row["error"]:
            lines.append(f"- error: {row['error']}")
        lines.append("")

    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="data/processed/evals")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    rows = run_experiment()
    summary = summarize_results(rows)
    recommended = select_recommended_config(summary)

    write_jsonl(output_dir / "retrieval_token_experiment.jsonl", rows)
    write_markdown_report(output_dir / "retrieval_token_experiment.md", rows, summary)

    print("SUMMARY")
    for row in summary:
        print(row)
    print("RECOMMENDED")
    print(recommended)
    print(f"saved: {output_dir / 'retrieval_token_experiment.jsonl'}")
    print(f"saved: {output_dir / 'retrieval_token_experiment.md'}")


if __name__ == "__main__":
    main()
