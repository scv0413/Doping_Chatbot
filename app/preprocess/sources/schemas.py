from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field

from app.preprocess.ocr.quality import PageQualityStatus


class SourceType(StrEnum):
    PDF = "pdf"
    WEB = "web"
    DRUG_SEARCH = "drug_search"
    MANUAL = "manual"


class Language(StrEnum):
    KO = "ko"
    EN = "en"
    MIXED = "mixed"


class Authority(StrEnum):
    KADA = "KADA"
    WADA = "WADA"
    KPIC = "KPIC"
    MANUAL = "manual"


class DocumentType(StrEnum):
    RULES = "rules"
    CODE = "code"
    PROHIBITED_LIST = "prohibited_list"
    TESTING_STANDARD = "testing_standard"
    TUE_STANDARD = "tue_standard"
    TUE_GUIDELINE = "tue_guideline"
    RESULTS_MANAGEMENT = "results_management"
    EDUCATION_STANDARD = "education_standard"
    LABORATORY_STANDARD = "laboratory_standard"
    COMPLIANCE_STANDARD = "compliance_standard"
    OTHER = "other"


class ProcessingStatus(StrEnum):
    NEEDS_REVIEW = "needs_review"
    READY = "ready"
    EXCLUDED = "excluded"


class LayoutType(StrEnum):
    STANDARD = "standard"
    MIXED_LANGUAGE = "mixed_language"
    TABLE_HEAVY = "table_heavy"
    SCANNED = "scanned"
    UNKNOWN = "unknown"


class TocEntry(BaseModel):
    title: str
    page: int


class DocumentMetadata(BaseModel):
    source_id: str
    source_type: SourceType
    title: str
    authority: Authority
    document_type: DocumentType = DocumentType.OTHER
    layout_type: LayoutType = LayoutType.UNKNOWN
    processing_status: ProcessingStatus = ProcessingStatus.NEEDS_REVIEW

    file_name: str | None = None
    file_path: Path | None = None
    url: str | None = None

    page: int | None = None
    section: str | None = None
    language: Language = Language.KO
    extraction_method: str = "text_layer"
    quality_status: PageQualityStatus = PageQualityStatus.ACCEPTED
    quality_reason: str | None = None
    ocr_language: str | None = None
    toc_pages: list[int] = Field(default_factory=list)
    toc_entries: list[TocEntry] = Field(default_factory=list)

    effective_date: str | None = None
    version: str | None = None
    retrieved_at: str | None = None


class DocumentChunk(BaseModel):
    text: str = Field(min_length=1)
    metadata: DocumentMetadata


class Citation(BaseModel):
    title: str
    authority: Authority
    source_type: SourceType

    page: int | None = None
    section: str | None = None
    url: str | None = None
    retrieved_at: str | None = None


class RetrievalResult(BaseModel):
    chunk: DocumentChunk
    score: float | None = None
