from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from app.chat.api.dependencies import ChatService, get_chat_service
from app.chat.api.readiness import ReadinessResponse, build_readiness_response
from app.chat.config import settings
from app.chat.runtime import ChatRequest, ChatResponse, CitationSummary

router = APIRouter()


class PublicChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)


class PublicChatResponse(BaseModel):
    answer: str
    query: str
    citations: list[CitationSummary] = Field(default_factory=list)
    drug_status: str | None = None
    pharmacology_status: str | None = None
    pharmacology_substance: str | None = None
    errors: list[dict] = Field(default_factory=list)

    @classmethod
    def from_chat_response(cls, response: ChatResponse) -> "PublicChatResponse":
        return cls(
            answer=response.answer,
            query=response.query,
            citations=response.citations,
            drug_status=response.drug_status,
            pharmacology_status=response.pharmacology_status,
            pharmacology_substance=response.pharmacology_substance,
            errors=response.errors,
        )


@router.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
    }


@router.get("/ready", response_model=ReadinessResponse, tags=["system"])
def readiness_check() -> ReadinessResponse:
    return build_readiness_response()


@router.post("/api/v1/chat-responses", response_model=PublicChatResponse, tags=["chat"])
def create_chat_response(
    request: PublicChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
) -> PublicChatResponse:
    return PublicChatResponse.from_chat_response(chat_service(ChatRequest(query=request.query)))


@router.post("/api/v1/debug/chat-responses", response_model=ChatResponse, tags=["debug"])
def create_debug_chat_response(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    return chat_service(request)
