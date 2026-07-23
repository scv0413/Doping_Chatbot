from pydantic import BaseModel, Field


class RetrievalMetadata(BaseModel):
    source_id: str = "unknown"
    title: str | None = None
    page: int | None = None
    section: str | None = None
    authority: str | None = None
    source_type: str | None = None
    chunk_id: str | None = None


class RetrievalMatch(BaseModel):
    rank: int = Field(ge=1)
    chunk_id: str
    distance: float
    metadata: RetrievalMetadata
    text: str = Field(min_length=1)

    @property
    def source_id(self) -> str:
        return self.metadata.source_id

    @property
    def title(self) -> str:
        return self.metadata.title or self.metadata.source_id
