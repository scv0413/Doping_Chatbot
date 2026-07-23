from app.chat.domain.drug_search.formatter import STATUS_LABELS
from app.chat.domain.policy.answer_policy import (
    DRUG_USE_SAFETY_NOTE,
    FIELD_RESPONSE_SAFETY_NOTE,
    LOW_RISK_DOES_NOT_GUARANTEE_USE_NOTE,
    OFFICIAL_DECISION_DISCLAIMER,
)
from app.chat.domain.drug_search.schemas import DrugRiskStatus, DrugSearchResult
from app.chat.domain.pharmacology.formatter import (
    format_pharmacology_result,
    format_pharmacology_sources,
)
from app.chat.domain.pharmacology.schemas import PharmacologyInfoResult
from app.chat.domain.retrieval.schemas import RetrievalMatch
from app.chat.orchestration.router.intent_router import ChatRoute, RouteDecision


EVIDENCE_PREVIEW_CHARS = 700


def format_answer(
    query: str,
    decision: RouteDecision,
    drug_result: DrugSearchResult | None = None,
    pharmacology_result: PharmacologyInfoResult | None = None,
    retrieval_matches: list[RetrievalMatch] | None = None,
    citation_limit: int = 3,
) -> str:
    retrieval_matches = retrieval_matches or []

    if pharmacology_result:
        return format_pharmacology_answer(
            query=query,
            decision=decision,
            drug_result=drug_result,
            pharmacology_result=pharmacology_result,
            retrieval_matches=retrieval_matches,
            citation_limit=citation_limit,
        )

    sections = [
        "## 답변 요약",
        *format_summary(
            decision=decision,
            drug_result=drug_result,
            pharmacology_result=pharmacology_result,
            has_retrieval=bool(retrieval_matches),
        ),
        "",
        "## 확인 결과와 근거 핵심",
        *format_findings(
            drug_result=drug_result,
            pharmacology_result=pharmacology_result,
            retrieval_matches=retrieval_matches,
        ),
        *format_source_language_notice(retrieval_matches),
        "",
        "## 추가 확인",
        *format_follow_up_checks(drug_result=drug_result, pharmacology_result=pharmacology_result),
        "",
        "## 행동 지침",
        *format_action_guidance(
            query=query,
            drug_result=drug_result,
            pharmacology_result=pharmacology_result,
            retrieval_matches=retrieval_matches,
        ),
        "",
        "## 주의",
        *format_safety_notes(
            decision=decision,
            drug_result=drug_result,
            pharmacology_result=pharmacology_result,
        ),
    ]

    return "\n".join(sections).strip()


def format_pharmacology_answer(
    query: str,
    decision: RouteDecision,
    drug_result: DrugSearchResult | None,
    pharmacology_result: PharmacologyInfoResult,
    retrieval_matches: list[RetrievalMatch],
    citation_limit: int,
) -> str:
    sections = [
        "## 답변 요약",
        *format_summary(
            decision=decision,
            drug_result=drug_result,
            pharmacology_result=pharmacology_result,
            has_retrieval=bool(retrieval_matches),
        ),
        "- 반감기는 참고용이며 도핑검사 검출 가능 시간이나 출전 가능 여부를 확정하지 않습니다.",
        "",
        "## 반감기 참고",
        *format_pharmacology_result(pharmacology_result),
        "",
        "## 지금 확인해야 할 정보",
        *format_follow_up_checks(drug_result=drug_result, pharmacology_result=pharmacology_result),
        "- 추가로 알려주면 더 정확히 도와줄 정보: 제품명, 성분명, 1회 복용량, 총 복용량, 마지막 복용 시각, 경기 시작 시각, 경기기간 여부",
        "",
        "## 도핑 규정상 주의",
        *format_drug_or_missing_findings(drug_result),
        *format_action_guidance(
            query=query,
            drug_result=drug_result,
            pharmacology_result=pharmacology_result,
            retrieval_matches=retrieval_matches,
        ),
        "",
        "## 근거 핵심",
        *format_evidence_highlights(retrieval_matches=retrieval_matches, limit=citation_limit),
        "",
        "## 주의",
        *format_safety_notes(
            decision=decision,
            drug_result=drug_result,
            pharmacology_result=pharmacology_result,
        ),
    ]
    return "\n".join(sections).strip()


