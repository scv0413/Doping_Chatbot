from app.chat.runtime import ChatEngine, ChatRequest, ChatResponse, CitationSummary
from app.chat.ui.gradio_app import build_demo, format_citations, format_metadata, respond


def fake_runner(request: ChatRequest) -> ChatResponse:
    assert request.query == "S0 비승인약물이 뭐야?"
    assert request.top_k in {None, 3}
    assert request.engine in {None, ChatEngine.GRAPH}
    return ChatResponse(
        answer="S0은 비승인 약물입니다.",
        route="rag",
        query=request.query,
        engine=request.engine or ChatEngine.GRAPH,
        top_k=request.top_k or 3,
        use_llm=request.use_llm if request.use_llm is not None else False,
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


def test_respond_returns_answer_citations_and_metadata() -> None:
    answer, citations, metadata = respond(
        " S0 비승인약물이 뭐야? ",
        top_k=3,
        use_llm=False,
        engine="graph",
        runner=fake_runner,
    )

    assert "S0" in answer
    assert "wada_prohibited_list_2026_ko:p5:c0" in citations
    assert "route" in metadata
    assert "retrieval_attempts" in metadata


def test_respond_can_use_runtime_policy_defaults() -> None:
    answer, citations, metadata = respond(" S0 비승인약물이 뭐야? ", runner=fake_runner)

    assert "S0" in answer
    assert "wada_prohibited_list_2026_ko:p5:c0" in citations
    assert "route" in metadata


def test_respond_handles_empty_query() -> None:
    answer, citations, metadata = respond("   ", 3, False, "graph", runner=fake_runner)

    assert answer == "질문을 입력해주세요."
    assert citations == ""
    assert metadata == ""


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
