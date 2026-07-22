from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FieldScenarioEvalCase:
    case_id: str
    query: str
    expected_route: str
    must_include_groups: tuple[tuple[str, ...], ...]
    must_not_include_terms: tuple[str, ...]
    action_order_terms: tuple[str, ...]


FIELD_SCENARIO_EVAL_CASES = [
    FieldScenarioEvalCase(
        case_id="field_dco_identity",
        query="도핑 검사관 신분이 불분명하면 어떻게 확인해야 해?",
        expected_route="rag",
        must_include_groups=(
            ("신분증", "신분"),
            ("소속", "권한"),
            ("검사 통지", "통지 내용", "통지서"),
            ("정중", "차분", "협조"),
            ("통역", "팀 관계자", "트레이너", "동석"),
            ("기록", "검사서", "관련 기록"),
            ("무단 거부", "거부로 보일", "검사 방해"),
            ("현장 이탈", "이탈하지"),
            ("이의제기", "보고", "사후"),
        ),
        must_not_include_terms=("그냥 거부", "현장을 떠나", "검사를 무시", "몸싸움", "멱살"),
        action_order_terms=("신분", "통역", "기록"),
    ),
    FieldScenarioEvalCase(
        case_id="field_night_blood",
        query="새벽에 혈액 시료 채취를 요청받으면 어떻게 대응해야 해?",
        expected_route="rag",
        must_include_groups=(
            ("혈액 시료", "혈액"),
            ("검사관 신분", "신분"),
            ("시료 유형", "절차", "검사 목적"),
            ("새벽", "야간", "오후 11시", "오전 6시", "time slot"),
            ("통역", "팀 관계자", "트레이너", "동석"),
            ("잠", "인지", "의사소통"),
            ("기록", "검사서"),
            ("의료", "안전", "우려"),
            ("대체", "소변", "단정", "공식 확인"),
            ("무단 거부", "현장 이탈", "거부로 보일"),
        ),
        must_not_include_terms=("혈액검사는 무조건 거부", "소변으로 반드시 대체", "새벽 검사는 무조건 거부", "그냥 거부"),
        action_order_terms=("신분", "절차", "통역", "기록"),
    ),
    FieldScenarioEvalCase(
        case_id="field_injury_delay",
        query="부상 치료가 먼저 필요한데 도핑검사를 미뤄달라고 하면 거부로 보일 수 있어?",
        expected_route="rag",
        must_include_groups=(
            ("부상", "응급", "치료"),
            ("검사를 거부", "거부한다", "표현하지"),
            ("협조", "절차에 협조"),
            ("의료진", "의료"),
            ("기록", "검사서", "관련 기록"),
            ("통역", "팀 관계자", "트레이너", "동석"),
            ("무단", "현장 이탈", "연락 두절"),
            ("정당한 사유", "상황", "공식 절차"),
        ),
        must_not_include_terms=("치료가 먼저면 검사를 안 받아도 된다", "무조건 미룰 수 있다", "그냥 병원으로 가면 된다"),
        action_order_terms=("치료", "설명", "기록"),
    ),
    FieldScenarioEvalCase(
        case_id="field_leave_station",
        query="도핑검사 중 짐을 가지러 현장을 벗어나도 돼?",
        expected_route="rag",
        must_include_groups=(
            ("현장 이탈", "이탈"),
            ("검사관에게 알리고", "알린다", "허가"),
            ("동행", "동석", "감시"),
            ("짐", "휴대폰", "신분증", "의무용품"),
            ("무단", "거부", "회피"),
            ("기록", "검사서"),
            ("절차", "협조"),
        ),
        must_not_include_terms=("잠깐이면 그냥 다녀와도 된다", "말 없이 다녀와도 된다", "검사관 허락 없이"),
        action_order_terms=("알리고", "허가", "동행"),
    ),
    FieldScenarioEvalCase(
        case_id="field_tue_representative",
        query="TUE는 어떻게 신청해? 대리 신청도 가능해?",
        expected_route="rag",
        must_include_groups=(
            ("TUE", "치료목적사용면책"),
            ("금지약물", "금지방법"),
            ("의학적", "치료"),
            ("신청서", "신청"),
            ("의료자료", "진단자료", "처방"),
            ("대리", "선수지원요원", "보호자", "팀 닥터"),
            ("KADA", "공식 절차", "공식"),
            ("경기 전", "사전", "시간 여유"),
            ("긴급", "사후"),
            ("무조건 승인", "승인을 보장", "단정"),
        ),
        must_not_include_terms=("항상 승인", "무조건 승인", "서류 없이 가능", "대리인이 마음대로"),
        action_order_terms=("KADA", "신청", "의료"),
    ),
]


def field_scenario_case_to_inputs(case: FieldScenarioEvalCase) -> dict[str, Any]:
    return {
        "case_id": case.case_id,
        "query": case.query,
    }


def field_scenario_case_to_outputs(case: FieldScenarioEvalCase) -> dict[str, Any]:
    return {
        "expected_route": case.expected_route,
        "must_include_groups": [list(group) for group in case.must_include_groups],
        "must_not_include_terms": list(case.must_not_include_terms),
        "action_order_terms": list(case.action_order_terms),
    }