def format_summary(
    decision: RouteDecision,
    drug_result: DrugSearchResult | None,
    pharmacology_result: PharmacologyInfoResult | None,
    has_retrieval: bool,
) -> list[str]:
    if pharmacology_result and drug_result:
        return [
            f"- KADA 약물검색 기준 현재 상태는 **{STATUS_LABELS[drug_result.status]}**입니다.",
            "- 반감기 정보는 참고용으로 함께 확인했으며, 도핑 허용 여부를 확정하지 않습니다.",
        ]

    if pharmacology_result:
        return ["- 약리 정보와 공식 문서 근거를 함께 확인해야 하는 질문입니다."]

    if decision.route is ChatRoute.DRUG_SEARCH and drug_result:
        return [f"- KADA 약물검색 기준 현재 상태는 **{STATUS_LABELS[drug_result.status]}**입니다."]

    if decision.route is ChatRoute.DRUG_SEARCH_WITH_RAG and drug_result:
        retrieval_text = "문서 근거도 함께 확인했습니다" if has_retrieval else "문서 근거는 아직 확인되지 않았습니다"
        return [
            f"- KADA 약물검색 기준 현재 상태는 **{STATUS_LABELS[drug_result.status]}**입니다.",
            f"- 이 질문은 약물 조회와 규정 근거가 모두 필요한 질문이므로 {retrieval_text}.",
        ]

    return ["- 공식 문서 근거를 바탕으로 안내합니다."]


def format_findings(
    drug_result: DrugSearchResult | None,
    pharmacology_result: PharmacologyInfoResult | None,
    retrieval_matches: list[RetrievalMatch],
) -> list[str]:
    lines: list[str] = []

    if drug_result:
        lines.extend(format_drug_findings(drug_result))

    if pharmacology_result:
        lines.append("- 약리 정보 참고 결과를 확인했습니다.")
        lines.extend(format_pharmacology_result(pharmacology_result))

    if retrieval_matches:
        lines.append(f"- 공식 문서에서 관련 근거 {len(retrieval_matches)}개를 확인했습니다.")
    elif not drug_result:
        lines.append("- 검색된 문서 근거가 없습니다.")

    return lines


def format_drug_or_missing_findings(drug_result: DrugSearchResult | None) -> list[str]:
    if drug_result:
        return format_drug_findings(drug_result)
    return ["- KADA 약물검색 결과가 없으므로 제품명 또는 성분명을 다시 확인해야 합니다."]


def format_drug_findings(drug_result: DrugSearchResult) -> list[str]:
    lines = [f"- 위험 상태: {STATUS_LABELS[drug_result.status]}"]

    if drug_result.matched_substances:
        lines.append(f"- 확인된 성분: {', '.join(drug_result.matched_substances[:5])}")
    else:
        lines.append("- 확인된 성분: 없음")

    if drug_result.prohibited_categories:
        lines.append(f"- 관련 금지 분류 후보: {', '.join(drug_result.prohibited_categories)}")

    product_candidates = [
        candidate
        for candidate in drug_result.matched_candidates
        if candidate.match_type.value == "product"
    ]
    if product_candidates:
        lines.append("- KADA 검색 제품 후보:")
        for candidate in product_candidates[:5]:
            ingredients = ", ".join(candidate.ingredient_names) or "성분 정보 없음"
            manufacturer = f" / 제조사: {candidate.manufacturer}" if candidate.manufacturer else ""
            lines.append(f"  - {candidate.name} ({ingredients}){manufacturer}")

    if drug_result.requires_product_selection:
        lines.append("- 제품 후보가 여러 개이므로 정확한 제품 선택이 필요합니다.")

    return lines


