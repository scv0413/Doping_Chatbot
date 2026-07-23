import argparse
import uuid
from collections.abc import Callable
from typing import Any

from langsmith import Client, evaluate, traceable

from app.core.config import settings
from app.chat.evals.field_scenario_cases import (
    FIELD_SCENARIO_EVAL_CASES,
    FieldScenarioEvalCase,
    field_scenario_case_to_inputs,
    field_scenario_case_to_outputs,
)
from app.chat.evals.langsmith_answer_eval import count_concept_hits, normalize_text
from app.chat.pipeline.chat_pipeline import ChatPipelineResult, run_chat_pipeline
from app.chat.policy.answer_policy import OFFICIAL_DECISION_DISCLAIMER, get_answer_rule

DATASET_NAME = "doping-chatbot-field-scenario-v1"
DATASET_DESCRIPTION = "Field scenario answer evaluation cases for formatter and LLM chain comparison."
EXAMPLE_NAMESPACE = uuid.UUID("d07cb9fd-43f4-4277-9da4-f175db849119")
DEFAULT_TOP_K = 3

PipelineRunner = Callable[..., ChatPipelineResult]


def build_field_scenario_example_id(case_id: str) -> uuid.UUID:
    return uuid.uuid5(EXAMPLE_NAMESPACE, case_id)


def get_or_create_dataset(
    client: Client,
    dataset_name: str = DATASET_NAME,
    description: str = DATASET_DESCRIPTION,
) -> object:
    try:
        return client.read_dataset(dataset_name=dataset_name)
    except Exception:
        return client.create_dataset(
            dataset_name=dataset_name,
            description=description,
            metadata={"app": "doping-chatbot", "eval_type": "field-scenario-answer"},
        )


def build_langsmith_examples(cases: list[FieldScenarioEvalCase] | None = None) -> list[dict[str, Any]]:
    resolved_cases = cases or FIELD_SCENARIO_EVAL_CASES
    return [
        {
            "id": build_field_scenario_example_id(case.case_id),
            "inputs": field_scenario_case_to_inputs(case),
            "outputs": field_scenario_case_to_outputs(case),
            "metadata": {"case_id": case.case_id, "scenario_type": "field"},
        }
        for case in resolved_cases
    ]


def upsert_dataset_examples(
    client: Client,
    dataset_name: str = DATASET_NAME,
    cases: list[FieldScenarioEvalCase] | None = None,
) -> object | None:
    dataset = get_or_create_dataset(client=client, dataset_name=dataset_name)
    examples = build_langsmith_examples(cases)
    try:
        return client.create_examples(dataset_name=dataset_name, examples=examples)
    except Exception as exc:
        if "already exists" not in str(exc) and "Conflict" not in type(exc).__name__:
            raise

    for example in examples:
        client.update_example(
            example_id=example["id"],
            inputs=example["inputs"],
            outputs=example["outputs"],
            metadata=example["metadata"],
            dataset_id=getattr(dataset, "id", None),
        )
    return None


