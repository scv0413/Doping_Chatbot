from pydantic import BaseModel, Field

from app.chat.domain.drug_search.schemas import AdministrationRoute, CompetitionPeriod, DrugSearchResult
from app.chat.domain.pharmacology.schemas import PharmacologyInfoResult


class ToolError(BaseModel):
    stage: str
    message: str
    error_type: str | None = None


class RagSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=3, ge=1, le=10)
    request_id: str | None = None


class RagSearchResult(BaseModel):
    rank: int = Field(ge=1)
    chunk_id: str
    source_id: str
    title: str
    text: str = Field(min_length=1)
    distance: float
    page: int | None = None
    section: str | None = None
    authority: str | None = None
    source_type: str | None = None
    source_language: str | None = None
    official_source_id: str | None = None
    official_source_page: int | None = None


class RagSearchToolOutput(BaseModel):
    tool_name: str = "rag_search_tool"
    query: str
    top_k: int
    results: list[RagSearchResult] = Field(default_factory=list)
    errors: list[ToolError] = Field(default_factory=list)
    request_id: str | None = None

    @property
    def ok(self) -> bool:
        return not self.errors


class DrugSearchToolRequest(BaseModel):
    query: str = Field(min_length=1)
    product_name: str | None = None
    ingredient_name: str | None = None
    competition_period: CompetitionPeriod = CompetitionPeriod.UNKNOWN
    route: AdministrationRoute | None = None
    sport: str | None = None
    dose: str | None = None
    request_id: str | None = None


class DrugSearchToolOutput(BaseModel):
    tool_name: str = "drug_search_tool"
    query: str
    result: DrugSearchResult | None = None
    errors: list[ToolError] = Field(default_factory=list)
    request_id: str | None = None

    @property
    def ok(self) -> bool:
        return not self.errors


class PharmacologyInfoToolRequest(BaseModel):
    query: str = Field(min_length=1)
    request_id: str | None = None


class PharmacologyInfoToolOutput(BaseModel):
    tool_name: str = "pharmacology_info_tool"
    query: str
    result: PharmacologyInfoResult | None = None
    errors: list[ToolError] = Field(default_factory=list)
    request_id: str | None = None

    @property
    def ok(self) -> bool:
        return not self.errors