def format_action_guidance(
    query: str,
    drug_result: DrugSearchResult | None,
    pharmacology_result: PharmacologyInfoResult | None,
    retrieval_matches: list[RetrievalMatch],
) -> list[str]:
    normalized_query = query.casefold().replace(" ", "")
    chunk_ids = {match.chunk_id for match in retrieval_matches}
    source_ids = {match.source_id for match in retrieval_matches}

    if is_specific_gravity_explanation_question(normalized_query) and has_isti_2023_evidence(retrieval_matches):
        return format_specific_gravity_explanation()

    if is_urine_requirements_question(normalized_query) and has_isti_2023_evidence(retrieval_matches):
        return format_urine_requirements_guidance()

    if is_urine_collection_question(normalized_query) and has_isti_2023_evidence(retrieval_matches):
        return format_urine_collection_guidance(normalized_query)

    if is_bathroom_request_question(normalized_query) and has_isti_2023_evidence(retrieval_matches):
        return [
            "- 대변을 보고 싶으면 즉시 검사관에게 알립니다.",
            "- 도핑관리소를 벗어날 필요가 있으면 검사관 승인과 목적·복귀 시각 확인을 먼저 요청합니다.",
            "- 승인된 이동 중에는 지속 관찰이 적용될 수 있으므로 혼자 현장을 떠나지 않습니다.",
            "- 대변 관련 화장실 이용의 구체적인 동행·관찰 방식은 현장 절차에 따라 검사관에게 확인합니다.",
            "- 소변 시료 제공 전에는 임의로 소변을 보지 말고, 필요한 사정을 먼저 설명합니다.",
        ]

    if "도핑검사" in normalized_query or "도핑관리" in normalized_query:
        return [
            "- 도핑검사는 선수의 소변 또는 혈액 등 시료를 채취하여 금지약물·금지방법 관련 여부를 확인하는 절차입니다.",
            "- 통지를 받으면 검사관의 신분과 절차를 차분히 확인하고, 필요한 경우 통역·팀 관계자 동석을 요청합니다.",
            "- 시료채취 전후의 우려 사항이나 의료상 사유는 검사관에게 설명하고 기록으로 남깁니다.",
            "- 무단 이탈, 연락 두절, 욕설이나 신체적 충돌은 검사 거부 또는 방해로 오해될 수 있으므로 피합니다.",
        ]

    if "s0" in normalized_query or "비승인약물" in normalized_query:
        return [
            "- S0은 비승인 약물 분류이며 상시 금지 항목으로 확인해야 합니다.",
            "- 정부 보건기구에서 사람 치료용으로 승인하지 않은 약리적 물질이 포함됩니다.",
            "- 예시 물질이 전부는 아니므로 공식 금지목록 기준으로 다시 확인해야 합니다.",
        ]

    if "슈도에페드린" in normalized_query or "pseudoephedrine" in normalized_query:
        guidance = [
            "- 슈도에페드린은 경기기간 중 금지 가능성이 있으므로 S6 흥분제 관련 기준을 확인해야 합니다.",
            "- 소변 농도 기준, 용량 또는 농도, 제품명과 성분명을 함께 확인해야 합니다.",
            "- 복용 전 팀 닥터, 약사, KADA 또는 도핑 담당자에게 확인하고 무조건 복용 가능/불가능으로 단정하지 않습니다.",
        ]
        if pharmacology_result:
            guidance.append("- 반감기는 위험도 참고에만 사용하고, 검출 가능 시간이나 출전 가능 여부로 바로 환산하지 않습니다.")
        return guidance

    if "tue" in normalized_query or "치료목적사용면책" in normalized_query:
        return [
            "- TUE는 치료목적사용면책이며 금지약물 또는 금지방법 사용이 의학적으로 필요한 경우 신청합니다.",
            "- KADA 안내 또는 공식 절차에 따라 신청서와 의료자료, 진단자료, 처방 및 검사결과를 준비해야 합니다.",
            "- 대리 신청 또는 선수지원요원의 도움 가능 여부를 확인하고, 팀 닥터, 트레이너 또는 팀 관계자의 도움을 받아 경기 전 충분한 시간 여유를 두고 신청해야 합니다.",
            "- 긴급 치료 상황은 사후 절차가 필요할 수 있지만, 공식 기준과 제출 기한을 확인해야 합니다.",
            "- TUE는 무조건 승인되거나 승인을 보장하는 절차가 아니므로 승인 전 사용은 선수 책임이 될 수 있습니다.",
            "- 허위자료 제출이나 절차 방해는 불이익으로 이어질 수 있으므로 제출 기록과 근거 자료를 정확히 남깁니다.",
        ]

    if "field_response_manual:s3" in " ".join(chunk_ids) or any(
        term in normalized_query for term in ("짐", "현장이탈", "현장을벗어나", "미뤄달", "부상", "치료")
    ):
        if "짐" in normalized_query or "현장을벗어나" in normalized_query or "현장이탈" in normalized_query:
            return [
                "- 짐, 휴대폰, 신분증, 의무용품을 가지러 가야 해도 말 없이 현장 이탈하지 않습니다.",
                "- 먼저 검사관에게 필요한 사유를 알리고 허가를 요청합니다.",
                "- 가능하면 검사관 동행 또는 팀 관계자 동석 상태에서 이동합니다.",
                "- 무단 이탈, 연락 두절, 검사 회피로 보일 행동은 피하고 절차에 협조합니다.",
                "- 이동 필요성과 허가 여부를 검사서 또는 관련 기록에 남깁니다.",
            ]
        return [
            "- 부상이나 응급 치료가 필요해도 검사 거부라고 표현하지 말고 치료 필요성을 설명합니다.",
            "- 의료진 확인을 요청하고, 치료와 검사 절차에 협조하겠다는 의사를 밝힙니다.",
            "- 통역, 팀 관계자 또는 트레이너 동석을 요청합니다.",
            "- 치료 필요성, 지연 사유, 검사관과의 대화 내용을 검사서 또는 관련 기록에 남깁니다.",
            "- 무단 현장 이탈, 연락 두절, 욕설, 신체적 충돌은 거부나 방해로 오해될 수 있으므로 피합니다.",
        ]

    if "field_response_manual:s1" in " ".join(chunk_ids) or ("검사관" in normalized_query and "신분" in normalized_query):
        return [
            "- 즉시 충돌하거나 현장을 이탈하지 말고 검사관 신분증, 소속, 권한을 차분히 확인합니다.",
            "- 신분이 불분명하면 확인될 때까지 절차 설명을 요청합니다.",
            "- 통역, 팀 관계자 또는 동석자를 요청하고 상황을 기록합니다.",
            "- 공식 절차 확인 없이 무단 거부로 보일 행동은 피합니다.",
            "- 검사관의 불합리한 행동은 사후 이의제기 또는 보고 절차로 남깁니다.",
        ]

    if "field_response_manual:s2" in " ".join(chunk_ids) or ("혈액" in normalized_query and ("새벽" in normalized_query or "야간" in normalized_query)):
        return [
            "- 무단 거부하거나 현장을 이탈하지 말고 검사관 신분과 절차를 먼저 확인합니다.",
            "- 잠이 덜 깼거나 상황 인지가 어렵다면 통역, 팀 관계자 또는 동석자를 요청합니다.",
            "- 혈액 시료 채취 사유와 절차 설명을 요청합니다.",
            "- 의사소통이 어렵다면 이를 기록하고 도움을 요청합니다.",
            "- 안전 또는 의료상 우려가 있으면 차분히 설명하고 기록합니다.",
            "- 대체 시료 가능 여부는 단정하지 말고 공식 근거 확인이 필요하다고 안내합니다.",
        ]

    if source_ids:
        return ["- 검색된 근거를 기준으로 답변하되, 불명확한 부분은 공식 기관 확인을 우선합니다."]

    return ["- 검색 근거가 부족하므로 공식 자료 확인 후 판단해야 합니다."]


