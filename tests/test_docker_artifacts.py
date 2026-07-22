from pathlib import Path


def test_dockerfile_runs_fastapi_api() -> None:
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")

    assert "ghcr.io/astral-sh/uv:python3.12" in dockerfile
    assert "uv sync --frozen --no-dev" in dockerfile
    assert "app.chat.api.main:app" in dockerfile
    assert "--no-access-log" in dockerfile
    assert "0.0.0.0" in dockerfile
    assert "8000" in dockerfile
    assert "USER appuser" in dockerfile
    assert "groupadd --system appuser" in dockerfile
    assert "chown -R appuser:appuser /app" in dockerfile
    assert "/ready" in dockerfile


def test_dockerignore_excludes_sensitive_and_runtime_data() -> None:
    dockerignore = Path(".dockerignore").read_text(encoding="utf-8")

    assert ".env" in dockerignore
    assert "!.env.example" in dockerignore
    assert ".venv" in dockerignore
    assert "data/raw" in dockerignore
    assert "data/processed" in dockerignore
    assert "data/indexes" in dockerignore
    assert "logs" in dockerignore


def test_compose_mounts_runtime_data_and_exposes_api_port() -> None:
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert "8000:8000" in compose
    assert "./data:/app/data" in compose
    assert "env_file:" in compose
    assert "- .env" in compose
    assert "RAW_DATA_DIR: /app/data/raw" in compose
    assert "/ready" in compose


def test_api_logging_module_is_configured() -> None:
    logging_file = Path("app/chat/api/logging.py").read_text(encoding="utf-8")
    main_file = Path("app/chat/api/main.py").read_text(encoding="utf-8")

    assert "request_completed" in logging_file
    assert "duration_ms" in logging_file
    assert "request_logging_middleware" in main_file


def test_github_actions_builds_and_smoke_tests_docker_image() -> None:
    workflow = Path(".github/workflows/docker-build.yml").read_text(encoding="utf-8")

    assert "docker build -t doping-chatbot-api:ci ." in workflow
    assert "docker run -d" in workflow
    assert "http://127.0.0.1:8000/health" in workflow
    assert "http://127.0.0.1:8000/ready" in workflow
    assert "uv run pytest" in workflow
    assert "uv run ruff check app tests" in workflow
