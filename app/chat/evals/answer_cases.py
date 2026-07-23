from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AnswerEvalCase:
    case_id: str
    query: str
    expected_route: str
    must_include_groups: tuple[tuple[str, ...], ...]
    must_not_include_terms: tuple[str, ...]


ANSWER_EVAL_CASES = [
    AnswerEvalCase(
        case_id="definition_s0",
        query="S0 비승인약물이 뭐야?",
        expected_route="rag",
        must_include_groups=(
            ("S0",),
            ("비승인 약물", "비승인약물"),
            ("정부 보건기구", "정부 보건당국", "정부 산하의 보건기구", "정부산하의보건기구", "각국 정부의 보건기구", "각국정부의보건기구", "governmental health authority"),
            ("사람 치료용", "human therapeutic use"),
            ("승인하지 않은", "승인되지 않은", "approved"),
            ("약리적 물질", "pharmacological substance"),
            ("상시 금지", "prohibited at all times"),
            ("예시", "전부는", "국한되지", "not inclusive"),
            ("공식 금지목록", "금지목록", "official"),
        ),
        must_not_include_terms=("무조건 사용 가능", "확실히 허용", "절대 안전"),
    ),
    AnswerEvalCase(
        case_id="drug_pseudoephedrine",
        query="슈도에페드린 경기기간 중 먹어도 돼?",
        expected_route="drug_search_with_rag",
        must_include_groups=(
            ("경기기간 중 금지", "경기기간 중", "금지 가능"),
            ("슈도에페드린", "Pseudoephedrine"),
            ("S6",),
            ("흥분제", "stimulants"),
            ("소변", "용량", "농도", "urinary threshold"),
            ("제품명",),
            ("성분명", "성분"),
            ("팀 닥터", "약사", "KADA", "도핑 담당자"),
            ("단정", "공식 판정", "확인"),
        ),
        must_not_include_terms=("무조건 먹어도 된다", "확실히 허용된다", "절대 안전하다"),
    ),
    AnswerEvalCase(
        case_id="procedure_tue",
        query="TUE는 어떻게 신청해? 대리 신청도 가능해?",
        expected_route="rag",
        must_include_groups=(
            ("TUE", "치료목적사용면책"),
            ("금지약물", "금지방법"),
            ("의학적", "치료"),
            ("KADA", "공식 절차", "공식"),
            ("신청서", "신청"),
            ("의료자료", "진단자료", "의료"),
            ("대리", "선수지원요원", "도움"),
            ("경기 전", "시간 여유", "사전"),
            ("긴급", "사후"),
        ),
        must_not_include_terms=("항상 승인", "무조건 승인", "서류 없이 가능"),
    ),
    AnswerEvalCase(
        case_id="field_dco_identity",
        query="도핑 검사관 신분이 불분명하면 어떻게 확인해야 해?",
        expected_route="rag",
        must_include_groups=(
            ("충돌", "현장을 이탈", "이탈하지"),
            ("신분증", "신분"),
            ("소속", "권한"),
            ("절차 설명", "설명 요청"),
            ("통역", "팀 관계자", "동석자"),
            ("기록",),
            ("무단 거부", "거부로 보일"),
            ("이의제기", "보고"),
        ),
        must_not_include_terms=("그냥 거부", "현장을 떠나", "검사를 무시"),
    ),
    AnswerEvalCase(
        case_id="field_night_blood",
        query="새벽에 혈액 시료 채취를 요청받으면 어떻게 대응해야 해?",
        expected_route="rag",
        must_include_groups=(
            ("무단 거부", "현장을 이탈", "이탈하지"),
            ("검사관 신분", "신분"),
            ("절차",),
            ("통역", "팀 관계자", "동석자"),
            ("혈액 시료", "혈액"),
            ("사유", "설명"),
            ("의사소통", "도움"),
            ("안전", "의료상 우려", "의료"),
            ("대체 시료", "공식 근거", "단정"),
        ),
        must_not_include_terms=("혈액검사는 무조건 거부", "소변으로 반드시 대체", "그냥 거부"),
    ),
    AnswerEvalCase(
        case_id="isti_interpreter_third_party_notification",
        query="도핑검사 통지 전에 통역이나 제3자에게 먼저 알려야 하나요?",
        expected_route="rag",
        must_include_groups=(
            ("제3자",),
            ("통역",),
            ("통지",),
            ("미성년", "장애"),
            ("기록",),
            ("공식 문서", "원문", "WADA"),
        ),
        must_not_include_terms=("항상 제3자에게 알려야", "통역 없이 진행해야", "무조건 지연"),
    ),
    AnswerEvalCase(
        case_id="isti_notification_signature",
        query="도핑검사 통지서 서명을 거부하면 어떻게 돼?",
        expected_route="rag",
        must_include_groups=(
            ("서명", "sign"),
            ("거부", "회피", "refuses", "evades"),
            ("규정 미준수", "Failure to Comply"),
            ("기록", "보고", "document", "report"),
            ("공식 문서", "원문", "WADA"),
        ),
        must_not_include_terms=("서명하지 말고 떠나", "서명 거부하면 끝", "검사를 무시"),
    ),
    AnswerEvalCase(
        case_id="isti_station_delay_observation",
        query="치료나 통역 때문에 도핑관리소 도착을 미뤄도 돼? 혼자 움직여도 돼?",
        expected_route="rag",
        must_include_groups=(
            ("정당한 사유", "합리적인 요청", "delay"),
            ("치료", "medical treatment"),
            ("통역", "interpreter"),
            ("지속 관찰", "continuous observation", "계속 관찰"),
            ("DCO", "동행요원", "검사관"),
            ("공식 문서", "원문", "WADA"),
        ),
        must_not_include_terms=("자유롭게 현장을 벗어나", "혼자 움직여도 된다", "무조건 지연 가능"),
    ),
]


def answer_case_to_inputs(case: AnswerEvalCase) -> dict[str, Any]:
    return {
        "case_id": case.case_id,
        "query": case.query,
    }


def answer_case_to_outputs(case: AnswerEvalCase) -> dict[str, Any]:
    return {
        "expected_route": case.expected_route,
        "must_include_groups": [list(group) for group in case.must_include_groups],
        "must_not_include_terms": list(case.must_not_include_terms),
    }
