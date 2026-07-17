from app.chat.drug_search.formatter import STATUS_LABELS
from app.chat.drug_search.schemas import DrugRiskStatus, DrugSearchResult
from app.chat.retrieval.schemas import RetrievalMatch
from app.chat.router.intent_router import ChatRoute, RouteDecision


def format_answer(
    query: str,
    decision: RouteDecision,
    drug_result: DrugSearchResult | None = None,
    retrieval_matches: list[RetrievalMatch] | None = None,
    citation_limit: int = 3,
) -> str:
    retrieval_matches = retrieval_matches or []
    sections = [
        "## 답변 요약",
        *format_summary(decision=decision, drug_result=drug_result, has_retrieval=bool(retrieval_matches)),
        "",
        "## 확인 결과",
        *format_findings(drug_result=drug_result, retrieval_matches=retrieval_matches),
        "",
        "## 추가 확인",
        *format_follow_up_checks(drug_result=drug_result),
        "",
        "## 근거",
        *format_citations(retrieval_matches=retrieval_matches, limit=citation_limit),
        "",
        "## 주의",
        *format_safety_notes(decision=decision, drug_result=drug_result),
    ]

    return "\n".join(sections).strip()


def format_summary(
    decision: RouteDecision,
    drug_result: DrugSearchResult | None,
    has_retrieval: bool,
) -> list[str]:
    if decision.route is ChatRoute.DRUG_SEARCH and drug_result:
        return [f"- KADA 약물검색 기준 현재 상태는 **{STATUS_LABELS[drug_result.status]}**입니다."]

    if decision.route is ChatRoute.DRUG_SEARCH_WITH_RAG and drug_result:
        retrieval_text = "문서 근거도 함께 확인했습니다" if has_retrieval else "문서 근거는 아직 확인되지 않았습니다"
        return [
            f"- KADA 약물검색 기준 현재 상태는 **{STATUS_LABELS[drug_result.status]}**입니다.",
            f"- 이 질문은 약물 조회와 규정 근거가 모두 필요한 질문이므로 {retrieval_text}.",
        ]

    return ["- 공식 문서와 manual source를 기준으로 확인해야 하는 질문입니다."]


def format_findings(
    drug_result: DrugSearchResult | None,
    retrieval_matches: list[RetrievalMatch],
) -> list[str]:
    lines: list[str] = []

    if drug_result:
        lines.extend(format_drug_findings(drug_result))

    if retrieval_matches:
        lines.append(f"- 문서 근거 후보 {len(retrieval_matches)}개를 검색했습니다.")
        top_match = retrieval_matches[0]
        lines.append(f"- 가장 가까운 근거는 `{top_match.source_id}`의 `{top_match.chunk_id}`입니다.")
    elif not drug_result:
        lines.append("- 검색된 문서 근거가 없습니다.")

    return lines


def format_drug_findings(drug_result: DrugSearchResult) -> list[str]:
    lines = [f"- 위험 상태: {STATUS_LABELS[drug_result.status]}"]

    if drug_result.matched_substances:
        lines.append(f"- 확인된 성분: {', '.join(drug_result.matched_substances[:5])}")
    else:
        lines.append("- 확인된 성분: 없음")

    if drug_result.prohibited_categories:
        lines.append(f"- 관련 금지 분류 후보: {', '.join(drug_result.prohibited_categories)}")

    if drug_result.requires_product_selection:
        lines.append("- 제품 후보가 여러 개이므로 정확한 제품 선택이 필요합니다.")

    return lines


def format_follow_up_checks(drug_result: DrugSearchResult | None) -> list[str]:
    if not drug_result:
        return ["- 질문과 관련된 공식 문서 근거를 확인하고, 불명확하면 KADA 또는 담당자에게 문의해야 합니다."]

    checks: list[str] = []

    if drug_result.requires_product_selection:
        checks.append("정확한 제품명과 성분표를 확인해야 합니다.")
    if drug_result.requires_route_confirmation:
        checks.append("투여 경로를 확인해야 합니다.")
    if drug_result.requires_sport_confirmation:
        checks.append("종목별 금지 여부를 확인해야 합니다.")
    if drug_result.requires_dose_confirmation:
        checks.append("용량 또는 농도 기준을 확인해야 합니다.")
    if not drug_result.matched_candidates and not drug_result.matched_substances:
        checks.append("조회 결과가 없으므로 제품명 또는 성분명을 다시 확인해야 합니다.")

    if not checks:
        checks.append("현재 입력 기준 추가 확인 플래그는 없습니다.")

    return [f"- {check}" for check in checks]


def format_citations(retrieval_matches: list[RetrievalMatch], limit: int) -> list[str]:
    if not retrieval_matches:
        return ["- 검색된 RAG 문서 근거 없음"]

    citations: list[str] = []
    for match in retrieval_matches[:limit]:
        page = match.metadata.page
        page_text = f", p.{page}" if page is not None else ""
        preview = match.text[:180].replace("\n", " ")
        citations.append(f"- {match.title}{page_text} (`{match.chunk_id}`): {preview}")

    return citations


def format_safety_notes(
    decision: RouteDecision,
    drug_result: DrugSearchResult | None,
) -> list[str]:
    notes = ["이 답변은 도핑 관련 의사결정을 돕기 위한 보조 정보이며 공식 판정을 대체하지 않습니다."]

    if decision.route in {ChatRoute.DRUG_SEARCH, ChatRoute.DRUG_SEARCH_WITH_RAG}:
        notes.append("경기기간 중 약물 사용은 복용 전 팀 닥터, 약사, KADA 또는 도핑 담당자에게 확인하는 것이 안전합니다.")
    else:
        notes.append("현장 상황에서는 즉시 거부보다 확인, 기록, 동석 요청, 공식 절차 확인을 우선해야 합니다.")

    if drug_result:
        notes.extend(drug_result.notes)

    if drug_result and drug_result.status is DrugRiskStatus.LOW_RISK:
        notes.append("낮은 위험은 사용 가능을 보장하는 표현이 아닙니다.")

    return [f"- {note}" for note in dict.fromkeys(notes)]
