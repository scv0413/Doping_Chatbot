from app.chat.drug_search.schemas import (
    CompetitionPeriod,
    DrugCandidate,
    DrugRiskStatus,
    DrugSearchInput,
    DrugSearchResult,
    DrugSearchSource,
    MatchType,
    build_needs_verification_result,
)


MOCK_SOURCE = DrugSearchSource(
    title="Mock drug search dataset for local development",
    retrieved_at="local_mock",
)

MOCK_CANDIDATES: tuple[DrugCandidate, ...] = (
    DrugCandidate(
        name="타이레놀정 500mg",
        match_type=MatchType.PRODUCT,
        ingredient_names=["아세트아미노펜"],
        manufacturer="mock",
        source_name=MOCK_SOURCE.title,
    ),
    DrugCandidate(
        name="타이레놀 8시간 이알서방정",
        match_type=MatchType.PRODUCT,
        ingredient_names=["아세트아미노펜"],
        manufacturer="mock",
        source_name=MOCK_SOURCE.title,
    ),
    DrugCandidate(
        name="어린이 타이레놀 현탁액",
        match_type=MatchType.PRODUCT,
        ingredient_names=["아세트아미노펜"],
        manufacturer="mock",
        source_name=MOCK_SOURCE.title,
    ),
    DrugCandidate(
        name="슈도에페드린",
        match_type=MatchType.INGREDIENT,
        ingredient_names=["슈도에페드린"],
        source_name=MOCK_SOURCE.title,
    ),
)

LOW_RISK_INGREDIENTS = {"아세트아미노펜", "acetaminophen", "paracetamol"}
CAUTION_INGREDIENTS = {"슈도에페드린", "pseudoephedrine"}


def normalize_search_text(text: str | None) -> str:
    return (text or "").strip().casefold()


def search_mock_drugs(search_input: DrugSearchInput) -> DrugSearchResult:
    query_text = " ".join(
        value
        for value in [
            search_input.query,
            search_input.product_name,
            search_input.ingredient_name,
        ]
        if value
    )
    normalized_query = normalize_search_text(query_text)

    matched_candidates = [
        candidate
        for candidate in MOCK_CANDIDATES
        if _candidate_matches(candidate=candidate, normalized_query=normalized_query)
    ]

    if not matched_candidates:
        return build_needs_verification_result(
            search_input=search_input,
            recommended_action="제품명 또는 성분명을 다시 확인한 뒤 KADA 약물검색 결과와 대조하세요.",
        )

    matched_ingredients = sorted(
        {
            ingredient
            for candidate in matched_candidates
            for ingredient in candidate.ingredient_names
        }
    )
    status = determine_mock_status(
        ingredients=matched_ingredients,
        competition_period=search_input.competition_period,
    )

    return DrugSearchResult(
        status=status,
        input=search_input,
        matched_candidates=matched_candidates,
        matched_substances=matched_ingredients,
        requires_product_selection=len(matched_candidates) > 1,
        requires_route_confirmation=status is DrugRiskStatus.CAUTION,
        requires_dose_confirmation=status is DrugRiskStatus.CAUTION,
        recommended_action=build_recommended_action(
            status=status,
            requires_product_selection=len(matched_candidates) > 1,
        ),
        sources=[MOCK_SOURCE],
        notes=[
            "이 결과는 KADA 자동 조회 전 로컬 개발용 mock 결과입니다.",
            "실제 사용 전 공식 KADA 약물검색 결과와 반드시 대조해야 합니다.",
        ],
    )


def determine_mock_status(
    ingredients: list[str],
    competition_period: CompetitionPeriod,
) -> DrugRiskStatus:
    normalized_ingredients = {normalize_search_text(ingredient) for ingredient in ingredients}

    if normalized_ingredients & {normalize_search_text(item) for item in CAUTION_INGREDIENTS}:
        return DrugRiskStatus.CAUTION

    if normalized_ingredients & {normalize_search_text(item) for item in LOW_RISK_INGREDIENTS}:
        if competition_period is CompetitionPeriod.UNKNOWN:
            return DrugRiskStatus.NEEDS_VERIFICATION
        return DrugRiskStatus.LOW_RISK

    return DrugRiskStatus.NEEDS_VERIFICATION


def build_recommended_action(
    status: DrugRiskStatus,
    requires_product_selection: bool,
) -> str:
    if requires_product_selection:
        return "검색 결과가 여러 개입니다. 정확한 제품을 선택하고 성분표를 확인하세요."

    if status is DrugRiskStatus.LOW_RISK:
        return "현재 정보 기준 위험은 낮아 보이나, 공식 KADA 검색 결과와 성분표를 함께 확인하세요."

    if status is DrugRiskStatus.CAUTION:
        return "경기기간, 용량, 투여 경로에 따라 판단이 달라질 수 있으므로 공식 근거 확인이 필요합니다."

    return "현재 정보만으로 판단하지 말고 제품명, 성분명, 경기기간 여부를 추가 확인하세요."


def _candidate_matches(candidate: DrugCandidate, normalized_query: str) -> bool:
    candidate_terms = [candidate.name, *candidate.ingredient_names]
    normalized_terms = [normalize_search_text(term) for term in candidate_terms]
    query_tokens = [
        token
        for token in normalized_query.replace("/", " ").replace(",", " ").split()
        if len(token) > 1
    ]

    return any(
        term in normalized_query
        or any(token in term or term in token for token in query_tokens)
        for term in normalized_terms
    )