def build_field_scenario_target(
    top_k: int = DEFAULT_TOP_K,
    use_llm: bool = False,
    pipeline_runner: PipelineRunner = run_chat_pipeline,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    target_name = "field_scenario_answer_chain" if use_llm else "field_scenario_formatter"

    @traceable(name=f"{target_name}_top{top_k}")
    def target(inputs: dict[str, Any]) -> dict[str, Any]:
        query = str(inputs["query"])
        result = pipeline_runner(query, top_k=top_k, use_llm=use_llm)
        answer = result.answer
        return {
            "answer": answer,
            "actual_route": result.decision.route.value,
            "retrieval_query": result.retrieval_query,
            "rewritten_query": result.rewritten_query,
            "source_ids": [match.source_id for match in result.retrieval_matches],
            "chunk_ids": [match.chunk_id for match in result.retrieval_matches],
            "errors": [error.model_dump() for error in result.errors],
            "answer_chars": len(answer),
            "use_llm": use_llm,
            "top_k": top_k,
        }

    return target


def route_match_evaluator(outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> dict[str, Any]:
    expected_route = reference_outputs.get("expected_route")
    actual_route = outputs.get("actual_route")
    return {
        "key": "field_route_match",
        "score": int(actual_route == expected_route),
        "comment": f"expected={expected_route}, actual={actual_route}",
    }


def field_required_info_evaluator(outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> dict[str, Any]:
    answer = str(outputs.get("answer", ""))
    groups = list(reference_outputs.get("must_include_groups", []))
    hits = count_concept_hits(answer, groups)
    return {
        "key": "field_required_info",
        "score": hits / len(groups) if groups else 1,
        "comment": f"concept_hits={hits}/{len(groups)}",
    }


def unsafe_action_evaluator(outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> dict[str, Any]:
    answer = extract_claim_text(str(outputs.get("answer", "")))
    normalized_answer = normalize_text(answer)
    banned_terms = list(reference_outputs.get("must_not_include_terms", []))
    found = [
        term
        for term in banned_terms
        if normalize_text(term) in normalized_answer and not is_negated_safety_phrase(normalized_answer, term)
    ]
    return {
        "key": "field_unsafe_action_absent",
        "score": int(not found),
        "comment": f"found={found}",
    }


def is_negated_safety_phrase(normalized_answer: str, term: str) -> bool:
    normalized_term = normalize_text(term)
    term_index = normalized_answer.find(normalized_term)
    if term_index < 0:
        return False

    nearby_text = normalized_answer[term_index : term_index + len(normalized_term) + 28]
    return any(
        negation in nearby_text
        for negation in (
            "아닙니다",
            "아니다",
            "없습니다",
            "없다",
            "않습니다",
            "않다",
            "아니므로",
            "보장하는절차가아니",
            "단정하지",
            "확정하지",
        )
    )


def action_order_evaluator(outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> dict[str, Any]:
    answer = extract_claim_text(str(outputs.get("answer", "")))
    terms = list(reference_outputs.get("action_order_terms", []))
    positions = [find_first_position(answer, term) for term in terms]
    present_positions = [position for position in positions if position >= 0]
    has_all_terms = len(present_positions) == len(terms)
    ordered = has_all_terms and present_positions == sorted(present_positions)
    if not terms:
        score = 1
    elif ordered:
        score = 1
    else:
        score = len(present_positions) / len(terms) * 0.75
    return {
        "key": "field_action_order",
        "score": score,
        "comment": f"terms={terms}, positions={positions}",
    }


def field_safety_posture_evaluator(outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> dict[str, Any]:
    del reference_outputs
    answer = str(outputs.get("answer", ""))
    groups = [
        ["거부", "회피", "방해", "불이익"],
        ["정중", "차분", "협조"],
        ["기록", "검사서", "보고"],
        ["통역", "팀 관계자", "트레이너", "동석"],
        ["공식", "KADA", "규정"],
    ]
    hits = count_concept_hits(answer, groups)
    return {
        "key": "field_safety_posture",
        "score": hits / len(groups),
        "comment": f"posture_hits={hits}/{len(groups)}",
    }


def citation_presence_evaluator(outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> dict[str, Any]:
    del reference_outputs
    answer = str(outputs.get("answer", ""))
    has_citation_section = "## 근거" in answer
    has_chunk_id = bool(outputs.get("chunk_ids")) and ":" in answer
    return {
        "key": "field_citation_presence",
        "score": int(has_citation_section and has_chunk_id),
        "comment": (
            f"{get_answer_rule('explicit_citations').name}: "
            f"has_citation_section={has_citation_section}, has_chunk_id={has_chunk_id}"
        ),
    }


def safety_disclaimer_evaluator(outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> dict[str, Any]:
    del reference_outputs
    answer = str(outputs.get("answer", ""))
    required = normalize_text(OFFICIAL_DECISION_DISCLAIMER)
    score = int(required in normalize_text(answer))
    return {
        "key": "field_safety_disclaimer",
        "score": score,
        "comment": f"{get_answer_rule('apply_safety_caveats').name}: requires policy official decision disclaimer",
    }


def pipeline_error_evaluator(outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> dict[str, Any]:
    del reference_outputs
    errors = list(outputs.get("errors", []))
    return {
        "key": "field_pipeline_errors",
        "score": int(not errors),
        "comment": f"errors={len(errors)}",
    }


def extract_claim_text(answer: str) -> str:
    evidence_markers = ("\n## 근거 핵심", "\n## 근거")
    end_index = len(answer)
    for marker in evidence_markers:
        marker_index = answer.find(marker)
        if marker_index >= 0:
            end_index = min(end_index, marker_index)
    return answer[:end_index]


def find_first_position(answer: str, term: str) -> int:
    normalized_answer = normalize_text(answer)
    normalized_term = normalize_text(term)
    return normalized_answer.find(normalized_term)


def run_langsmith_field_scenario_eval(
    dataset_name: str = DATASET_NAME,
    top_k: int = DEFAULT_TOP_K,
    use_llm: bool = False,
    upload_dataset: bool = True,
    client: Client | None = None,
) -> object:
    resolved_client = client or Client()
    if upload_dataset:
        upsert_dataset_examples(client=resolved_client, dataset_name=dataset_name)

    experiment_kind = "field-scenario-answer-chain" if use_llm else "field-scenario-formatter"
    return evaluate(
        build_field_scenario_target(top_k=top_k, use_llm=use_llm),
        data=dataset_name,
        evaluators=[
            route_match_evaluator,
            field_required_info_evaluator,
            unsafe_action_evaluator,
            action_order_evaluator,
            field_safety_posture_evaluator,
            citation_presence_evaluator,
            safety_disclaimer_evaluator,
            pipeline_error_evaluator,
        ],
        experiment_prefix=f"{experiment_kind}-top{top_k}",
        description="Field scenario answer evaluation comparing deterministic formatter and LLM chain output.",
        metadata={
            "top_k": top_k,
            "use_llm": use_llm,
            "project": settings.langsmith_project,
        },
        client=resolved_client,
        blocking=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-name", default=DATASET_NAME)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--use-llm", action="store_true")
    parser.add_argument("--skip-dataset-upload", action="store_true")
    args = parser.parse_args()

    result = run_langsmith_field_scenario_eval(
        dataset_name=args.dataset_name,
        top_k=args.top_k,
        use_llm=args.use_llm,
        upload_dataset=not args.skip_dataset_upload,
    )
    print(result)


if __name__ == "__main__":
    main()
