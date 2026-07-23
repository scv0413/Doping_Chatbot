"""Convert a natural-language drug question into safe KADA search fields."""

from collections.abc import Callable
from enum import StrEnum
import re

from pydantic import BaseModel

from app.chat.domain.drug_search.schemas import AdministrationRoute, CompetitionPeriod


class DrugQuestionIntent(StrEnum):
    DRUG_USE_CHECK = "drug_use_check"
    DRUG_INFO = "drug_info"


class ExtractionSource(StrEnum):
    RULE = "rule"
    LLM = "llm"
    NONE = "none"


class DrugQueryExtraction(BaseModel):
    product_name: str | None = None
    ingredient_name: str | None = None
    competition_period: CompetitionPeriod = CompetitionPeriod.UNKNOWN
    route: AdministrationRoute | None = None
    intent: DrugQuestionIntent = DrugQuestionIntent.DRUG_INFO
    source: ExtractionSource = ExtractionSource.NONE


DrugQueryLLM = Callable[[str], DrugQueryExtraction | None]

KNOWN_INGREDIENTS = {
    "아세트아미노펜",
    "acetaminophen",
    "paracetamol",
    "슈도에페드린",
    "pseudoephedrine",
    "테스토스테론",
    "testosterone",
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

KNOWN_PRODUCT_NAMES = {"타이레놀"}
ORAL_TERMS = {"먹어", "먹어도", "복용", "마셔", "마셔도", "경구"}
SPRAY_USE_TERMS = {"뿌려", "뿌려도", "분사", "분사해도", "분무", "분무해도"}
IN_COMPETITION_TERMS = {
    "경기중",
    "경기 중",
    "경기기간중",
    "경기기간 중",
    "시합중",
    "시합 중",
    "대회중",
    "대회 중",
}
GENERIC_PRODUCT_TERMS = {"감기약", "약", "약물", "제품", "이약", "그약"}
NON_MEDICATION_CANDIDATES = {
    *GENERIC_PRODUCT_TERMS,
    "도핑",
    "도핑검사",
    "검사관",
    "시료채취",
    "반감기",
    "tue",
    "규정",
    "금지목록",
    "경기",
    "경기기간",
    "경기기간중",
    "경기기간외",
}
OUT_OF_COMPETITION_TERMS = {"경기기간외", "경기기간 외", "경기 외", "시합 전", "대회 전"}
PRODUCT_BEFORE_USE_PATTERN = re.compile(
    r"(?P<product>[A-Za-z0-9가-힣]+)(?:을|를|은|는|이|가)?\s*"
    r"(?:먹어도|먹어|복용해도|복용|마셔도|마셔|사용해도|사용|뿌려도|뿌려|분사해도|분사|분무해도|분무)"
)
PRODUCT_BEFORE_HALF_LIFE_PATTERN = re.compile(
    r"(?P<product>[A-Za-z0-9가-힣]+)(?:은|는|의|이|가)?\s*반감기"
)


def extract_drug_query(
    query: str,
    llm_extractor: DrugQueryLLM | None = None,
) -> DrugQueryExtraction:
    """Extract searchable terms without allowing an LLM to invent a drug name."""

    rule_extraction = extract_by_rules(query)
    if rule_extraction.product_name or rule_extraction.ingredient_name or llm_extractor is None:
        return rule_extraction

    llm_extraction = llm_extractor(query)
    if llm_extraction is None or not is_supported_by_query(llm_extraction, query):
        return rule_extraction

    return llm_extraction.model_copy(
        update={
            "competition_period": llm_extraction.competition_period
            if llm_extraction.competition_period is not CompetitionPeriod.UNKNOWN
            else rule_extraction.competition_period,
            "route": llm_extraction.route or rule_extraction.route,
            "source": ExtractionSource.LLM,
        }
    )


def extract_by_rules(query: str) -> DrugQueryExtraction:
    normalized = normalize_text(query)
    competition_period = extract_competition_period(normalized)
    route = extract_route(normalized)
    intent = extract_intent(normalized)

    ingredient_name = next(
        (ingredient for ingredient in KNOWN_INGREDIENTS if normalize_text(ingredient) in normalized),
        None,
    )
    if ingredient_name:
        return DrugQueryExtraction(
            ingredient_name=ingredient_name,
            competition_period=competition_period,
            route=route,
            intent=intent,
            source=ExtractionSource.RULE,
        )

    product_name = next(
        (product for product in KNOWN_PRODUCT_NAMES if normalize_text(product) in normalized),
        None,
    ) or extract_product_before_use(query) or extract_product_before_half_life(query) or extract_generic_medication_candidate(query)
    if product_name:
        return DrugQueryExtraction(
            product_name=product_name,
            competition_period=competition_period,
            route=route,
            intent=intent,
            source=ExtractionSource.RULE,
        )

    return DrugQueryExtraction(
        competition_period=competition_period,
        route=route,
        intent=intent,
    )


def is_supported_by_query(extraction: DrugQueryExtraction, query: str) -> bool:
    normalized_query = normalize_text(query)
    candidates = [extraction.product_name, extraction.ingredient_name]
    return any(candidate and normalize_text(candidate) in normalized_query for candidate in candidates)


def extract_product_before_use(query: str) -> str | None:
    match = PRODUCT_BEFORE_USE_PATTERN.search(query)
    if match is None:
        return None

    candidate = match.group("product").strip()
    if len(candidate) < 2 or normalize_text(candidate) in NON_MEDICATION_CANDIDATES:
        return None
    return candidate


def extract_product_before_half_life(query: str) -> str | None:
    match = PRODUCT_BEFORE_HALF_LIFE_PATTERN.search(query)
    if match is None:
        return None

    return validate_generic_medication_candidate(match.group("product").strip())


def extract_generic_medication_candidate(query: str) -> str | None:
    """Keep an unfamiliar, user-provided medicine or herbal term searchable in KADA."""

    stripped = query.strip().rstrip("?.!").strip()
    single_term = re.fullmatch(r"(?P<candidate>[A-Za-z0-9가-힣]+)", stripped)
    if single_term:
        return validate_generic_medication_candidate(single_term.group("candidate"))

    contextual = re.match(
        r"(?P<candidate>[A-Za-z0-9가-힣]+)(?:을|를|은|는|이|가)?\s*"
        r"(?:성분|계열(?:의)?|약(?:물)?|제품|금지|허용|가능|괜찮|돼)",
        stripped,
    )
    if contextual:
        return validate_generic_medication_candidate(contextual.group("candidate"))

    return None


def validate_generic_medication_candidate(candidate: str) -> str | None:
    normalized = normalize_text(candidate)
    if len(candidate) < 2 or normalized in NON_MEDICATION_CANDIDATES:
        return None
    return candidate


def extract_competition_period(normalized_query: str) -> CompetitionPeriod:
    if any(normalize_text(term) in normalized_query for term in IN_COMPETITION_TERMS):
        return CompetitionPeriod.IN_COMPETITION
    if any(normalize_text(term) in normalized_query for term in OUT_OF_COMPETITION_TERMS):
        return CompetitionPeriod.OUT_OF_COMPETITION
    return CompetitionPeriod.UNKNOWN


def extract_route(normalized_query: str) -> AdministrationRoute | None:
    if any(normalize_text(term) in normalized_query for term in ORAL_TERMS):
        return AdministrationRoute.ORAL
    if "비강" in normalized_query or "코스프레이" in normalized_query:
        return AdministrationRoute.NASAL
    if "주사" in normalized_query:
        return AdministrationRoute.INJECTION
    if "흡입" in normalized_query:
        return AdministrationRoute.INHALATION
    return None


def extract_intent(normalized_query: str) -> DrugQuestionIntent:
    if any(normalize_text(term) in normalized_query for term in ORAL_TERMS | SPRAY_USE_TERMS | {"사용해도", "사용"}):
        return DrugQuestionIntent.DRUG_USE_CHECK
    return DrugQuestionIntent.DRUG_INFO


def normalize_text(value: str) -> str:
    return value.strip().casefold().replace(" ", "")