def format_source_language_notice(retrieval_matches: list[RetrievalMatch]) -> list[str]:
    if any(match.metadata.source_language == "en" for match in retrieval_matches):
        return ["- 아래 설명은 WADA 영문 원문을 기준으로 한국어로 안내한 내용이며, 공식 한국어 번역문이 아닙니다."]
    return []


def format_evidence_highlights(retrieval_matches: list[RetrievalMatch], limit: int) -> list[str]:
    if not retrieval_matches:
        return []

    highlights: list[str] = []
    for match in retrieval_matches[:limit]:
        preview = normalize_preview_text(match.text, max_chars=EVIDENCE_PREVIEW_CHARS)
        highlights.append(f"- {preview}")

    return highlights


def normalize_preview_text(text: str, max_chars: int) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= max_chars:
        return collapsed
    return f"{collapsed[:max_chars].rstrip()}..."


def format_follow_up_checks(
    drug_result: DrugSearchResult | None,
    pharmacology_result: PharmacologyInfoResult | None,
) -> list[str]:
    if not drug_result and not pharmacology_result:
        return ["- 질문과 관련된 공식 문서 근거를 확인하고, 불명확하면 KADA 또는 담당자에게 문의해야 합니다."]

    checks: list[str] = []

    if pharmacology_result:
        checks.append("복용한 제품명, 성분명, 복용량, 마지막 복용 시각, 경기 시작 시각을 함께 정리해야 합니다.")

    if drug_result:
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


