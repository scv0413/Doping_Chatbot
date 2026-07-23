from collections.abc import Mapping
from typing import Any

from app.chat.domain.pharmacology.knowledge_base import PHARMACOLOGY_REFERENCE_RECORDS
from app.chat.domain.pharmacology.schemas import PharmacologyInfoResult, PharmacologyInfoStatus


PHARMACOLOGY_QUERY_TERMS = {
    "반감기",
    "half-life",
    "half life",
    "대사",
    "배출",
    "얼마나 지나",
    "얼마나지나",
    "며칠",
    "몇 시간",
    "몇시간",
}


def should_run_pharmacology_info(query: str) -> bool:
    normalized_query = normalize_text(query)
    return any(normalize_text(term) in normalized_query for term in PHARMACOLOGY_QUERY_TERMS)


def search_pharmacology_info(query: str) -> PharmacologyInfoResult:
    normalized_query = normalize_text(query)
    candidate_matches: list[tuple[int, Mapping[str, Any], list[str]]] = []

    for record in PHARMACOLOGY_REFERENCE_RECORDS.values():
        matched_terms = [
            alias
            for alias in record["aliases"]
            if normalize_text(alias) in normalized_query
        ]
        if matched_terms:
            longest_match = max(len(normalize_text(term)) for term in matched_terms)
            candidate_matches.append((longest_match, record, matched_terms))

    if candidate_matches:
        _, record, matched_terms = max(candidate_matches, key=lambda item: item[0])
        return build_found_result(query=query, record=record, matched_terms=matched_terms)

    return PharmacologyInfoResult(
        status=PharmacologyInfoStatus.NOT_FOUND,
        query=query,
        recommended_action=(
            "현재 pharmacology_info에 등록된 성분 근거가 없습니다. 정확한 제품명과 성분명을 확인한 뒤 "
            "KADA 약물검색, 약사 또는 팀 닥터에게 확인하세요."
        ),
        safety_notes=[
            "반감기 정보가 없다는 뜻이 복용 가능하다는 뜻은 아닙니다.",
            "도핑 판단은 제품명, 성분명, 경기기간, 용량, 투여 경로, 종목 기준을 함께 확인해야 합니다.",
        ],
    )


def build_found_result(
    query: str,
    record: Mapping[str, Any],
    matched_terms: list[str],
) -> PharmacologyInfoResult:
    return PharmacologyInfoResult(
        status=PharmacologyInfoStatus.FOUND,
        query=query,
        substance_name=record["substance_name"],
        matched_terms=matched_terms,
        half_life=record["half_life"],
        recommended_action=record["recommended_action"],
        safety_notes=list(record["safety_notes"]),
        sources=list(record["sources"]),
    )


def normalize_text(text: str) -> str:
    return text.strip().casefold().replace(" ", "")
