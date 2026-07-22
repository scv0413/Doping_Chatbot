import json
import logging
import sys
import time
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from uuid import uuid4

from fastapi import Request, Response

REQUEST_ID_HEADER = "X-Request-ID"
request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)

logger = logging.getLogger("app.chat.api")


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        request_id = getattr(record, "request_id", None) or request_id_context.get()
        if request_id:
            payload["request_id"] = request_id

        for field in ("method", "path", "status_code", "duration_ms", "error_type"):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    app_logger = logging.getLogger("app.chat")
    app_logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter())

    app_logger.handlers.clear()
    app_logger.addHandler(handler)
    app_logger.propagate = False


async def request_logging_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = get_or_create_request_id(request)
    request.state.request_id = request_id
    token = request_id_context.set(request_id)
    started_at = time.perf_counter()

    try:
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        duration_ms = (time.perf_counter() - started_at) * 1000

        logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )
        return response
    finally:
        request_id_context.reset(token)


def get_or_create_request_id(request: Request) -> str:
    incoming_request_id = request.headers.get(REQUEST_ID_HEADER)
    if incoming_request_id:
        return incoming_request_id
    return str(uuid4())


def get_current_request_id() -> str | None:
    return request_id_context.get()
