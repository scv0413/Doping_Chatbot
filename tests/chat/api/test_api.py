from fastapi.testclient import TestClient

from app.chat.api.dependencies import get_chat_service
from app.chat.api.main import create_app
from app.chat.runtime import ChatEngine, ChatRequest, ChatResponse


def fake_chat_service(request: ChatRequest) -> ChatResponse:
    return ChatResponse(
        answer=f"stub answer: {request.query}",
        route="rag",
        query=request.query,
        engine=request.engine,
        retrieval_attempts=1,
    )


def build_test_client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_chat_service] = lambda: fake_chat_service
    return TestClient(app)


def test_health_endpoint() -> None:
    client = build_test_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["app"] == "doping-chatbot"


def test_root_endpoint_points_to_docs() -> None:
    client = build_test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["docs"] == "/docs"


def test_create_chat_response_endpoint() -> None:
    client = build_test_client()

    response = client.post(
        "/api/v1/chat-responses",
        json={
            "query": "도핑 검사관 신분이 불분명하면 어떻게 해?",
            "top_k": 3,
            "use_llm": False,
            "engine": "graph",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"].startswith("stub answer")
    assert body["route"] == "rag"
    assert body["engine"] == ChatEngine.GRAPH
    assert body["retrieval_attempts"] == 1


def test_create_chat_response_validates_request_body() -> None:
    client = build_test_client()

    response = client.post(
        "/api/v1/chat-responses",
        json={"query": "", "top_k": 0},
    )

    assert response.status_code == 422