def format_citations(
    retrieval_matches: list[RetrievalMatch],
    pharmacology_result: PharmacologyInfoResult | None,
    limit: int,
) -> list[str]:
    citations: list[str] = []
    official_citation_keys: set[tuple[str, int | None]] = set()

    if pharmacology_result:
        citations.extend(format_pharmacology_sources(pharmacology_result))

    if not retrieval_matches:
        if citations:
            citations.append("- 검색된 RAG 문서 근거 없음")
            return citations
        return ["- 검색된 RAG 문서 근거 없음"]

    for match in retrieval_matches[:limit]:
        page = match.metadata.page
        page_text = f", p.{page}" if page is not None else ""
        preview = normalize_preview_text(match.text, max_chars=180)
        citations.append(f"- {match.title}{page_text} (`{match.chunk_id}`): {preview}")

        official_source_id = match.metadata.official_source_id
        official_source_page = match.metadata.official_source_page
        official_citation_key = (official_source_id, official_source_page)
        if official_source_id and official_citation_key not in official_citation_keys:
            official_citation_keys.add(official_citation_key)
            official_page_text = f", p.{official_source_page}" if official_source_page is not None else ""
            citations.append(f"  - 원문: `{official_source_id}`{official_page_text}")

    return citations


def format_safety_notes(
    decision: RouteDecision,
    drug_result: DrugSearchResult | None,
    pharmacology_result: PharmacologyInfoResult | None,
) -> list[str]:
    notes = [OFFICIAL_DECISION_DISCLAIMER]

    if decision.route in {ChatRoute.DRUG_SEARCH, ChatRoute.DRUG_SEARCH_WITH_RAG}:
        notes.append(DRUG_USE_SAFETY_NOTE)
    else:
        notes.append(FIELD_RESPONSE_SAFETY_NOTE)

    if drug_result:
        notes.extend(drug_result.notes)

    if pharmacology_result:
        notes.extend(pharmacology_result.safety_notes)

    if drug_result and drug_result.status is DrugRiskStatus.LOW_RISK:
        notes.append(LOW_RISK_DOES_NOT_GUARANTEE_USE_NOTE)

    return [f"- {note}" for note in dict.fromkeys(notes)]


def is_urine_collection_question(normalized_query: str) -> bool:
    return any(term in normalized_query for term in ("소변", "오줌", "urine"))


def is_bathroom_request_question(normalized_query: str) -> bool:
    return any(term in normalized_query for term in ("대변", "화장실", "변이마려"))


def has_isti_2023_evidence(retrieval_matches: list[RetrievalMatch]) -> bool:
    return any(match.source_id == "wada_isti_2023_en" for match in retrieval_matches)


