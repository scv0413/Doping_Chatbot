import pytest
from pydantic import ValidationError

from app.chat.drug_search.schemas import DrugSearchInput
from app.chat.retrieval.schemas import RetrievalMatch, RetrievalMetadata
from app.chat.runtime import ChatEngine, ChatRequest, ChatRuntimeDependencies, run_chat


def fake_retriever(query: str, top_k: int) -> list[RetrievalMatch]:
    assert top_k == 2
    return [
        RetrievalMatch(
            rank=1,
            chunk_id="field_response_manual:s1:c0",
            distance=0.2,
            metadata=RetrievalMetadata(
                source_id="field_response_manual",
                title="현장 대응 매뉴얼",
                page=None,
            ),
            text=(
                "검사관 신분 확인, 소속 확인, 절차 설명 요청, 기록, 동석 요청. "
                "공식 절차 확인 전에는 무단 거부로 보일 행동을 피해야 한다. "
                "선수는 검사관의 신분증과 통지 내용을 정중히 확인하고, 통역이나 팀 관계자 동석을 요청할 수 있다."
            ),
        )
    ]


def identity_rewriter(query: str) -> str:
    return query


def test_run_chat_uses_graph_engine_by_default() -> None:
    response = run_chat(
        ChatRequest(
            query="도핑 검사관 신분이 불분명하면 어떻게 확인해야 해?",
            top_k=2,
            use_llm=False,
        ),
        dependencies=ChatRuntimeDependencies(
            retriever=fake_retriever,
            query_rewriter=identity_rewriter,
        ),
    )

    assert response.engine is ChatEngine.GRAPH
    assert response.route == "rag"
    assert response.citations[0].chunk_id == "field_response_manual:s1:c0"
    assert response.retrieval_attempts == 1
    assert response.errors == []
    assert "확인" in response.answer


def test_run_chat_can_use_pipeline_engine() -> None:
    response = run_chat(
        ChatRequest(
            query="도핑 검사관 신분이 불분명하면 어떻게 확인해야 해?",
            top_k=2,
            use_llm=False,
            engine=ChatEngine.PIPELINE,
        ),
        dependencies=ChatRuntimeDependencies(
            retriever=fake_retriever,
            query_rewriter=identity_rewriter,
        ),
    )

    assert response.engine is ChatEngine.PIPELINE
    assert response.route == "rag"
    assert response.retrieval_attempts == 1
    assert response.citations[0].source_id == "field_response_manual"


def test_run_chat_accepts_plain_string_and_drug_search_input() -> None:
    string_response = run_chat(
        "도핑 검사관 신분이 불분명하면 어떻게 확인해야 해?",
        dependencies=ChatRuntimeDependencies(
            retriever=fake_retriever,
            query_rewriter=identity_rewriter,
        ),
    )
    input_response = run_chat(
        DrugSearchInput(query="도핑 검사관 신분이 불분명하면 어떻게 확인해야 해?"),
        dependencies=ChatRuntimeDependencies(
            retriever=fake_retriever,
            query_rewriter=identity_rewriter,
        ),
    )

    assert string_response.query == input_response.query
    assert string_response.route == input_response.route


def test_chat_request_validates_query_and_top_k() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(query="")

    with pytest.raises(ValidationError):
        ChatRequest(query="질문", top_k=0)

    with pytest.raises(ValidationError):
        ChatRequest(query="질문", top_k=11)
