from collections.abc import Mapping
from typing import Any

from app.chat.domain.pharmacology.knowledge_base import PHARMACOLOGY_REFERENCE_RECORDS
from app.chat.domain.pharmacology.schemas import (
    PharmacologyIngredientResult,
    PharmacologyInfoResult,
    PharmacologyInfoStatus,
)


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
        candidate_matches = remove_embedded_alias_matches(candidate_matches)
        ordered_matches = sorted(candidate_matches, key=lambda item: item[0], reverse=True)
        ingredient_results = [
            build_ingredient_result(record=record, matched_terms=matched_terms)
            for _, record, matched_terms in ordered_matches
        ]
        return build_found_result(
            query=query,
            ingredient_results=ingredient_results,
        )

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


def remove_embedded_alias_matches(
    candidate_matches: list[tuple[int, Mapping[str, Any], list[str]]],
) -> list[tuple[int, Mapping[str, Any], list[str]]]:
    longest_aliases = [
        max((normalize_text(alias) for alias in matched_terms), key=len)
        for _, _, matched_terms in candidate_matches
    ]
    filtered: list[tuple[int, Mapping[str, Any], list[str]]] = []
    for candidate, alias in zip(candidate_matches, longest_aliases, strict=True):
        if any(alias != other and alias in other for other in longest_aliases):
            continue
        filtered.append(candidate)
    return filtered


def build_ingredient_result(
    record: Mapping[str, Any],
    matched_terms: list[str],
) -> PharmacologyIngredientResult:
    return PharmacologyIngredientResult(
        substance_name=record["substance_name"],
        matched_terms=matched_terms,
        half_life=record["half_life"],
        sources=list(record["sources"]),
    )


def build_found_result(
    query: str,
    ingredient_results: list[PharmacologyIngredientResult],
) -> PharmacologyInfoResult:
    primary = ingredient_results[0]
    sources = dedupe_sources(
        source
        for ingredient_result in ingredient_results
        for source in ingredient_result.sources
    )
    return PharmacologyInfoResult(
        status=PharmacologyInfoStatus.FOUND,
        query=query,
        substance_name=primary.substance_name,
        matched_terms=primary.matched_terms,
        half_life=primary.half_life,
        recommended_action=(
            "제품의 각 성분 반감기는 서로 다릅니다. 제품명, 1회 복용량, 총 복용량, "
            "마지막 복용 시각, 경기 시작 시각을 정리한 뒤 팀 닥터, 약사, KADA 또는 도핑 담당자에게 확인하세요."
        ),
        safety_notes=[
            "이 정보는 선수와 지도자의 응급 판단을 돕는 참고자료이며 복용 허가나 도핑 안전 판정이 아닙니다.",
            "경기기간 중 복용 여부는 KADA 약물검색 결과와 WADA 금지목록 기준을 함께 확인해야 합니다.",
            "반감기만으로 도핑검사 검출 가능 시간이나 경기기간 중 사용 가능 여부를 확정할 수 없습니다.",
        ],
        sources=sources,
        ingredient_results=ingredient_results,
    )


def dedupe_sources(sources) -> list:
    unique_sources = []
    seen: set[tuple[str, str | None]] = set()
    for source in sources:
        key = (source.title, source.url)
        if key not in seen:
            seen.add(key)
            unique_sources.append(source)
    return unique_sources


def normalize_text(text: str) -> str:
    return text.strip().casefold().replace(" ", "")
