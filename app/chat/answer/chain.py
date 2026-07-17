from langchain_openai import ChatOpenAI

from app.chat.answer.formatter import format_answer
from app.chat.answer.types import AnswerLLM, ChatMessage
from app.chat.config import settings
from app.chat.drug_search.schemas import DrugSearchResult
from app.chat.retrieval.schemas import RetrievalMatch
from app.chat.router.intent_router import RouteDecision


SYSTEM_PROMPT = """당신은 엘리트 선수와 트레이너를 돕는 도핑 정보 챗봇입니다.

역할:
- 제공된 KADA 약물검색 결과와 RAG 문서 근거만 사용해 답변합니다.
- 근거에 없는 법적 판단, 의학적 처방, 복용 가능 확정 표현을 만들지 않습니다.
- 사용자가 현장에서 바로 이해할 수 있게 짧고 명확한 한국어로 답변합니다.
- 문서 근거가 부족하면 부족하다고 말하고 추가 확인 방법을 안내합니다.
- chunk_id, 문서명, page 정보가 있으면 답변 하단에 유지합니다.

안전 원칙:
- 도핑 관련 답변은 공식 판정을 대체하지 않습니다.
- 약물 질문은 제품명, 성분명, 투여 경로, 용량, 종목, 경기기간 여부를 확인하도록 안내합니다.
- 현장 절차 질문은 즉시 충돌보다 확인, 기록, 동석 요청, 공식 절차 확인을 우선하도록 안내합니다.
"""


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

    try:
        if llm:
            return normalize_answer_text(llm(messages))
        return normalize_answer_text(call_configured_llm(messages))
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
1. 위 구조화 답변의 사실과 주의문을 유지하세요.
2. 사용자가 바로 행동 기준을 알 수 있도록 답변하세요.
3. 근거가 부족한 부분은 확정하지 말고 추가 확인이 필요하다고 말하세요.
4. 답변 마지막에 근거와 주의 섹션을 유지하세요.
"""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


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
