import pytest
from fastapi.testclient import TestClient

from app.chat.api.dependencies import get_chat_service
from app.chat.api.main import create_app
from app.chat.config import settings
from app.chat.runtime import ChatEngine, ChatRequest, ChatResponse


def fake_chat_service(request: ChatRequest) -> ChatResponse:
    return ChatResponse(
        answer=f"stub answer: {request.query}",
        route="rag",
        query=request.query,
        engine=request.engine or ChatEngine.GRAPH,
        top_k=request.top_k or 3,
        use_llm=False,
        retrieval_attempts=1,
    )


def build_client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_chat_service] = lambda: fake_chat_service
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def security_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.chat.api.security import rate_limiter

    monkeypatch.setattr(settings, "api_auth_enabled", True)
    monkeypatch.setattr(
        settings,
        "api_key_roles",
        "athlete-secret:athlete,trainer-secret:trainer,admin-secret:admin",
    )
    monkeypatch.setattr(settings, "api_rate_limit_enabled", True)
    monkeypatch.setattr(settings, "api_rate_limit_requests", 2)
    monkeypatch.setattr(settings, "api_rate_limit_window_seconds", 60)
    rate_limiter.reset()


def test_public_chat_requires_api_key_when_auth_is_enabled() -> None:
    response = build_client().post("/api/v1/chat-responses", json={"query": "S0이 뭐야?"})

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "API key is required"


def test_athlete_key_can_call_public_chat() -> None:
    response = build_client().post(
        "/api/v1/chat-responses",
        headers={"X-API-Key": "athlete-secret"},
        json={"query": "S0이 뭐야?"},
    )

    assert response.status_code == 200
    assert response.json()["answer"].startswith("stub answer")


def test_debug_endpoint_requires_admin_role() -> None:
    response = build_client().post(
        "/api/v1/debug/chat-responses",
        headers={"X-API-Key": "trainer-secret"},
        json={"query": "S0이 뭐야?", "use_llm": False},
    )

    assert response.status_code == 403
    assert response.json()["error"]["message"] == "Insufficient role"


def test_admin_key_can_call_debug_endpoint() -> None:
    response = build_client().post(
        "/api/v1/debug/chat-responses",
        headers={"X-API-Key": "admin-secret"},
        json={"query": "S0이 뭐야?", "use_llm": False},
    )

    assert response.status_code == 200
    assert response.json()["engine"] == "graph"


def test_rate_limit_is_applied_per_authenticated_principal() -> None:
    client = build_client()
    headers = {"X-API-Key": "athlete-secret"}

    assert client.post("/api/v1/chat-responses", headers=headers, json={"query": "1"}).status_code == 200
    assert client.post("/api/v1/chat-responses", headers=headers, json={"query": "2"}).status_code == 200

    response = client.post("/api/v1/chat-responses", headers=headers, json={"query": "3"})

    assert response.status_code == 429
    assert response.json()["error"]["message"] == "Rate limit exceeded"
