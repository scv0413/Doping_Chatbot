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
