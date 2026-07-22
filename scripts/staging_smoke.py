import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REQUEST_ID_HEADER = "X-Request-ID"
DEFAULT_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True)
class SmokeResult:
    name: str
    passed: bool
    detail: str


def request_json(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[int, dict[str, Any], dict[str, str]]:
    body = None
    request_headers = {"Accept": "application/json"}
    if headers:
        request_headers.update(headers)

    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request_headers["Content-Type"] = "application/json"

    request = Request(url=url, data=body, headers=request_headers, method=method)

    try:
        with urlopen(request, timeout=timeout) as response:
            response_body = response.read().decode("utf-8")
            parsed = json.loads(response_body) if response_body else {}
            return response.status, parsed, dict(response.headers.items())
    except HTTPError as exc:
        response_body = exc.read().decode("utf-8")
        parsed = json.loads(response_body) if response_body else {}
        return exc.code, parsed, dict(exc.headers.items())
    except URLError as exc:
        raise RuntimeError(f"request failed: {url}: {exc}") from exc


def get_header(headers: dict[str, str], name: str) -> str | None:
    expected = name.lower()
    for key, value in headers.items():
        if key.lower() == expected:
            return value
    return None


def pass_if(name: str, condition: bool, detail: str) -> SmokeResult:
    return SmokeResult(name=name, passed=condition, detail=detail)


def run_smoke(base_url: str, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> list[SmokeResult]:
    base_url = base_url.rstrip("/")
    results: list[SmokeResult] = []

    status_code, body, headers = request_json("GET", f"{base_url}/health", timeout=timeout)
    results.append(
        pass_if(
            "health",
            status_code == 200 and body.get("status") == "ok" and bool(get_header(headers, REQUEST_ID_HEADER)),
            f"status={status_code}, body_status={body.get('status')}, request_id={get_header(headers, REQUEST_ID_HEADER)}",
        )
    )

    status_code, body, _ = request_json("GET", f"{base_url}/ready", timeout=timeout)
    readiness_status = body.get("status")
    failed_checks = [check.get("name") for check in body.get("checks", []) if not check.get("ready")]
    results.append(
        pass_if(
            "ready",
            status_code == 200 and readiness_status == "ready",
            f"status={status_code}, readiness={readiness_status}, failed_checks={failed_checks}",
        )
    )

    request_id = "staging-smoke-public-chat"
    status_code, body, headers = request_json(
        "POST",
        f"{base_url}/api/v1/chat-responses",
        payload={"query": "S0 비승인약물이 뭐야?"},
        headers={REQUEST_ID_HEADER: request_id},
        timeout=timeout,
    )
    results.append(
        pass_if(
            "public_chat",
            status_code == 200
            and bool(body.get("answer"))
            and get_header(headers, REQUEST_ID_HEADER) == request_id
            and not body.get("errors"),
            f"status={status_code}, route={body.get('route')}, request_id={get_header(headers, REQUEST_ID_HEADER)}, errors={body.get('errors')}",
        )
    )

    status_code, body, _ = request_json(
        "POST",
        f"{base_url}/api/v1/chat-responses",
        payload={"query": "S0 비승인약물이 뭐야?", "top_k": 1},
        timeout=timeout,
    )
    results.append(
        pass_if(
            "public_rejects_internal_options",
            status_code == 422 and body.get("error", {}).get("code") == "validation_error",
            f"status={status_code}, error_code={body.get('error', {}).get('code')}",
        )
    )

    status_code, body, _ = request_json(
        "POST",
        f"{base_url}/api/v1/debug/chat-responses",
        payload={
            "query": "S0 비승인약물이 뭐야?",
            "top_k": 3,
            "use_llm": False,
            "engine": "graph",
        },
        timeout=timeout,
    )
    results.append(
        pass_if(
            "debug_chat",
            status_code == 200 and bool(body.get("answer")) and body.get("top_k") == 3,
            f"status={status_code}, route={body.get('route')}, top_k={body.get('top_k')}, errors={body.get('errors')}",
        )
    )

    return results


def print_results(results: list[SmokeResult]) -> None:
    for result in results:
        marker = "PASS" if result.passed else "FAIL"
        print(f"[{marker}] {result.name}: {result.detail}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run staging smoke checks against the chat API.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        results = run_smoke(base_url=args.base_url, timeout=args.timeout)
    except RuntimeError as exc:
        print(f"[FAIL] smoke_error: {exc}", file=sys.stderr)
        return 1

    print_results(results)
    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
