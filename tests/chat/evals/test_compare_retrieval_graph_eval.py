from app.chat.evals.compare_retrieval_graph_eval import (
    ComparisonRow,
    EvalScoreSet,
    average_scores,
    build_markdown,
    format_chunks,
)


def test_average_scores_compares_baseline_and_graph() -> None:
    rows = [
        ComparisonRow(
            case_id="case_a",
            query="질문",
            baseline_route="rag",
            graph_route="rag",
            baseline_chunks=["a:p1:c0"],
            graph_chunks=["a:p1:c0"],
            baseline_scores=EvalScoreSet(1, 1, 1, 1, 1),
            graph_scores=EvalScoreSet(1, 1, 0, 1, 2 / 3),
        ),
        ComparisonRow(
            case_id="case_b",
            query="질문",
            baseline_route="rag",
            graph_route="rag",
            baseline_chunks=["b:p1:c0"],
            graph_chunks=["b:p1:c0"],
            baseline_scores=EvalScoreSet(1, 1, 1, 1, 1),
            graph_scores=EvalScoreSet(1, 1, 1, 1, 1),
        ),
    ]

    assert average_scores(rows, "baseline").retrieval_quality == 1
    assert average_scores(rows, "graph").term_hit == 0.5


def test_build_markdown_contains_summary_table() -> None:
    rows = [
        ComparisonRow(
            case_id="definition_s0",
            query="S0?",
            baseline_route="rag",
            graph_route="rag",
            baseline_chunks=["wada:p1:c0"],
            graph_chunks=["wada:p1:c0"],
            baseline_scores=EvalScoreSet(1, 1, 1, 1, 1),
            graph_scores=EvalScoreSet(1, 1, 1, 1, 1),
        )
    ]

    markdown = build_markdown(rows, top_k=3, rewrite_enabled=True)

    assert "Average Scores" in markdown
    assert "baseline retrieval" in markdown
    assert "LangGraph retrieval" in markdown
    assert "definition_s0" in markdown


def test_format_chunks_handles_empty_list() -> None:
    assert format_chunks([]) == "-"
