from typing import Any

from scripts import staging_smoke
from scripts.staging_smoke import get_header, pass_if, print_results


def test_pass_if_builds_smoke_result() -> None:
    result = pass_if("health", True, "status=200")

    assert result.name == "health"
    assert result.passed is True
    assert result.detail == "status=200"


def test_print_results_outputs_pass_and_fail(capsys) -> None:
    results = [
        pass_if("health", True, "ok"),
        pass_if("ready", False, "not_ready"),
    ]

    print_results(results)

    output = capsys.readouterr().out
    assert "[PASS] health: ok" in output
    assert "[FAIL] ready: not_ready" in output


def test_get_header_is_case_insensitive() -> None:
    headers = {"x-request-id": "request-123"}

    assert get_header(headers, "X-Request-ID") == "request-123"


def test_run_smoke_checks_public_contract_and_pharmacology_policy(monkeypatch) -> None:
    def fake_request_json(
        method: str,
        url: str,
        payload: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = staging_smoke.DEFAULT_TIMEOUT_SECONDS,
    ) -> tuple[int, dict[str, Any], dict[str, str]]:
        del method, timeout
        request_headers = headers or {}
        response_headers = {staging_smoke.REQUEST_ID_HEADER: request_headers.get(staging_smoke.REQUEST_ID_HEADER, "generated")}

        if url.endswith("/health"):
            return 200, {"status": "ok"}, response_headers
        if url.endswith("/ready"):
            return 200, {"status": "ready", "checks": []}, response_headers
        if url.endswith("/api/v1/debug/chat-responses"):
            return 200, {"answer": "debug", "route": "rag", "top_k": payload.get("top_k"), "errors": []}, response_headers
        if payload and "top_k" in payload:
            return 422, {"error": {"code": "validation_error"}}, response_headers
        if payload and "반감기" in str(payload.get("query", "")):
            return 200, {"answer": "half-life", "route": "rag", "pharmacology_status": "not_found", "errors": []}, response_headers
        return 200, {"answer": "answer", "route": "rag", "errors": []}, response_headers

    monkeypatch.setattr(staging_smoke, "request_json", fake_request_json)

    results = staging_smoke.run_smoke("http://testserver")

    assert [result.name for result in results] == [
        "health",
        "ready",
        "public_chat",
        "public_rejects_internal_options",
        "public_pharmacology_policy",
        "debug_chat",
    ]
    assert all(result.passed for result in results)
