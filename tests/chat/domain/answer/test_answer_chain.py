from app.chat.domain.answer.chain import (
    build_answer_messages,
    extract_message_content,
    generate_answer,
    trim_answer_messages,
)
from app.chat.domain.drug_search.schemas import (
    CompetitionPeriod,
    DrugRiskStatus,
    DrugSearchInput,
    DrugSearchResult,
)
from app.chat.domain.retrieval.schemas import RetrievalMatch, RetrievalMetadata
from app.chat.router.intent_router import ChatRoute, RouteDecision
from app.chat.domain.policy.answer_policy import OFFICIAL_DECISION_DISCLAIMER


def test_generate_answer_uses_deterministic_formatter_when_llm_disabled() -> None:
    answer = generate_answer(
        query="도핑검사관 신분이 불분명하면 어떻게 확인해야 해?",
        decision=RouteDecision(route=ChatRoute.RAG, reason="rag only"),
        retrieval_matches=[
            RetrievalMatch(
                rank=1,
                chunk_id="field_response_manual:s1:c0",
                distance=0.2,
                metadata=RetrievalMetadata(
                    source_id="field_response_manual",
                    title="현장 대응 매뉴얼",
                ),
                text="검사관 신분이 불분명한 경우 신분 확인, 기록, 동석 요청이 필요합니다.",
            )
        ],
        use_llm=False,
    )

    assert "공식 문서와 manual source" in answer
    assert "확인, 기록, 동석 요청" in answer
    assert "경기기간 중 약물 사용" not in answer


def test_generate_answer_passes_structured_context_to_injected_llm() -> None:
    search_input = DrugSearchInput(
        query="슈도에페드린 경기기간 중 먹어도 돼?",
        ingredient_name="슈도에페드린",
        competition_period=CompetitionPeriod.IN_COMPETITION,
    )
    drug_result = DrugSearchResult(
        status=DrugRiskStatus.PROHIBITED_POSSIBLE,
        input=search_input,
        matched_substances=["슈도에페드린"],
        prohibited_categories=["S6_120"],
        requires_dose_confirmation=True,
        recommended_action="농도 기준 확인 필요",
    )
    captured_messages: list[dict[str, str]] = []

    def fake_llm(messages: list[dict[str, str]]) -> str:
        captured_messages.extend(messages)
        return "슈도에페드린은 경기기간 중 농도 기준 확인이 필요합니다.\n\n## 근거\n- S6_120"

    answer = generate_answer(
        query=search_input.query,
        decision=RouteDecision(route=ChatRoute.DRUG_SEARCH_WITH_RAG, reason="drug with rag"),
        drug_result=drug_result,
        retrieval_matches=[
            RetrievalMatch(
                rank=1,
                chunk_id="wada_prohibited_list_2026_ko:p17:c3",
                distance=0.3,
                metadata=RetrievalMetadata(
                    source_id="wada_prohibited_list_2026_ko",
                    title="금지목록 국제표준",
                    page=17,
                ),
                text="Pseudoephedrine has a prohibited urinary threshold.",
            )
        ],
        llm=fake_llm,
    )

    assert "농도 기준 확인" in answer
    assert "S6_120" in answer
    assert captured_messages[0]["role"] == "system"
    assert "검증된 구조화 답변" in captured_messages[1]["content"]
    assert "금지 가능성 있음" in captured_messages[1]["content"]
    assert "wada_prohibited_list_2026_ko:p17:c3" in captured_messages[1]["content"]


def test_generate_answer_falls_back_when_llm_fails() -> None:
    def broken_llm(messages: list[dict[str, str]]) -> str:
        raise RuntimeError("temporary llm failure")

    answer = generate_answer(
        query="TUE 신청 방법 알려줘",
        decision=RouteDecision(route=ChatRoute.RAG, reason="rag only"),
        retrieval_matches=[],
        llm=broken_llm,
    )

    assert "검색된 문서 근거가 없습니다" in answer
    assert "LLM 답변 생성 중 오류" in answer
    assert "RuntimeError" in answer


def test_build_answer_messages_contains_guardrails() -> None:
    messages = build_answer_messages(
        query="타이레놀 먹어도 돼?",
        decision=RouteDecision(route=ChatRoute.DRUG_SEARCH, reason="drug only"),
        structured_answer="## 답변 요약\n- 확인 필요",
    )

    assert messages[0]["role"] == "system"
    assert "근거에 없는 법적 판단" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert "route: drug_search" in messages[1]["content"]
    assert "확인 필요" in messages[1]["content"]


def test_extract_message_content_handles_langchain_content_blocks() -> None:
    content = [
        {"type": "text", "text": "첫 번째 문장"},
        "두 번째 문장",
        {"type": "tool_call", "name": "ignored"},
    ]

    assert extract_message_content(content) == "첫 번째 문장\n두 번째 문장"


def test_trim_answer_messages_preserves_system_and_required_query_info() -> None:
    query = "슈도에페드린 경기기간 중 먹어도 돼?"
    messages = build_answer_messages(
        query=query,
        decision=RouteDecision(route=ChatRoute.DRUG_SEARCH_WITH_RAG, reason="drug with rag"),
        structured_answer="긴 근거 " * 2000,
    )

    trimmed = trim_answer_messages(messages, max_tokens=300)

    assert trimmed[0]["role"] == "system"
    assert "도핑 정보 챗봇" in trimmed[0]["content"]
    assert trimmed[-1]["role"] == "user"
    assert query in trimmed[-1]["content"]
    assert OFFICIAL_DECISION_DISCLAIMER in trimmed[-1]["content"]
    assert len(trimmed[-1]["content"]) < len(messages[-1]["content"])


def test_generate_answer_passes_trimmed_messages_to_injected_llm() -> None:
    captured_messages: list[dict[str, str]] = []

    def fake_llm(messages: list[dict[str, str]]) -> str:
        captured_messages.extend(messages)
        return "trimmed answer"

    answer = generate_answer(
        query="TUE 신청 방법 알려줘",
        decision=RouteDecision(route=ChatRoute.RAG, reason="rag only"),
        retrieval_matches=[
            RetrievalMatch(
                rank=1,
                chunk_id="field_response_manual:s6:c0",
                distance=0.2,
                metadata=RetrievalMetadata(source_id="field_response_manual"),
                text="긴 검색 근거 " * 2000,
            )
        ],
        llm=fake_llm,
    )

    assert answer == "trimmed answer"
    assert captured_messages[0]["role"] == "system"
    assert captured_messages[-1]["role"] == "user"
    assert "TUE 신청 방법 알려줘" in captured_messages[-1]["content"]
