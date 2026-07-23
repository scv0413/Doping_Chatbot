from app.chat.evals.answer_cases import ANSWER_EVAL_CASES, answer_case_to_inputs, answer_case_to_outputs
from app.chat.evals.langsmith_answer_eval import (
    build_answer_example_id,
    build_answer_target,
    build_langsmith_examples,
    citation_presence_evaluator,
    count_concept_hits,
    must_include_evaluator,
    must_not_include_evaluator,
    pipeline_error_evaluator,
    route_match_evaluator,
    safety_disclaimer_evaluator,
)
from app.chat.orchestration.pipeline.chat_pipeline import ChatPipelineResult
from app.chat.orchestration.router.intent_router import ChatRoute, RouteDecision
from app.chat.domain.policy.answer_policy import OFFICIAL_DECISION_DISCLAIMER


def fake_pipeline_runner(query: str, top_k: int, use_llm: bool) -> ChatPipelineResult:
    assert query == "S0 비승인약물이 뭐야?"
    assert top_k == 3
    assert use_llm is False
    return ChatPipelineResult(
        search_input={"query": query},
        decision=RouteDecision(route=ChatRoute.RAG, reason="test"),
        retrieval_matches=[],
        answer=(
            "## 답변 요약\n"
            "S0은 비승인 약물이며 정부 보건기구에서 사람 치료용으로 "
            "승인하지 않은 약리적 물질입니다. 상시 금지입니다.\n"
            "## 근거\n"
            "- wada (`wada:p1:c0`)\n"
            "## 주의\n"
            f"- {OFFICIAL_DECISION_DISCLAIMER}"
        ),
        errors=[],
    )


def test_answer_cases_convert_to_langsmith_io() -> None:
    case = ANSWER_EVAL_CASES[0]

    assert answer_case_to_inputs(case)["case_id"] == "definition_s0"
    assert answer_case_to_outputs(case)["expected_route"] == "rag"


def test_build_langsmith_examples_has_stable_ids() -> None:
    examples = build_langsmith_examples(ANSWER_EVAL_CASES[:1])

    assert examples[0]["id"] == build_answer_example_id("definition_s0")
    assert examples[0]["inputs"]["query"] == "S0 비승인약물이 뭐야?"
    assert examples[0]["outputs"]["expected_route"] == "rag"


def test_answer_target_returns_formatter_outputs() -> None:
    target = build_answer_target(top_k=3, use_llm=False, pipeline_runner=fake_pipeline_runner)

    outputs = target({"query": "S0 비승인약물이 뭐야?"})

    assert outputs["actual_route"] == "rag"
    assert outputs["use_llm"] is False
    assert outputs["answer_chars"] > 0
    assert outputs["errors"] == []


def test_answer_evaluators_score_expected_result() -> None:
    outputs = {
        "actual_route": "rag",
        "answer": (
            "S0은 비승인 약물이며 정부 보건기구에서 사람 치료용으로 승인하지 않은 "
            "약리적 물질입니다. 상시 금지입니다. 공식 금지목록 기준 확인이 필요합니다. "
            f"## 근거 (`wada:p1:c0`) ## 주의 {OFFICIAL_DECISION_DISCLAIMER}"
        ),
        "chunk_ids": ["wada:p1:c0"],
        "errors": [],
    }
    reference_outputs = {
        "expected_route": "rag",
        "must_include_groups": [
            ["S0"],
            ["비승인 약물"],
            ["정부 보건기구"],
            ["사람 치료용"],
        ],
        "must_not_include_terms": ["무조건 사용 가능"],
    }

    assert route_match_evaluator(outputs, reference_outputs)["score"] == 1
    assert must_include_evaluator(outputs, reference_outputs)["score"] == 1
    assert must_not_include_evaluator(outputs, reference_outputs)["score"] == 1
    assert citation_presence_evaluator(outputs, reference_outputs)["score"] == 1
    assert safety_disclaimer_evaluator(outputs, reference_outputs)["score"] == 1
    assert pipeline_error_evaluator(outputs, reference_outputs)["score"] == 1


def test_count_concept_hits_accepts_synonym_groups() -> None:
    answer = "정부 보건당국에서 사람 치료용으로 승인되지 않은 약리적 물질"
    groups = [["정부 보건기구", "정부 보건당국"], ["승인하지 않은", "승인되지 않은"]]

    assert count_concept_hits(answer, groups) == 2
