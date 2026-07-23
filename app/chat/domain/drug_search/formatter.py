from app.chat.domain.drug_search.schemas import (
    CompetitionPeriod,
    DrugCandidate,
    DrugRiskStatus,
    DrugSearchResult,
)


STATUS_LABELS = {
    DrugRiskStatus.LOW_RISK: "낮은 위험",
    DrugRiskStatus.CAUTION: "주의 필요",
    DrugRiskStatus.PROHIBITED_POSSIBLE: "금지 가능성 있음",
    DrugRiskStatus.NEEDS_VERIFICATION: "확인 필요",
}

COMPETITION_PERIOD_LABELS = {
    CompetitionPeriod.IN_COMPETITION: "경기기간 중",
    CompetitionPeriod.OUT_OF_COMPETITION: "경기기간 외",
    CompetitionPeriod.UNKNOWN: "모름",
}


def format_drug_search_answer(result: DrugSearchResult, candidate_limit: int = 5) -> str:
    sections = [
        "## 현재 입력 정보",
        *format_input_info(result),
        "",
        "## 확인된 핵심 정보",
        *format_core_info(result, candidate_limit=candidate_limit),
        "",
        "## 추가 확인이 필요한 정보",
        *format_required_confirmations(result),
        "",
        "## 권장 행동",
        f"- {result.recommended_action}",
        "",
        "## 근거",
        *format_sources_and_notes(result),
    ]

    return "\n".join(sections).strip()


def format_input_info(result: DrugSearchResult) -> list[str]:
    search_input = result.input
    return [
        f"- 질문: {search_input.query}",
        f"- 제품명: {search_input.product_name or '미입력'}",
        f"- 성분명: {search_input.ingredient_name or '미입력'}",
        f"- 경기기간 여부: {COMPETITION_PERIOD_LABELS[search_input.competition_period]}",
        f"- 투여 경로: {search_input.route or '미입력'}",
        f"- 종목: {search_input.sport or '미입력'}",
        f"- 용량: {search_input.dose or '미입력'}",
    ]


def format_core_info(result: DrugSearchResult, candidate_limit: int) -> list[str]:
    lines = [f"- 위험 상태: {STATUS_LABELS[result.status]}"]

    if result.matched_substances:
        substances = ", ".join(result.matched_substances[:candidate_limit])
        lines.append(f"- 확인된 성분: {substances}")
        if len(result.matched_substances) > candidate_limit:
            lines.append(f"- 추가 성분 후보: {len(result.matched_substances) - candidate_limit}개")
    else:
        lines.append("- 확인된 성분: 없음")

    if result.prohibited_categories:
        lines.append(f"- 관련 금지 분류 후보: {', '.join(result.prohibited_categories)}")

    if result.matched_candidates:
        lines.append("- 검색 후보:")
        lines.extend(
            f"  {idx}. {format_candidate(candidate)}"
            for idx, candidate in enumerate(result.matched_candidates[:candidate_limit], start=1)
        )
        if len(result.matched_candidates) > candidate_limit:
            lines.append(f"  - 그 외 후보 {len(result.matched_candidates) - candidate_limit}개")
    else:
        lines.append("- 검색 후보: 없음")

    return lines


def format_candidate(candidate: DrugCandidate) -> str:
    ingredient_text = ", ".join(candidate.ingredient_names) or "성분 정보 없음"
    manufacturer_text = f" / 제조사: {candidate.manufacturer}" if candidate.manufacturer else ""
    return f"{candidate.name} ({ingredient_text}){manufacturer_text}"


def format_required_confirmations(result: DrugSearchResult) -> list[str]:
    confirmations: list[str] = []

    if result.requires_product_selection:
        confirmations.append("정확한 제품을 선택해야 합니다.")
    if result.requires_route_confirmation:
        confirmations.append("투여 경로를 확인해야 합니다.")
    if result.requires_sport_confirmation:
        confirmations.append("종목별 금지 여부를 확인해야 합니다.")
    if result.requires_dose_confirmation:
        confirmations.append("용량 또는 농도 기준을 확인해야 합니다.")
    if result.input.competition_period is CompetitionPeriod.UNKNOWN:
        confirmations.append("경기기간 중인지 경기기간 외인지 확인해야 합니다.")
    if not result.matched_candidates and not result.matched_substances:
        confirmations.append("정확한 제품명 또는 성분명을 다시 확인해야 합니다.")

    if not confirmations:
        confirmations.append("현재 입력 기준 추가 확인 플래그는 없습니다.")

    return [f"- {confirmation}" for confirmation in confirmations]


def format_sources_and_notes(result: DrugSearchResult) -> list[str]:
    lines: list[str] = []

    if result.sources:
        for source in result.sources:
            source_line = f"- {source.title}"
            if source.url:
                source_line += f": {source.url}"
            if source.retrieved_at:
                source_line += f" (조회: {source.retrieved_at})"
            lines.append(source_line)
    else:
        lines.append("- 출처 정보 없음")

    lines.extend(f"- 주의: {note}" for note in result.notes)
    return lines
