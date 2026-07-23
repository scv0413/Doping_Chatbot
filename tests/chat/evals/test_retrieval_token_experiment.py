from app.chat.evals.retrieval_token_experiment import (
    EvalCase,
    ExperimentConfig,
    evaluate_case,
    run_experiment,
    select_recommended_config,
    summarize_results,
)
from app.chat.domain.retrieval.schemas import RetrievalMatch, RetrievalMetadata


def fake_retriever(query: str, top_k: int) -> list[RetrievalMatch]:
    return [
        RetrievalMatch(
            rank=1,
            chunk_id="wada_prohibited_list_2026_ko:p5:c0",
            distance=0.2,
            metadata=RetrievalMetadata(
                source_id="wada_prohibited_list_2026_ko",
                title="금지목록 국제표준",
                page=5,
            ),
            text="S0 비승인 약물 상시 금지",
        )
    ][:top_k]


def test_evaluate_case_scores_expected_source_and_terms() -> None:
    case = EvalCase(
        case_id="definition_s0",
        query="S0 비승인약물이 뭐야?",
        expected_route="rag",
        expected_sources=("wada_prohibited_list_2026_ko",),
        must_include_terms=("S0", "비승인"),
    )

    row = evaluate_case(
        case=case,
        config=ExperimentConfig(top_k=3, rewrite_enabled=False),
        retriever=fake_retriever,
    )

    assert row["route_match"] is True
    assert row["expected_source_hit"] is True
    assert row["must_terms_hit"] == 2
    assert row["quality_score"] == 3


def test_run_experiment_and_summary_selects_best_config() -> None:
    rows = run_experiment(
        cases=[
            EvalCase(
                case_id="definition_s0",
                query="S0 비승인약물이 뭐야?",
                expected_route="rag",
                expected_sources=("wada_prohibited_list_2026_ko",),
                must_include_terms=("S0",),
            )
        ],
        configs=[
            ExperimentConfig(top_k=3, rewrite_enabled=False),
            ExperimentConfig(top_k=5, rewrite_enabled=True),
        ],
        retriever=fake_retriever,
    )

    summary = summarize_results(rows)
    recommended = select_recommended_config(summary)

    assert len(rows) == 2
    assert len(summary) == 2
    assert recommended["avg_quality_score"] == 3.0