def format_urine_collection_guidance(normalized_query: str) -> list[str]:
    guidance = [
        "- 통지 후 소변을 이미 봤다면 즉시 검사관에게 알리고, 그 뒤 절차는 검사관 안내에 따릅니다.",
        "- 소변이 바로 나오지 않거나 양이 부족해도 혼자 현장을 떠나지 말고, 검사관의 지속 관찰 아래 다음 시료 절차를 기다립니다.",
        "- 첫 시료의 양이 부족하면 부분 시료를 봉인한 뒤 추가 시료를 받아 합쳐 필요한 양을 충족하는 절차가 적용될 수 있습니다.",
        "- 임의로 물을 계속 마시지 말고 검사관 안내에 따라 필요한 만큼만 섭취합니다. 과도한 수분 섭취는 적정 농도의 시료 제공을 지연시킬 수 있습니다.",
        "- 이미 낸 시료의 농도가 기준에 맞지 않아 추가 시료가 필요한 경우에는 추가 수분 섭취를 하지 말라는 안내를 받을 수 있습니다.",
    ]
    if "검사전" in normalized_query:
        guidance.insert(
            1,
            "- 통지 전인지 통지 후인지에 따라 적용 절차가 다르므로, 통지 후였다면 반드시 검사관에게 바로 알립니다.",
        )
    return guidance



def is_urine_requirements_question(normalized_query: str) -> bool:
    has_urine_term = is_urine_collection_question(normalized_query)
    has_requirement_term = any(
        term in normalized_query
        for term in ("ml", "몇", "양", "농도", "비중", "인정", "기준")
    )
    return has_urine_term and has_requirement_term


def format_urine_requirements_guidance() -> list[str]:
    return [
        "- 먼저 기억할 것은 **최소 90 mL의 소변 시료**가 필요하다는 점입니다.",
        "- 선수는 이 숫자를 직접 재거나 외울 필요는 없습니다. 검사관이 시료 용기의 표시와 측정 도구로 확인합니다.",
        "- 쉽게 말하면 소변 양이 적을수록 농도 기준이 더 엄격하고, 양이 충분히 많으면 기준이 조금 완화됩니다.",
        "- 채취 단계에서는 B 용기에 최소 30 mL, A 용기에 최소 60 mL를 나누어 담는 절차가 적용됩니다.",
        "- 굴절계와 시험지는 소변이 지나치게 묽지 않은지 확인하는 도구입니다.",
        "- 현장 비중 측정은 예비 확인이며, 최종 판단은 검사실 측정값과 검사기관 절차에 따릅니다.",
        "- 양이나 비중이 기준에 미치지 않으면 부분 시료 또는 추가 시료 절차가 적용될 수 있으므로 검사관 안내에 따릅니다.",
    ]



def is_specific_gravity_explanation_question(normalized_query: str) -> bool:
    has_specific_gravity_term = any(
        term in normalized_query
        for term in ("굴절계", "비중", "specificgravity")
    )
    has_threshold = any(term in normalized_query for term in ("1.003", "1.005", "1.010"))
    return has_specific_gravity_term and has_threshold


def format_specific_gravity_explanation() -> list[str]:
    return [
        "- 굴절계는 검사관이 소변의 비중을 재는 기기입니다. 비중은 소변이 지나치게 묽지 않은지 확인하는 수치로 이해하면 됩니다.",
        "- **1.003 이상**은 150 mL 이상 소변 시료를 굴절계로 측정했을 때 적용되는 최소 비중 기준입니다.",
        "- 예를 들어 1.003보다 낮으면 소변이 너무 묽다고 판단되어 추가 시료 절차가 필요할 수 있습니다.",
        "- 이 수치는 도핑 음성이나 사용 가능을 뜻하지는 않습니다. 시료의 양과 농도가 분석에 적합한지 확인하는 절차입니다.",
        "- 현장 측정은 예비 확인이며, 최종 판단은 검사실 측정값과 검사기관 절차에 따릅니다.",
    ]
