TERM_EXPANSIONS = {
    "검사관": [
        "도핑검사관",
        "시료채취요원",
        "DCO",
        "Sample Collection Personnel",
    ],
    "신분": [
        "신분 확인",
        "소속기관",
        "검사 권한",
        "통지",
        "notification",
        "identification",
    ],
    "새벽": [
        "오후 11시",
        "오전 6시",
        "야간 검사",
        "overnight testing",
        "11 p.m.",
        "6 a.m.",
        "60분",
        "60-minute timeslot",
    ],
    "혈액": [
        "혈액 시료",
        "혈액 시료 채취",
        "blood sample",
        "blood collection",
        "BCO",
        "Blood Collection Officer",
    ],
    "거부": [
        "시료채취 거부",
        "시료채취 회피",
        "시료채취 실패",
        "refusal",
        "evasion",
        "failure to comply",
    ],
    "회피": [
        "시료채취 회피",
        "evasion",
        "failure to comply",
    ],
    "서명": [
        "통지서 서명",
        "통지 확인",
        "Article 5.4.3",
        "Failure to Comply",
        "document",
        "report",
    ],
    "통지서": [
        "통지서 서명",
        "Article 5.4.3",
        "Failure to Comply",
    ],
    "지연": [
        "도핑관리소 보고 지연",
        "일시 이탈",
        "지속 관찰",
        "continuous observation",
        "Article 5.4.4",
        "DCO",
    ],
    "미뤄": [
        "도핑관리소 보고 지연",
        "지속 관찰",
        "continuous observation",
        "Article 5.4.4",
    ],
    "혼자": [
        "지속 관찰",
        "continuous observation",
        "Article 5.4.4",
    ],
    "TUE": [
        "치료목적사용면책",
        "치료목적사용면책 신청",
        "Therapeutic Use Exemption",
        "Therapeutic Use Exemption application",
    ],
    "통역": [
        "interpreter",
        "Article 5.3.7",
        "third party",
        "notification",
    ],
    "제3자": [
        "third party",
        "prior notification",
        "Article 5.3.7",
        "interpreter",
    ],
    "통지": [
        "notification",
        "prior notification",
        "Article 5.3.7",
        "DCO",
    ],
    "대리": [
        "위임받은 선수지원요원",
        "선수지원요원",
        "athlete support personnel",
    ],
    "신청": [
        "온라인",
        "팩스",
        "이메일",
        "KADA 누리집",
        "online",
        "fax",
        "email",
    ],
    "금지약물": [
        "금지약물",
        "금지방법",
        "prohibited substance",
        "prohibited method",
        "약물검색",
        "성분명",
        "제품명",
    ],
    "코감기": [
        "제품명",
        "성분명",
        "약물검색",
        "KADA 금지약물 검색서비스",
        "투여 경로",
        "용량",
        "비강 스프레이",
        "product name",
        "ingredient",
        "substance",
    ],
}


def rewrite_query(query: str) -> str:
    expansions: list[str] = []

    for trigger, terms in TERM_EXPANSIONS.items():
        if trigger in query:
            expansions.extend(terms)

    if not expansions:
        return query

    unique_expansions = list(dict.fromkeys(expansions))
    return f"{query}\n{' '.join(unique_expansions)}"
