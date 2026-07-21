from app.chat.evals.cases import DEFAULT_CASES, case_to_inputs, case_to_outputs, find_case
from app.chat.evals.langsmith_retrieval_eval import (
    build_example_id,
    build_langsmith_examples,
    build_retrieval_target,
    context_budget_evaluator,
    retrieval_quality_evaluator,
    route_match_evaluator,
    source_hit_evaluator,
    term_hit_evaluator,
)
from app.chat.evals.retrieval_token_experiment import ExperimentConfig
from app.chat.retrieval.schemas import RetrievalMatch, RetrievalMetadata


def fake_retriever(query: str, top_k: int) -> list[RetrievalMatch]:
    assert top_k == 3
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
    ]


def test_cases_convert_to_langsmith_io() -> None:
    case = find_case("definition_s0")

    assert case_to_inputs(case)["query"] == "S0 비승인약물이 뭐야?"
    assert case_to_outputs(case)["expected_route"] == "rag"


def test_build_langsmith_examples_has_stable_ids() -> None:
    examples = build_langsmith_examples(DEFAULT_CASES[:1])

    assert examples[0]["id"] == build_example_id("definition_s0")
    assert examples[0]["inputs"]["case_id"] == "definition_s0"
    assert examples[0]["outputs"]["expected_sources"] == ["wada_prohibited_list_2026_ko"]


def test_retrieval_target_returns_retrieval_only_outputs() -> None:
    target = build_retrieval_target(
        config=ExperimentConfig(top_k=3, rewrite_enabled=True),
        retriever=fake_retriever,
    )

    outputs = target({"query": "S0 비승인약물이 뭐야?", "retrieval_terms": []})

    assert outputs["actual_route"] == "rag"
    assert outputs["source_ids"] == ["wada_prohibited_list_2026_ko"]
    assert outputs["chunk_ids"] == ["wada_prohibited_list_2026_ko:p5:c0"]
    assert outputs["context_chars"] > 0
    assert outputs["error"] is None


def test_evaluators_score_expected_result() -> None:
    outputs = {
        "actual_route": "rag",
        "source_ids": ["wada_prohibited_list_2026_ko"],
        "retrieved_text": "S0 비승인 약물 상시 금지",
        "context_chars": 200,
        "match_count": 1,
        "error": None,
    }
    reference_outputs = {
        "expected_route": "rag",
        "expected_sources": ["wada_prohibited_list_2026_ko"],
        "must_include_terms": ["S0", "비승인"],
    }

    assert route_match_evaluator(outputs, reference_outputs)["score"] == 1
    assert source_hit_evaluator(outputs, reference_outputs)["score"] == 1
    assert term_hit_evaluator(outputs, reference_outputs)["score"] == 1
    assert context_budget_evaluator(outputs, reference_outputs)["score"] == 1
    assert retrieval_quality_evaluator(outputs, reference_outputs)["score"] == 1
