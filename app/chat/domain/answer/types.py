from collections.abc import Callable
from typing import Literal, TypedDict


class ChatMessage(TypedDict):
    role: Literal["system", "user", "assistant"]
    content: str


AnswerLLM = Callable[[list[ChatMessage]], str]
