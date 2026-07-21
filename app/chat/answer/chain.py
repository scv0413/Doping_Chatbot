from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, trim_messages
from langchain_openai import ChatOpenAI

from app.chat.answer.formatter import format_answer
from app.chat.answer.types import AnswerLLM, ChatMessage
from app.chat.config import settings
from app.chat.policy.answer_policy import (
    OFFICIAL_DECISION_DISCLAIMER,
    build_answer_writing_instructions,
    build_system_prompt,
)
from app.chat.drug_search.schemas import DrugSearchResult
from app.chat.retrieval.schemas import RetrievalMatch
from app.chat.router.intent_router import RouteDecision


DEFAULT_MAX_PROMPT_TOKENS = 6000
TRIM_TEXT_CHUNK_SIZE = 800

SYSTEM_PROMPT = build_system_prompt()


def generate_answer(
    query: str,
    decision: RouteDecision,
    drug_result: DrugSearchResult | None = None,
    retrieval_matches: list[RetrievalMatch] | None = None,
    llm: AnswerLLM | None = None,
    use_llm: bool = True,
) -> str:
    """Generate a user-facing answer from already verified tool outputs.

    The deterministic formatter remains the fallback and safety baseline. The LLM
    is only asked to rewrite the structured answer, not to retrieve or decide.
    """

    structured_answer = format_answer(
        query=query,
        decision=decision,
        drug_result=drug_result,
        retrieval_matches=retrieval_matches,
    )

    if not use_llm:
        return structured_answer

    messages = build_answer_messages(
        query=query,
        decision=decision,
        structured_answer=structured_answer,
    )

    trimmed_messages = trim_answer_messages(messages)

    try:
        if llm:
            return normalize_answer_text(llm(trimmed_messages))
        return normalize_answer_text(call_configured_llm(trimmed_messages))
    except Exception as exc:
        return format_llm_fallback_answer(structured_answer=structured_answer, error=exc)


def build_answer_messages(
    query: str,
    decision: RouteDecision,
    structured_answer: str,
) -> list[ChatMessage]:
    user_prompt = f"""사용자 질문:
{query}

라우팅 결과:
- route: {decision.route}
- reason: {decision.reason}
- matched_terms: {", ".join(decision.matched_terms) if decision.matched_terms else "없음"}

검증된 구조화 답변:
{structured_answer}

작성 지침:
{build_answer_writing_instructions()}

필수 유지 정보:
- 사용자 질문: {query}
- route: {decision.route}
- {OFFICIAL_DECISION_DISCLAIMER}
"""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def trim_answer_messages(
    messages: list[ChatMessage],
    max_tokens: int = DEFAULT_MAX_PROMPT_TOKENS,
) -> list[ChatMessage]:
    trimmed = trim_messages(
        messages,
        max_tokens=max_tokens,
        token_counter="approximate",
        strategy="last",
        include_system=True,
        allow_partial=True,
        text_splitter=split_text_for_trimming,
    )
    chat_messages = [base_message_to_chat_message(message) for message in trimmed]

    if has_user_message(chat_messages):
        return chat_messages

    fallback_user_message = build_fallback_user_message(messages)
    if fallback_user_message is None:
        return chat_messages

    return [*chat_messages, fallback_user_message]


def has_user_message(messages: list[ChatMessage]) -> bool:
    return any(message["role"] == "user" for message in messages)


def build_fallback_user_message(messages: list[ChatMessage]) -> ChatMessage | None:
    user_messages = [message for message in messages if message["role"] == "user"]
    if not user_messages:
        return None

    content = user_messages[-1]["content"]
    return {"role": "user", "content": content[-TRIM_TEXT_CHUNK_SIZE:]}


def split_text_for_trimming(text: str) -> list[str]:
    return [
        text[index : index + TRIM_TEXT_CHUNK_SIZE]
        for index in range(0, len(text), TRIM_TEXT_CHUNK_SIZE)
    ]


def base_message_to_chat_message(message: BaseMessage) -> ChatMessage:
    if isinstance(message, SystemMessage):
        role = "system"
    elif isinstance(message, HumanMessage):
        role = "user"
    elif isinstance(message, AIMessage):
        role = "assistant"
    else:
        role = "user"

    return {"role": role, "content": extract_message_content(message.content)}


def call_configured_llm(messages: list[ChatMessage]) -> str:
    provider = settings.llm_provider.strip().casefold()

    if provider == "openai":
        return call_openai(messages)

    msg = f"Unsupported LLM_PROVIDER: {settings.llm_provider}"
    raise ValueError(msg)


def call_openai(messages: list[ChatMessage]) -> str:
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is not configured.")

    llm = ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openai_api_key,
        temperature=0.2,
    )
    response = llm.invoke(messages)
    return extract_message_content(response.content)


def extract_message_content(content: str | list[str | dict]) -> str:
    if isinstance(content, str):
        return content

    parts: list[str] = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
            continue

        if block.get("type") == "text" and isinstance(block.get("text"), str):
            parts.append(block["text"])

    return "\n".join(parts)


def normalize_answer_text(answer: str) -> str:
    cleaned = answer.strip()
    if not cleaned:
        raise ValueError("LLM returned an empty answer.")
    return cleaned


def format_llm_fallback_answer(structured_answer: str, error: Exception) -> str:
    return "\n".join(
        [
            structured_answer,
            "",
            "## 생성 상태",
            f"- LLM 답변 생성 중 오류가 발생해 구조화 답변으로 대체했습니다: {type(error).__name__}",
        ]
    )
