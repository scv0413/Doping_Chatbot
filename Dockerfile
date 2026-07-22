FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    APP_ENV=production \
    RAW_DATA_DIR=/app/data/raw \
    PROCESSED_DATA_DIR=/app/data/processed \
    INDEX_DIR=/app/data/indexes

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev

COPY app ./app
RUN mkdir -p /app/data/raw /app/data/processed /app/data/indexes \
    && groupadd --system appuser \
    && useradd --system --gid appuser --home-dir /app --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD uv run --no-sync python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=2).read()"

CMD ["uv", "run", "--no-sync", "uvicorn", "app.chat.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
