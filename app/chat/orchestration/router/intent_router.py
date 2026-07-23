from enum import StrEnum

from pydantic import BaseModel, Field


class ChatRoute(StrEnum):
    RAG = "rag"
    DRUG_SEARCH = "drug_search"
    DRUG_SEARCH_WITH_RAG = "drug_search_with_rag"


class RouteDecision(BaseModel):
    route: ChatRoute
    reason: str
    matched_terms: list[str] = Field(default_factory=list)


DRUG_SUBSTANCE_TERMS = {
    "아세트아미노펜",
    "acetaminophen",
    "paracetamol",
    "슈도에페드린",
    "pseudoephedrine",
    "테스토스테론",
    "testosterone",
    "타이레놀",
    "에페드린",
    "ephedrine",
    "메틸에페드린",
    "메칠에페드린",
    "methylephedrine",
    "카틴",
    "cathine",
    "노르슈도에페드린",
    "norpseudoephedrine",
    "트라마돌",
    "tramadol",
}

DRUG_CONTEXT_TERMS = {
    "약",
    "약물",
    "금지약물",
    "성분",
    "성분명",
    "제품명",
    "복용",
    "먹어도",
    "사용",
    "감기약",
    "코감기",
    "스프레이",
    "분사",
}

REGULATION_CONTEXT_TERMS = {
    "규정",
    "금지목록",
    "금지약물",
    "금지방법",
    "경기기간",
    "경기 기간",
    "상시 금지",
    "투여",
    "투여경로",
    "용량",
    "농도",
    "종목",
    "TUE",
    "치료목적사용면책",
}


PROHIBITED_CATEGORY_TERMS = {
    "S0",
    "S1",
    "S2",
    "S3",
    "S4",
    "S5",
    "S6",
    "S7",
    "S8",
    "S9",
    "M1",
    "M2",
    "M3",
    "P1",
    "비승인약물",
    "동화작용제",
    "흥분제",
    "금지분류",
}

RAG_ONLY_TERMS = {
    "반감기",
    "검사관",
    "시료채취",
    "혈액",
    "새벽",
    "거부",
    "회피",
    "신분",
    "대리 신청",
    "신청 방법",
}


def route_question(query: str) -> RouteDecision:
    normalized_query = normalize_query(query)
    matched_drug_terms = find_terms(normalized_query, DRUG_SUBSTANCE_TERMS | DRUG_CONTEXT_TERMS)
    matched_regulation_terms = find_terms(normalized_query, REGULATION_CONTEXT_TERMS)
    matched_category_terms = find_terms(normalized_query, PROHIBITED_CATEGORY_TERMS)
    matched_rag_only_terms = find_terms(normalized_query, RAG_ONLY_TERMS)

    matched_specific_drug_terms = find_terms(normalized_query, DRUG_SUBSTANCE_TERMS)

    if matched_category_terms and not matched_specific_drug_terms:
        return RouteDecision(
            route=ChatRoute.RAG,
            reason="금지목록 분류나 규정 정의를 묻는 질문입니다.",
            matched_terms=dedupe_terms([*matched_category_terms, *matched_regulation_terms]),
        )

    if "반감기" in matched_rag_only_terms and matched_specific_drug_terms:
        return RouteDecision(
            route=ChatRoute.DRUG_SEARCH_WITH_RAG,
            reason="특정 성분의 반감기 참고와 도핑 규정 근거가 함께 필요한 질문입니다.",
            matched_terms=dedupe_terms([*matched_specific_drug_terms, *matched_rag_only_terms, *matched_regulation_terms]),
        )

    if "반감기" in matched_rag_only_terms and not matched_specific_drug_terms:
        return RouteDecision(
            route=ChatRoute.RAG,
            reason="특정 제품 조회보다 약물 정보 해석 기준을 묻는 질문입니다.",
            matched_terms=dedupe_terms([*matched_rag_only_terms, *matched_regulation_terms]),
        )

    if matched_drug_terms and matched_regulation_terms:
        return RouteDecision(
            route=ChatRoute.DRUG_SEARCH_WITH_RAG,
            reason="약물 조회와 규정 근거가 함께 필요한 질문입니다.",
            matched_terms=dedupe_terms([*matched_drug_terms, *matched_regulation_terms]),
        )

    if matched_drug_terms:
        return RouteDecision(
            route=ChatRoute.DRUG_SEARCH,
            reason="제품명, 성분명 또는 약물 사용 가능 여부를 묻는 질문입니다.",
            matched_terms=matched_drug_terms,
        )

    if matched_rag_only_terms:
        return RouteDecision(
            route=ChatRoute.RAG,
            reason="도핑검사 절차, TUE, 권리와 의무 등 문서 근거 검색이 필요한 질문입니다.",
            matched_terms=matched_rag_only_terms,
        )

    return RouteDecision(
        route=ChatRoute.RAG,
        reason="명확한 약물 조회 신호가 없어 기본 RAG 검색으로 처리합니다.",
    )


def find_terms(normalized_query: str, terms: set[str]) -> list[str]:
    return sorted(term for term in terms if normalize_query(term) in normalized_query)


def normalize_query(query: str) -> str:
    return query.strip().casefold().replace(" ", "")


def dedupe_terms(terms: list[str]) -> list[str]:
    return list(dict.fromkeys(terms))
