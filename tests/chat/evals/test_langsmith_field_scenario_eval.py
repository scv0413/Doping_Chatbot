from app.chat.evals.field_scenario_cases import (
    FIELD_SCENARIO_EVAL_CASES,
    field_scenario_case_to_inputs,
    field_scenario_case_to_outputs,
)
from app.chat.evals.langsmith_field_scenario_eval import (
    action_order_evaluator,
    build_field_scenario_example_id,
    build_field_scenario_target,
    build_langsmith_examples,
    citation_presence_evaluator,
    field_required_info_evaluator,
    field_safety_posture_evaluator,
    pipeline_error_evaluator,
    route_match_evaluator,
    safety_disclaimer_evaluator,
    unsafe_action_evaluator,
)
from app.chat.pipeline.chat_pipeline import ChatPipelineResult
from app.chat.policy.answer_policy import OFFICIAL_DECISION_DISCLAIMER
from app.chat.retrieval.schemas import RetrievalMatch, RetrievalMetadata
from app.chat.router.intent_router import ChatRoute, RouteDecision


def fake_field_pipeline_runner(query: str, top_k: int, use_llm: bool) -> ChatPipelineResult:
    assert query == "도핑 검사관 신분이 불분명하면 어떻게 확인해야 해?"
    assert top_k == 3
    assert use_llm is True
    return ChatPipelineResult(
        search_input={"query": query},
        decision=RouteDecision(route=ChatRoute.RAG, reason="test", matched_terms=["검사관", "신분"]),
        retrieval_query=query,
        rewritten_query="도핑 검사관 시료채취요원 신분증 소속 권한 통역 기록",
        retrieval_matches=[
            RetrievalMatch(
                rank=1,
                chunk_id="field_response_manual:s1:c0",
                distance=0.1,
                metadata=RetrievalMetadata(
                    source_id="field_response_manual",
                    title="현장 대응 매뉴얼",
                    chunk_id="field_response_manual:s1:c0",
                ),
                text="검사관 신분 확인, 통역 요청, 기록, 무단 거부와 현장 이탈 주의.",
            )
        ],
        answer=(
            "검사관 신분이 불분명하면 즉시 거부하지 말고 정중하게 신분증, 소속, 권한, 검사 통지 내용을 확인하세요. "
            "통역, 팀 관계자 또는 트레이너 동석을 요청하고, 확인이 어려운 점은 검사서나 관련 기록에 남기세요. "
            "무단 거부, 현장 이탈, 검사 방해로 보일 행동은 피하고 절차에는 협조하되 사후 이의제기나 보고를 준비하세요. "
            "공식 KADA 규정과 절차 확인이 필요합니다. "
            f"{OFFICIAL_DECISION_DISCLAIMER}\n\n"
            "## 근거\n"
            "- 현장 대응 매뉴얼 (`field_response_manual:s1:c0`)"
        ),
        errors=[],
    )


def test_field_scenario_cases_convert_to_langsmith_io() -> None:
    case = FIELD_SCENARIO_EVAL_CASES[0]

    assert field_scenario_case_to_inputs(case)["case_id"] == "field_dco_identity"
    assert field_scenario_case_to_outputs(case)["expected_route"] == "rag"
    assert field_scenario_case_to_outputs(case)["action_order_terms"] == ["신분", "통역", "기록"]


def test_build_langsmith_examples_has_stable_ids() -> None:
    examples = build_langsmith_examples(FIELD_SCENARIO_EVAL_CASES[:1])

    assert examples[0]["id"] == build_field_scenario_example_id("field_dco_identity")
    assert examples[0]["inputs"]["query"] == "도핑 검사관 신분이 불분명하면 어떻게 확인해야 해?"
    assert examples[0]["outputs"]["expected_route"] == "rag"


def test_field_scenario_target_returns_outputs() -> None:
    target = build_field_scenario_target(top_k=3, use_llm=True, pipeline_runner=fake_field_pipeline_runner)

    outputs = target({"query": FIELD_SCENARIO_EVAL_CASES[0].query})

    assert outputs["actual_route"] == "rag"
    assert outputs["use_llm"] is True
    assert outputs["chunk_ids"] == ["field_response_manual:s1:c0"]
    assert outputs["errors"] == []


def test_field_scenario_evaluators_score_expected_result() -> None:
    target = build_field_scenario_target(top_k=3, use_llm=True, pipeline_runner=fake_field_pipeline_runner)
    outputs = target({"query": FIELD_SCENARIO_EVAL_CASES[0].query})
    refs = field_scenario_case_to_outputs(FIELD_SCENARIO_EVAL_CASES[0])

    assert route_match_evaluator(outputs, refs)["score"] == 1
    assert field_required_info_evaluator(outputs, refs)["score"] == 1
    assert unsafe_action_evaluator(outputs, refs)["score"] == 1
    assert action_order_evaluator(outputs, refs)["score"] == 1
    assert field_safety_posture_evaluator(outputs, refs)["score"] == 1
    assert citation_presence_evaluator(outputs, refs)["score"] == 1
    assert safety_disclaimer_evaluator(outputs, refs)["score"] == 1
    assert pipeline_error_evaluator(outputs, refs)["score"] == 1


def test_unsafe_action_evaluator_fails_on_bad_instruction() -> None:
    outputs = {"answer": "상황이 불쾌하면 그냥 거부하고 현장을 떠나도 됩니다."}
    refs = {"must_not_include_terms": ["그냥 거부", "현장을 떠나"]}

    result = unsafe_action_evaluator(outputs, refs)

    assert result["score"] == 0
    assert "그냥 거부" in result["comment"]


def test_action_order_evaluator_allows_partial_score() -> None:
    outputs = {"answer": "먼저 기록하고 나중에 신분 확인을 합니다."}
    refs = {"action_order_terms": ["신분", "통역", "기록"]}

    result = action_order_evaluator(outputs, refs)

    assert result["score"] == 0.5
