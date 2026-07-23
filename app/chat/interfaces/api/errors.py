import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.chat.interfaces.api.logging import REQUEST_ID_HEADER, get_current_request_id

logger = logging.getLogger("app.chat.interfaces.api.errors")


class ApiErrorBody(BaseModel):
    code: str
    message: str
    request_id: str | None = None
    details: list[dict[str, Any]] = Field(default_factory=list)


class ApiErrorResponse(BaseModel):
    error: ApiErrorBody


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)


async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    request_id = resolve_request_id(request)
    logger.info(
        "api_validation_error",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
        },
    )
    return build_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="validation_error",
        message="요청 형식이 올바르지 않습니다.",
        details=normalize_validation_errors(exc.errors()),
        request_id=request_id,
    )


async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return build_error_response(
        status_code=exc.status_code,
        code="http_error",
        message=str(exc.detail),
        request_id=resolve_request_id(request),
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = resolve_request_id(request)
    logger.exception(
        "api_unhandled_error",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "error_type": type(exc).__name__,
        },
    )
    return build_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="internal_server_error",
        message="서버 처리 중 오류가 발생했습니다.",
        request_id=request_id,
    )


def build_error_response(
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
    request_id: str | None = None,
) -> JSONResponse:
    request_id = request_id or get_current_request_id()
    body = ApiErrorResponse(
        error=ApiErrorBody(
            code=code,
            message=message,
            request_id=request_id,
            details=details or [],
        )
    )
    headers = {REQUEST_ID_HEADER: request_id} if request_id else None
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(mode="json"),
        headers=headers,
    )


def normalize_validation_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for error in errors:
        normalized.append(
            {
                "loc": [str(part) for part in error.get("loc", [])],
                "message": str(error.get("msg", "Invalid value")),
                "type": str(error.get("type", "value_error")),
            }
        )
    return normalized


def resolve_request_id(request: Request) -> str | None:
    state_request_id = getattr(request.state, "request_id", None)
    if state_request_id:
        return str(state_request_id)
    return get_current_request_id()
