from enum import StrEnum

from pydantic import BaseModel, Field


class PharmacologyInfoStatus(StrEnum):
    FOUND = "found"
    NOT_FOUND = "not_found"


class PharmacologySource(BaseModel):
    title: str
    url: str | None = None
    retrieved_at: str | None = None
    note: str | None = None


class HalfLifeInfo(BaseModel):
    typical_range: str | None = None
    wider_range: str | None = None
    unit: str = "hours"
    factors: list[str] = Field(default_factory=list)
    interpretation_notes: list[str] = Field(default_factory=list)


class PharmacologyInfoResult(BaseModel):
    status: PharmacologyInfoStatus
    query: str
    substance_name: str | None = None
    matched_terms: list[str] = Field(default_factory=list)
    half_life: HalfLifeInfo | None = None
    recommended_action: str
    safety_notes: list[str] = Field(default_factory=list)
    sources: list[PharmacologySource] = Field(default_factory=list)
