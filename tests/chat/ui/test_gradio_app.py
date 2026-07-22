from app.chat.runtime import ChatEngine, ChatRequest, ChatResponse, CitationSummary
from app.chat.ui.gradio_app import build_demo, format_citations, format_metadata, respond


def fake_runner(request: ChatRequest) -> ChatResponse:
    assert request.query == "S0 비승인약물이 뭐야?"
    assert request.top_k is None
    assert request.use_llm is None
    assert request.engine is None
    return ChatResponse(
        answer="S0은 비승인 약물입니다.",
        route="rag",
        query=request.query,
        engine=ChatEngine.GRAPH,
        top_k=3,
        use_llm=False,
        citations=[
            CitationSummary(
                chunk_id="wada_prohibited_list_2026_ko:p5:c0",
                source_id="wada_prohibited_list_2026_ko",
                title="금지목록 국제표준",
                page=5,
                distance=0.2,
            )
        ],
        retrieval_attempts=1,
    )


def test_respond_returns_answer_and_citations_with_runtime_policy_defaults() -> None:
    answer, citations = respond(" S0 비승인약물이 뭐야? ", runner=fake_runner)

    assert "S0" in answer
    assert "wada_prohibited_list_2026_ko:p5:c0" in citations


def test_respond_handles_empty_query() -> None:
    answer, citations = respond("   ", runner=fake_runner)

    assert answer == "질문을 입력해주세요."
    assert citations == ""


def test_format_helpers_handle_no_citations() -> None:
    response = ChatResponse(
        answer="답변",
        route="drug_search",
        query="타이레놀 먹어도 돼?",
        engine=ChatEngine.GRAPH,
    )

    assert format_citations(response) == "검색된 문서 근거가 없습니다."
    assert "drug_search" in format_metadata(response)


def test_build_demo_creates_gradio_blocks() -> None:
    demo = build_demo(runner=fake_runner)

    assert demo is not None
    assert hasattr(demo, "launch")


def test_respond_does_not_expose_internal_runtime_metadata() -> None:
    answer, citations = respond("S0 비승인약물이 뭐야?", runner=fake_runner)
    combined = answer + "\n" + citations

    assert "engine" not in combined
    assert "top_k" not in combined
    assert "use_llm" not in combined
    assert "retrieval_attempts" not in combined
