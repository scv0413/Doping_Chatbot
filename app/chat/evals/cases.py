from dataclasses import dataclass


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    query: str
    expected_route: str
    expected_sources: tuple[str, ...]
    must_include_terms: tuple[str, ...]
    retrieval_terms: tuple[str, ...] = ()


DEFAULT_CASES = [
    EvalCase(
        case_id="definition_s0",
        query="S0 비승인약물이 뭐야?",
        expected_route="rag",
        expected_sources=("wada_prohibited_list_2026_ko",),
        must_include_terms=("S0", "비승인"),
    ),
    EvalCase(
        case_id="drug_tylenol",
        query="타이레놀 먹어도 돼?",
        expected_route="drug_search",
        expected_sources=(),
        must_include_terms=(),
    ),
    EvalCase(
        case_id="drug_pseudoephedrine",
        query="슈도에페드린 경기기간 중 먹어도 돼?",
        expected_route="drug_search_with_rag",
        expected_sources=("wada_prohibited_list_2026_ko",),
        must_include_terms=("Pseudoephedrine", "S6"),
        retrieval_terms=("Pseudoephedrine", "S6", "흥분제", "경기기간 중 금지"),
    ),
    EvalCase(
        case_id="procedure_tue",
        query="TUE는 어떻게 신청해? 대리 신청도 가능해?",
        expected_route="rag",
        expected_sources=("field_response_manual", "kada_anti_doping_rules_2021_ko"),
        must_include_terms=("TUE", "신청"),
    ),
    EvalCase(
        case_id="field_dco_identity",
        query="도핑 검사관 신분이 불분명하면 어떻게 확인해야 해?",
        expected_route="rag",
        expected_sources=("field_response_manual", "wada_isti_2023_en"),
        must_include_terms=("신분", "검사관"),
    ),
    EvalCase(
        case_id="field_night_blood",
        query="새벽에 혈액 시료 채취를 요청받으면 어떻게 대응해야 해?",
        expected_route="rag",
        expected_sources=("field_response_manual", "wada_isti_2023_en"),
        must_include_terms=("혈액", "시료"),
    ),
    EvalCase(
        case_id="field_injury_delay",
        query="부상 치료가 먼저 필요한데 도핑검사를 미뤄달라고 하면 거부로 보일 수 있어?",
        expected_route="rag",
        expected_sources=("field_response_manual", "kada_anti_doping_rules_2021_ko", "wada_isti_2023_en"),
        must_include_terms=("거부", "검사"),
    ),
    EvalCase(
        case_id="drug_nasal_spray",
        query="경기기간 중 코감기약을 비강 스프레이로 써도 돼?",
        expected_route="drug_search_with_rag",
        expected_sources=("field_response_manual",),
        must_include_terms=("제품명", "성분"),
        retrieval_terms=("제품명", "성분명", "KADA 약물검색", "비강 스프레이", "투여 경로", "용량"),
    ),
    EvalCase(
        case_id="field_leave_station",
        query="도핑검사 중 짐을 가지러 현장을 벗어나도 돼?",
        expected_route="rag",
        expected_sources=("field_response_manual", "kada_anti_doping_rules_2021_ko", "wada_isti_2023_en"),
        must_include_terms=("현장", "이탈"),
    ),
    EvalCase(
        case_id="drug_half_life",
        query="약물 반감기로 경기기간 복용 가능 여부를 판단해도 돼?",
        expected_route="rag",
        expected_sources=("field_response_manual", "wada_prohibited_list_2026_ko"),
        must_include_terms=("반감기", "경기기간"),
    ),
    EvalCase(
        case_id="isti_2023_interpreter_notification_en",
        query="When should an interpreter or third party be notified before athlete notification?",
        expected_route="rag",
        expected_sources=("wada_isti_2023_en",),
        must_include_terms=("interpreter", "third party"),
        retrieval_terms=("Article 5.3.7", "interpreter", "third party", "notification"),
    ),
    EvalCase(
        case_id="isti_2023_interpreter_notification_ko",
        query="도핑검사 통지 전에 통역이나 제3자에게 먼저 알려야 하나요?",
        expected_route="rag",
        expected_sources=("wada_isti_2023_en",),
        must_include_terms=("interpreter", "third party"),
        retrieval_terms=("Article 5.3.7", "interpreter", "third party", "notification"),
    ),
    EvalCase(
        case_id="isti_identity_documentation",
        query="도핑 검사관이 본인 신분증을 보여줘야 하나요? 선수 신분도 확인해야 하나요?",
        expected_route="rag",
        expected_sources=("wada_isti_2023_ko_human_reviewed",),
        must_include_terms=("신분", "권한"),
        retrieval_terms=("Article 5.3.3", "Article 5.3.4", "official documentation", "identification", "identity"),
    ),
    EvalCase(
        case_id="isti_notification_signature",
        query="도핑검사 통지서 서명을 거부하면 어떻게 돼?",
        expected_route="rag",
        expected_sources=("wada_isti_2023_ko_human_reviewed",),
        must_include_terms=("서명", "규정 미준수"),
        retrieval_terms=("Article 5.4.3", "sign", "refuses", "evades", "Failure to Comply"),
    ),
    EvalCase(
        case_id="isti_station_delay_observation",
        query="치료나 통역 때문에 도핑관리소 도착을 미뤄도 돼? 혼자 움직여도 돼?",
        expected_route="rag",
        expected_sources=("wada_isti_2023_ko_human_reviewed",),
        must_include_terms=("지연", "지속 관찰", "치료"),
        retrieval_terms=("Article 5.4.4", "delay", "continuous observation", "medical treatment", "interpreter"),
    ),
]


def case_to_inputs(case: EvalCase) -> dict[str, object]:
    return {
        "case_id": case.case_id,
        "query": case.query,
        "retrieval_terms": list(case.retrieval_terms),
    }


def case_to_outputs(case: EvalCase) -> dict[str, object]:
    return {
        "expected_route": case.expected_route,
        "expected_sources": list(case.expected_sources),
        "must_include_terms": list(case.must_include_terms),
    }


def find_case(case_id: str, cases: list[EvalCase] | None = None) -> EvalCase:
    resolved_cases = cases or DEFAULT_CASES
    for case in resolved_cases:
        if case.case_id == case_id:
            return case

    msg = f"Unknown eval case: {case_id}"
    raise ValueError(msg)
