from fastapi import APIRouter, Depends

from app.chat.api.dependencies import ChatService, get_chat_service
from app.chat.config import settings
from app.chat.runtime import ChatRequest, ChatResponse

router = APIRouter()


@router.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
    }


@router.post("/api/v1/chat-responses", response_model=ChatResponse, tags=["chat"])
def create_chat_response(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    return chat_service(request)
