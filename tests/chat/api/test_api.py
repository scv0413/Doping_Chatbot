import json
import logging

from fastapi.testclient import TestClient

from app.chat.api.dependencies import get_chat_service
from app.chat.api.logging import REQUEST_ID_HEADER, JsonLogFormatter
from app.chat.api.main import create_app
from app.chat.runtime import ChatEngine, ChatRequest, ChatResponse


def fake_chat_service(request: ChatRequest) -> ChatResponse:
    return ChatResponse(
        answer=f"stub answer: {request.query}",
        route="rag",
        query=request.query,
        engine=request.engine or ChatEngine.GRAPH,
        top_k=request.top_k or 3,
        use_llm=request.use_llm if request.use_llm is not None else False,
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
    assert response.headers[REQUEST_ID_HEADER]


def test_ready_endpoint_reports_runtime_dependencies() -> None:
    client = build_test_client()

    response = client.get("/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ready", "not_ready"}
    check_names = {check["name"] for check in body["checks"]}
    assert {
        "processed_data_dir",
        "processed_chunks",
        "index_dir",
        "chroma_directory",
        "chroma_collection",
        "openai_api_key",
        "runtime_import",
        "runtime_policy_import",
    }.issubset(check_names)


def test_root_endpoint_points_to_docs() -> None:
    client = build_test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["docs"] == "/docs"


def test_create_chat_response_endpoint_accepts_query_only() -> None:
    client = build_test_client()

    response = client.post(
        "/api/v1/chat-responses",
        json={"query": "도핑 검사관 신분이 불분명하면 어떻게 해?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"].startswith("stub answer")
    assert body["query"] == "도핑 검사관 신분이 불분명하면 어떻게 해?"
    assert "route" not in body
    assert "engine" not in body
    assert "top_k" not in body
    assert "use_llm" not in body
    assert "retrieval_attempts" not in body


def test_create_chat_response_rejects_internal_options() -> None:
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

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_create_debug_chat_response_accepts_internal_options() -> None:
    client = build_test_client()

    response = client.post(
        "/api/v1/debug/chat-responses",
        json={
            "query": "도핑 검사관 신분이 불분명하면 어떻게 해?",
            "top_k": 3,
            "use_llm": False,
            "engine": "graph",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["top_k"] == 3
    assert body["use_llm"] is False
    assert body["engine"] == ChatEngine.GRAPH


def test_create_chat_response_hides_runtime_policy_defaults() -> None:
    client = build_test_client()

    response = client.post(
        "/api/v1/chat-responses",
        json={"query": "슈도에페드린 반감기가 얼마나 돼?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"].startswith("stub answer")
    assert "engine" not in body
    assert "top_k" not in body
    assert "use_llm" not in body
    assert "policy_reason" not in body
    assert "policy_matched_rules" not in body


def test_create_chat_response_returns_standard_validation_error() -> None:
    client = build_test_client()

    response = client.post(
        "/api/v1/chat-responses",
        json={"query": ""},
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
        json={"query": "도핑 검사관 신분이 불분명하면 어떻게 해?"},
    )

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_server_error"
    assert body["error"]["message"] == "서버 처리 중 오류가 발생했습니다."
    assert body["error"]["details"] == []


def test_success_response_echoes_incoming_request_id() -> None:
    client = build_test_client()

    response = client.get("/health", headers={REQUEST_ID_HEADER: "test-request-123"})

    assert response.status_code == 200
    assert response.headers[REQUEST_ID_HEADER] == "test-request-123"


def test_validation_error_includes_request_id_in_header_and_body() -> None:
    client = build_test_client()

    response = client.post(
        "/api/v1/chat-responses",
        headers={REQUEST_ID_HEADER: "validation-request-123"},
        json={"query": ""},
    )

    assert response.status_code == 422
    assert response.headers[REQUEST_ID_HEADER] == "validation-request-123"
    assert response.json()["error"]["request_id"] == "validation-request-123"


def test_unhandled_error_includes_request_id_in_header_and_body() -> None:
    def broken_chat_service(request: ChatRequest) -> ChatResponse:
        raise RuntimeError("temporary failure")

    client = build_test_client(chat_service=broken_chat_service)

    response = client.post(
        "/api/v1/chat-responses",
        headers={REQUEST_ID_HEADER: "internal-error-request-123"},
        json={"query": "도핑 검사관 신분이 불분명하면 어떻게 해?"},
    )

    assert response.status_code == 500
    assert response.headers[REQUEST_ID_HEADER] == "internal-error-request-123"
    assert response.json()["error"]["request_id"] == "internal-error-request-123"


def test_json_log_formatter_outputs_structured_json() -> None:
    record = logging.LogRecord(
        name="app.chat.api",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="request_completed",
        args=(),
        exc_info=None,
    )
    record.request_id = "log-request-123"
    record.method = "GET"
    record.path = "/health"
    record.status_code = 200
    record.duration_ms = 12.34

    payload = json.loads(JsonLogFormatter().format(record))

    assert payload["message"] == "request_completed"
    assert payload["request_id"] == "log-request-123"
    assert payload["method"] == "GET"
    assert payload["path"] == "/health"
    assert payload["status_code"] == 200
    assert payload["duration_ms"] == 12.34


def test_public_chat_response_schema_hides_internal_runtime_fields() -> None:
    client = build_test_client()

    response = client.get("/openapi.json")

    assert response.status_code == 200
    schemas = response.json()["components"]["schemas"]
    public_properties = schemas["PublicChatResponse"]["properties"]
    chat_properties = schemas["ChatResponse"]["properties"]

    for internal_field in (
        "route",
        "engine",
        "top_k",
        "use_llm",
        "policy_reason",
        "policy_matched_rules",
        "retrieval_attempts",
        "retrieval_retry_reason",
        "planned_tool_names",
    ):
        assert internal_field not in public_properties
        assert internal_field in chat_properties
