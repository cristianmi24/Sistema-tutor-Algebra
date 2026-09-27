"""Excepciones de dominio y manejo uniforme de errores HTTP.

Formato de error público (nunca incluye trazas ni detalles internos):

    {"error": {"code": "...", "message": "...", "request_id": "...", "details": ...}}
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger, request_id_ctx

log = get_logger(__name__)


class AppError(Exception):
    """Error de aplicación con código estable y estado HTTP."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "BAD_REQUEST"

    def __init__(self, message: str, *, details: Any | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "NOT_FOUND"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "CONFLICT"


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "UNAUTHORIZED"


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "FORBIDDEN"


class ServiceUnavailableError(AppError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "SERVICE_UNAVAILABLE"


def error_payload(code: str, message: str, details: Any | None = None) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id_ctx.get(),
            "details": details,
        }
    }


_HTTP_CODES: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
    503: "SERVICE_UNAVAILABLE",
}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"loc": list(err.get("loc", [])), "msg": err.get("msg"), "type": err.get("type")} for err in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=error_payload("VALIDATION_ERROR", "Los datos enviados no son válidos.", details),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _HTTP_CODES.get(exc.status_code, "HTTP_ERROR")
        message = exc.detail if isinstance(exc.detail, str) else "Error en la petición."
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(code, message),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled_exception", error_type=type(exc).__name__)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_payload("INTERNAL_ERROR", "Ocurrió un error interno. Intenta de nuevo."),
        )
