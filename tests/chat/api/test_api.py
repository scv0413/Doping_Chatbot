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


def build_test_client(chat_service=fake_chat_service) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_chat_service] = lambda: chat_service
    return TestClient(app, raise_server_exceptions=False)


def test_health_endpoint() -> None:
    client = build_test_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["app"] == "doping-chatbot"


def test_ready_endpoint_reports_runtime_dependencies() -> None:
    client = build_test_client()

    response = client.get("/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ready", "not_ready"}
    assert {check["name"] for check in body["checks"]} == {"processed_data_dir", "index_dir"}


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


def test_create_chat_response_returns_standard_validation_error() -> None:
    client = build_test_client()

    response = client.post(
        "/api/v1/chat-responses",
        json={"query": "", "top_k": 0},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["message"] == "요청 형식이 올바르지 않습니다."
    assert body["error"]["details"]


def test_unknown_route_returns_standard_http_error() -> None:
    client = build_test_client()

    response = client.get("/missing")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "http_error"
    assert body["error"]["message"] == "Not Found"


def test_unhandled_exception_returns_standard_internal_error() -> None:
    def broken_chat_service(request: ChatRequest) -> ChatResponse:
        raise RuntimeError("temporary failure")

    client = build_test_client(chat_service=broken_chat_service)

    response = client.post(
        "/api/v1/chat-responses",
        json={
            "query": "도핑 검사관 신분이 불분명하면 어떻게 해?",
            "top_k": 3,
            "use_llm": False,
            "engine": "graph",
        },
    )

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_server_error"
    assert body["error"]["message"] == "서버 처리 중 오류가 발생했습니다."
    assert body["error"]["details"] == []
