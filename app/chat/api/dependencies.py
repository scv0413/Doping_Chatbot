from collections.abc import Callable

from app.chat.runtime import ChatRequest, ChatResponse, run_chat

ChatService = Callable[[ChatRequest], ChatResponse]


def get_chat_service() -> ChatService:
    return run_chat
