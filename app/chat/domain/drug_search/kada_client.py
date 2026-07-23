import json
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.chat.domain.drug_search.schemas import (
    CompetitionPeriod,
    DrugCandidate,
    DrugRiskStatus,
    DrugSearchInput,
    DrugSearchResult,
    DrugSearchSource,
    MatchType,
)


KADA_HEALTH_BASE_URL = "https://kada.health.kr"
KADA_SOURCE_TITLE = "KADA 금지약물 검색서비스"
DEFAULT_PAGE_SIZE = 5
REQUEST_TIMEOUT_SECONDS = 15


def search_kada_drugs(
    search_input: DrugSearchInput,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> DrugSearchResult:
    query = search_input.ingredient_name or search_input.product_name or search_input.query
    product_payload = fetch_kada_json(
        endpoint="/result/baseDrug",
        data={
            "pageNo": "0",
            "pageSize": str(page_size),
            "bothName": query,
            "idfy": "N",
        },
    )
    substance_payload = fetch_kada_json(
        endpoint="/result/sunb",
        data={
            "pageNo": "0",
            "pageSize": str(page_size),
            "bothName": query,
            "idfy": "N",
        },
    )

    return parse_kada_search_result(
        search_input=search_input,
        product_payload=product_payload,
        substance_payload=substance_payload,
    )


def fetch_kada_json(
    endpoint: str,
    data: dict[str, str],
    timeout_seconds: int = REQUEST_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    encoded_data = urlencode(data).encode("utf-8")
    request = Request(
        url=f"{KADA_HEALTH_BASE_URL}{endpoint}",
        data=encoded_data,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "doping-chatbot/0.1 local-development",
        },
    )

    with urlopen(request, timeout=timeout_seconds) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return json.loads(response.read().decode(charset))


def parse_kada_search_result(
    search_input: DrugSearchInput,
    product_payload: dict[str, Any],
    substance_payload: dict[str, Any],
    retrieved_at: str | None = None,
) -> DrugSearchResult:
    retrieved_at = retrieved_at or datetime.now(UTC).isoformat()
    product_candidates = parse_product_candidates(product_payload, retrieved_at=retrieved_at)
    substance_candidates = parse_substance_candidates(substance_payload, retrieved_at=retrieved_at)
    matched_substances = extract_matched_substances(substance_payload)
    status = determine_kada_status(
        substance_payload=substance_payload,
        product_candidates=product_candidates,
        competition_period=search_input.competition_period,
    )
    requires_product_selection = should_require_product_selection(
        search_input=search_input,
        product_candidates=product_candidates,
        substance_candidates=substance_candidates,
    )
    has_sport_specific_substance = any(
        is_sport_specific(item)
        for item in substance_payload.get("list", [])
        if isinstance(item, dict)
    )

    return DrugSearchResult(
        status=status,
        input=search_input,
        matched_candidates=[*substance_candidates, *product_candidates],
        matched_substances=matched_substances,
        prohibited_categories=extract_prohibited_categories(substance_payload),
        requires_product_selection=requires_product_selection,
        requires_sport_confirmation=has_sport_specific_substance,
        requires_dose_confirmation=requires_dose_confirmation(substance_payload),
        recommended_action=build_kada_recommended_action(
            status=status,
            has_product_candidates=bool(product_candidates),
            has_substance_candidates=bool(substance_candidates),
            requires_product_selection=requires_product_selection,
            competition_period=search_input.competition_period,
        ),
        sources=[
            DrugSearchSource(
                title=KADA_SOURCE_TITLE,
                url=KADA_HEALTH_BASE_URL,
                retrieved_at=retrieved_at,
            )
        ],
        notes=build_kada_notes(),
    )


def should_require_product_selection(
    search_input: DrugSearchInput,
    product_candidates: list[DrugCandidate],
    substance_candidates: list[DrugCandidate],
) -> bool:
    if len(product_candidates) <= 1:
        return False
    if search_input.product_name:
        return True
    return not substance_candidates


def parse_product_candidates(
    payload: dict[str, Any],
    retrieved_at: str,
) -> list[DrugCandidate]:
    candidates: list[DrugCandidate] = []

    for item in payload.get("list", []):
        if not isinstance(item, dict):
            continue

        name = string_or_none(item.get("drug_name"))
        if not name:
            continue

        candidates.append(
            DrugCandidate(
                name=name,
                match_type=MatchType.PRODUCT,
                ingredient_names=parse_ingredient_names(item.get("list_sunb_name")),
                manufacturer=string_or_none(item.get("firm_name")),
                source_name=KADA_SOURCE_TITLE,
                source_url=KADA_HEALTH_BASE_URL,
                retrieved_at=retrieved_at,
            )
        )

    return candidates


def parse_substance_candidates(
    payload: dict[str, Any],
    retrieved_at: str,
) -> list[DrugCandidate]:
    candidates: list[DrugCandidate] = []

    for item in payload.get("list", []):
        if not isinstance(item, dict):
            continue

        names = [string_or_none(item.get("sunb_name")), string_or_none(item.get("sunb_ename"))]
        display_name = " / ".join(name for name in names if name)
        if not display_name:
            continue

        candidates.append(
            DrugCandidate(
                name=display_name,
                match_type=MatchType.INGREDIENT,
                ingredient_names=[name for name in names if name],
                source_name=KADA_SOURCE_TITLE,
                source_url=KADA_HEALTH_BASE_URL,
                retrieved_at=retrieved_at,
            )
        )

    return candidates


def determine_kada_status(
    substance_payload: dict[str, Any],
    product_candidates: list[DrugCandidate],
    competition_period: CompetitionPeriod,
) -> DrugRiskStatus:
    substance_items = [item for item in substance_payload.get("list", []) if isinstance(item, dict)]

    if not substance_items:
        if product_candidates:
            return DrugRiskStatus.NEEDS_VERIFICATION
        return DrugRiskStatus.NEEDS_VERIFICATION

    statuses = [(normalize_status(item.get("ingame")), normalize_status(item.get("outgame"))) for item in substance_items]

    if any(in_game == "금지" and out_game == "금지" for in_game, out_game in statuses):
        return DrugRiskStatus.PROHIBITED_POSSIBLE

    if competition_period is CompetitionPeriod.IN_COMPETITION:
        if any(in_game == "금지" for in_game, _ in statuses):
            return DrugRiskStatus.PROHIBITED_POSSIBLE
        if any(in_game == "종목확인" for in_game, _ in statuses):
            return DrugRiskStatus.CAUTION

    if competition_period is CompetitionPeriod.OUT_OF_COMPETITION:
        if any(out_game == "금지" for _, out_game in statuses):
            return DrugRiskStatus.PROHIBITED_POSSIBLE
        if any(out_game == "종목확인" for _, out_game in statuses):
            return DrugRiskStatus.CAUTION
        if any(in_game == "금지" and out_game == "허용" for in_game, out_game in statuses):
            return DrugRiskStatus.CAUTION

    if any("종목확인" in status_pair for status_pair in statuses):
        return DrugRiskStatus.CAUTION

    if any("금지" in status_pair for status_pair in statuses):
        return DrugRiskStatus.CAUTION

    if competition_period is CompetitionPeriod.UNKNOWN:
        return DrugRiskStatus.NEEDS_VERIFICATION

    return DrugRiskStatus.LOW_RISK


def build_kada_recommended_action(
    status: DrugRiskStatus,
    has_product_candidates: bool,
    has_substance_candidates: bool,
    requires_product_selection: bool,
    competition_period: CompetitionPeriod,
) -> str:
    if not has_product_candidates and not has_substance_candidates:
        return "조회 결과가 없습니다. 금지가 아님을 의미하지 않으므로 제품명과 성분명을 다시 확인하세요."

    if status is DrugRiskStatus.PROHIBITED_POSSIBLE:
        return "금지 가능성이 확인됩니다. 사용 전 KADA, 팀 닥터, 약사 또는 도핑 담당자에게 확인하세요."

    if status is DrugRiskStatus.CAUTION:
        return "경기기간, 종목, 용량 또는 투여 경로에 따라 판단이 달라질 수 있어 추가 확인이 필요합니다."

    if requires_product_selection:
        return "검색 결과가 여러 개입니다. 정확한 제품을 선택하고 성분표를 확인하세요."

    if competition_period is CompetitionPeriod.UNKNOWN:
        return "경기기간 여부가 불분명합니다. 경기기간 중인지 확인한 뒤 다시 판단하세요."

    return "현재 정보 기준 위험은 낮아 보이나, 제품 성분표와 공식 KADA 검색 결과를 함께 보관하세요."


def build_kada_notes() -> list[str]:
    return [
        "KADA 금지약물 검색서비스는 국내 허가 의약품 정보를 기준으로 제공됩니다.",
        "보충제, 건강기능식품, 한약재, 국외 의약품은 검색 결과의 신뢰성을 보장하기 어렵습니다.",
        "조회 결과가 없다는 것은 금지가 아님을 의미하지 않습니다.",
        "의약품 사용 전 의사 또는 약사와 함께 확인하는 것을 권장합니다.",
    ]


def extract_matched_substances(payload: dict[str, Any]) -> list[str]:
    substances: set[str] = set()

    for item in payload.get("list", []):
        if not isinstance(item, dict):
            continue
        for key in ("sunb_name", "sunb_ename"):
            value = string_or_none(item.get(key))
            if value:
                substances.add(value)

    return sorted(substances)


def extract_prohibited_categories(payload: dict[str, Any]) -> list[str]:
    categories: set[str] = set()

    for item in payload.get("list", []):
        if not isinstance(item, dict):
            continue
        mapid = string_or_none(item.get("mapid"))
        if mapid:
            categories.add(mapid)

    return sorted(categories)


def parse_ingredient_names(raw_value: Any) -> list[str]:
    value = string_or_none(raw_value)
    if not value:
        return []
    return [value]


def requires_dose_confirmation(payload: dict[str, Any]) -> bool:
    return any(
        normalize_status(item.get("ingame")) == "금지"
        and normalize_status(item.get("outgame")) == "허용"
        for item in payload.get("list", [])
        if isinstance(item, dict)
    )


def is_sport_specific(item: dict[str, Any]) -> bool:
    return normalize_status(item.get("ingame")) == "종목확인" or normalize_status(item.get("outgame")) == "종목확인"


def normalize_status(value: Any) -> str | None:
    normalized = string_or_none(value)
    if normalized is None:
        return None
    return normalized.replace(" ", "")


def string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
