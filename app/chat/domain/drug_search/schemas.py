from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class CompetitionPeriod(StrEnum):
    IN_COMPETITION = "in_competition"
    OUT_OF_COMPETITION = "out_of_competition"
    UNKNOWN = "unknown"


class AdministrationRoute(StrEnum):
    ORAL = "oral"
    INJECTION = "injection"
    INHALATION = "inhalation"
    NASAL = "nasal"
    TOPICAL = "topical"
    OPHTHALMIC = "ophthalmic"
    OTIC = "otic"
    RECTAL = "rectal"
    UNKNOWN = "unknown"


class DrugRiskStatus(StrEnum):
    LOW_RISK = "low_risk"
    CAUTION = "caution"
    PROHIBITED_POSSIBLE = "prohibited_possible"
    NEEDS_VERIFICATION = "needs_verification"


class MatchType(StrEnum):
    PRODUCT = "product"
    INGREDIENT = "ingredient"
    SUBSTANCE_CLASS = "substance_class"


class DrugSearchInput(BaseModel):
    query: str = Field(min_length=1)
    product_name: str | None = None
    ingredient_name: str | None = None
    competition_period: CompetitionPeriod = CompetitionPeriod.UNKNOWN
    route: AdministrationRoute | None = None
    sport: str | None = None
    dose: str | None = None

    @model_validator(mode="after")
    def require_searchable_text(self) -> "DrugSearchInput":
        if self.product_name or self.ingredient_name or self.query.strip():
            return self
        msg = "query, product_name, or ingredient_name is required"
        raise ValueError(msg)


class DrugCandidate(BaseModel):
    name: str
    match_type: MatchType
    ingredient_names: list[str] = Field(default_factory=list)
    manufacturer: str | None = None
    source_name: str | None = None
    source_url: str | None = None
    retrieved_at: str | None = None


class DrugSearchSource(BaseModel):
    title: str
    url: str | None = None
    retrieved_at: str | None = None


class DrugSearchResult(BaseModel):
    status: DrugRiskStatus
    input: DrugSearchInput
    matched_candidates: list[DrugCandidate] = Field(default_factory=list)
    matched_substances: list[str] = Field(default_factory=list)
    prohibited_categories: list[str] = Field(default_factory=list)
    requires_product_selection: bool = False
    requires_route_confirmation: bool = False
    requires_sport_confirmation: bool = False
    requires_dose_confirmation: bool = False
    recommended_action: str
    sources: list[DrugSearchSource] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


def build_needs_verification_result(
    search_input: DrugSearchInput,
    recommended_action: str = "제품명, 성분명, 경기기간 여부를 확인한 뒤 공식 검색 결과와 대조하세요.",
) -> DrugSearchResult:
    return DrugSearchResult(
        status=DrugRiskStatus.NEEDS_VERIFICATION,
        input=search_input,
        recommended_action=recommended_action,
        notes=[
            "현재 정보만으로 약물 사용 가능 여부를 단정하지 않습니다.",
            "투여 경로, 종목, 용량에 따라 판단이 달라질 수 있습니다.",
        ],
    )
