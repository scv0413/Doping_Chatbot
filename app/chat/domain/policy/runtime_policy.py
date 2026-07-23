from enum import StrEnum
from pydantic import BaseModel, Field

from app.core.config import DEFAULT_GRAPH_RECURSION_LIMIT
from app.chat.orchestration.router.intent_router import ChatRoute, route_question

DEFAULT_TOP_K = 3
MAX_TOP_K = 10


class RuntimeEngine(StrEnum):
    GRAPH = "graph"
    PIPELINE = "pipeline"


class RuntimePolicyDecision(BaseModel):
    top_k: int = Field(default=DEFAULT_TOP_K, ge=1, le=MAX_TOP_K)
    use_llm: bool = False
    engine: RuntimeEngine = RuntimeEngine.GRAPH
    recursion_limit: int = Field(default=DEFAULT_GRAPH_RECURSION_LIMIT, ge=1, le=50)
    reason: str
    matched_rules: list[str] = Field(default_factory=list)


def decide_runtime_policy(
    query: str,
    top_k: int | None = None,
    use_llm: bool | None = None,
    engine: RuntimeEngine | str | None = None,
    recursion_limit: int | None = None,
) -> RuntimePolicyDecision:
    """Resolve runtime options from product policy and explicit overrides.

    Explicit values are respected so experiments and tests can force a mode. If a
    value is omitted, the policy chooses the conservative operational default.
    """

    route_decision = route_question(query)
    normalized_query = normalize_query(query)
    matched_rules: list[str] = []

    resolved_top_k = top_k or DEFAULT_TOP_K
    resolved_engine = normalize_engine(engine) or RuntimeEngine.GRAPH
    resolved_recursion_limit = recursion_limit or DEFAULT_GRAPH_RECURSION_LIMIT

    policy_use_llm = should_use_llm_by_policy(
        normalized_query=normalized_query,
        route=route_decision.route,
        matched_rules=matched_rules,
    )
    resolved_use_llm = policy_use_llm if use_llm is None else use_llm

    if top_k is None:
        matched_rules.append("default_top_k_3")
    if engine is None:
        matched_rules.append("default_graph_engine")
    if recursion_limit is None:
        matched_rules.append("default_recursion_limit")
    if use_llm is not None:
        matched_rules.append("explicit_use_llm_override")
    if top_k is not None:
        matched_rules.append("explicit_top_k_override")
    if engine is not None:
        matched_rules.append("explicit_engine_override")

    return RuntimePolicyDecision(
        top_k=resolved_top_k,
        use_llm=resolved_use_llm,
        engine=resolved_engine,
        recursion_limit=resolved_recursion_limit,
        reason=build_policy_reason(route_decision.route, resolved_use_llm, matched_rules),
        matched_rules=matched_rules,
    )


def should_use_llm_by_policy(
    normalized_query: str,
    route: ChatRoute,
    matched_rules: list[str],
) -> bool:
    if contains_any(normalized_query, HALF_LIFE_TERMS) and contains_any(normalized_query, SPECIFIC_SUBSTANCE_TERMS):
        matched_rules.append("half_life_safety_baseline_formatter")
        return False

    if "도핑검사" in normalized_query or "도핑관리" in normalized_query:
        matched_rules.append("general_doping_control_llm")
        return True

    if route is ChatRoute.DRUG_SEARCH:
        matched_rules.append("simple_drug_search_formatter")
        return False

    if contains_any(normalized_query, COMPLEX_FIELD_TERMS):
        matched_rules.append("complex_field_scenario_llm")
        return True

    if route is ChatRoute.DRUG_SEARCH_WITH_RAG:
        matched_rules.append("drug_with_rag_formatter_baseline")
        return False

    matched_rules.append("default_formatter_baseline")
    return False


def normalize_engine(engine: RuntimeEngine | str | None) -> RuntimeEngine | None:
    if engine is None:
        return None
    if isinstance(engine, RuntimeEngine):
        return engine
    return RuntimeEngine(engine)


def build_policy_reason(route: ChatRoute, use_llm: bool, matched_rules: list[str]) -> str:
    mode = "LLM answer chain" if use_llm else "deterministic formatter"
    return f"route={route.value}에 대해 {mode}를 선택했습니다. rules={', '.join(matched_rules)}"


def normalize_query(query: str) -> str:
    return query.casefold().replace(" ", "")


def contains_any(normalized_query: str, terms: set[str]) -> bool:
    return any(normalize_query(term) in normalized_query for term in terms)


HALF_LIFE_TERMS = {"반감기", "half-life", "halflife", "half life"}

SPECIFIC_SUBSTANCE_TERMS = {
    "슈도에페드린",
    "pseudoephedrine",
    "에페드린",
    "ephedrine",
    "메틸에페드린",
    "메칠에페드린",
    "methylephedrine",
    "카틴",
    "cathine",
    "트라마돌",
    "tramadol",
}

COMPLEX_FIELD_TERMS = {
    "검사관",
    "시료채취",
    "소변",
    "오줌",
    "대변",
    "화장실",
    "굴절계",
    "비중",
    "혈액",
    "새벽",
    "야간",
    "부상",
    "응급",
    "치료",
    "거부",
    "회피",
    "현장이탈",
    "신분",
    "통역",
    "TUE",
    "치료목적사용면책",
    "대리신청",
    "대리 신청",
}
