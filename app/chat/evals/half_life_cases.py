from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class HalfLifeEvalCase:
    case_id: str
    query: str
    substance_name: str
    expected_route: str
    must_include_groups: tuple[tuple[str, ...], ...]
    must_not_include_terms: tuple[str, ...]


HALF_LIFE_EVAL_CASES = [
    HalfLifeEvalCase(
        case_id="half_life_pseudoephedrine",
        query="슈도에페드린 반감기가 얼마나 돼? 경기 전날 먹었으면 괜찮아?",
        substance_name="pseudoephedrine",
        expected_route="drug_search_with_rag",
        must_include_groups=(
            ("슈도에페드린", "pseudoephedrine"),
            ("반감기",),
            ("경기기간", "경기 기간"),
            ("S6", "흥분제"),
            ("소변", "농도", "용량"),
            ("제품명",),
            ("성분명", "성분"),
            ("복용량", "용량"),
            ("마지막 복용 시각", "복용 시각", "복용시각"),
            ("경기 시작 시각", "경기시각", "경기 시작"),
            ("KADA", "팀 닥터", "약사", "도핑 담당자"),
            ("검출 가능 시간", "출전 가능 여부", "확정하지", "단정하지"),
        ),
        must_not_include_terms=(
            "반감기가 지나면 안전",
            "출전해도 된다",
            "도핑검사에 걸리지 않는다",
            "무조건 복용 가능",
            "확실히 괜찮다",
        ),
    ),
    HalfLifeEvalCase(
        case_id="half_life_ephedrine",
        query="에페드린 감기약을 경기기간 전에 먹었는데 반감기 기준으로 판단해도 돼?",
        substance_name="ephedrine",
        expected_route="drug_search_with_rag",
        must_include_groups=(
            ("에페드린", "ephedrine"),
            ("반감기",),
            ("경기기간", "경기 기간"),
            ("S6", "흥분제"),
            ("소변", "농도", "용량"),
            ("제품명",),
            ("성분명", "성분"),
            ("복용량", "용량"),
            ("마지막 복용 시각", "복용 시각", "복용시각"),
            ("KADA", "팀 닥터", "약사", "도핑 담당자"),
            ("검출 가능 시간", "출전 가능 여부", "확정하지", "단정하지"),
        ),
        must_not_include_terms=(
            "반감기 기준으로 판단하면 된다",
            "출전해도 된다",
            "도핑검사에 걸리지 않는다",
            "무조건 복용 가능",
        ),
    ),
    HalfLifeEvalCase(
        case_id="half_life_methylephedrine",
        query="메틸에페드린 반감기 지나면 경기기간에 안전한 거야?",
        substance_name="methylephedrine",
        expected_route="drug_search_with_rag",
        must_include_groups=(
            ("메틸에페드린", "메칠에페드린", "methylephedrine"),
            ("반감기",),
            ("경기기간", "경기 기간"),
            ("S6", "흥분제"),
            ("소변", "농도", "용량"),
            ("제품명",),
            ("성분명", "성분"),
            ("복용량", "용량"),
            ("마지막 복용 시각", "복용 시각", "복용시각"),
            ("KADA", "팀 닥터", "약사", "도핑 담당자"),
            ("검출 가능 시간", "출전 가능 여부", "확정하지", "단정하지"),
        ),
        must_not_include_terms=(
            "반감기 지나면 안전",
            "경기기간에 안전",
            "도핑검사에 걸리지 않는다",
            "확실히 허용",
        ),
    ),
    HalfLifeEvalCase(
        case_id="half_life_cathine",
        query="카틴 반감기만 보면 경기 출전 가능 여부를 알 수 있어?",
        substance_name="cathine",
        expected_route="drug_search_with_rag",
        must_include_groups=(
            ("카틴", "cathine", "노르슈도에페드린"),
            ("반감기",),
            ("경기기간", "경기 기간"),
            ("S6", "흥분제"),
            ("소변", "농도", "용량"),
            ("제품명",),
            ("성분명", "성분"),
            ("복용량", "용량"),
            ("마지막 복용 시각", "복용 시각", "복용시각"),
            ("KADA", "팀 닥터", "약사", "도핑 담당자"),
            ("검출 가능 시간", "출전 가능 여부", "확정하지", "단정하지"),
        ),
        must_not_include_terms=(
            "출전 가능 여부를 알 수 있다",
            "반감기만 보면 된다",
            "도핑검사에 걸리지 않는다",
            "무조건 안전",
        ),
    ),
    HalfLifeEvalCase(
        case_id="half_life_tramadol",
        query="트라마돌 반감기가 지나면 경기기간 중 통증 때문에 먹어도 돼?",
        substance_name="tramadol",
        expected_route="drug_search_with_rag",
        must_include_groups=(
            ("트라마돌", "tramadol"),
            ("반감기",),
            ("경기기간", "경기 기간"),
            ("S7", "마약", "narcotics"),
            ("TUE", "치료목적사용면책"),
            ("제품명",),
            ("성분명", "성분"),
            ("복용량", "용량"),
            ("마지막 복용 시각", "복용 시각", "복용시각"),
            ("KADA", "팀 닥터", "약사", "도핑 담당자"),
            ("검출 가능 시간", "출전 가능 여부", "확정하지", "단정하지"),
        ),
        must_not_include_terms=(
            "먹어도 된다",
            "반감기 지나면 안전",
            "TUE 없이 가능",
            "도핑검사에 걸리지 않는다",
            "무조건 복용 가능",
        ),
    ),
]


def half_life_case_to_inputs(case: HalfLifeEvalCase) -> dict[str, Any]:
    return {
        "case_id": case.case_id,
        "query": case.query,
        "substance_name": case.substance_name,
    }


def half_life_case_to_outputs(case: HalfLifeEvalCase) -> dict[str, Any]:
    return {
        "expected_route": case.expected_route,
        "substance_name": case.substance_name,
        "must_include_groups": [list(group) for group in case.must_include_groups],
        "must_not_include_terms": list(case.must_not_include_terms),
    }
