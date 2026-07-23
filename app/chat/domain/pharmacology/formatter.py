from app.chat.domain.pharmacology.schemas import PharmacologyInfoResult, PharmacologyInfoStatus


def format_pharmacology_result(result: PharmacologyInfoResult) -> list[str]:
    if result.status is PharmacologyInfoStatus.NOT_FOUND:
        return [
            "- 현재 등록된 약리 정보 근거를 찾지 못했습니다.",
            f"- 권장 행동: {result.recommended_action}",
            *[f"- 주의: {note}" for note in result.safety_notes],
        ]

    lines = [f"- 성분: {result.substance_name}"]

    if result.half_life:
        if result.half_life.typical_range:
            lines.append(f"- 일반적 반감기 참고: {result.half_life.typical_range}")
        if result.half_life.wider_range:
            lines.append(f"- 변동 가능 범위: {result.half_life.wider_range}")
        if result.half_life.factors:
            lines.append(f"- 달라지는 요인: {', '.join(result.half_life.factors)}")
        lines.extend(f"- 해석 주의: {note}" for note in result.half_life.interpretation_notes)

    lines.append(f"- 권장 행동: {result.recommended_action}")
    lines.extend(f"- 주의: {note}" for note in result.safety_notes)
    return lines


def format_pharmacology_sources(result: PharmacologyInfoResult) -> list[str]:
    if not result.sources:
        return ["- 등록된 약리 정보 출처 없음"]

    return [
        f"- {source.title}: {source.url or 'URL 없음'}"
        for source in result.sources
    ]
