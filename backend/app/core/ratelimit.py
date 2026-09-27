"""Rate limiting (slowapi) para endpoints sensibles.

Se activa/desactiva con ``RATE_LIMIT_ENABLED``; las pruebas lo desactivan.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import Settings, get_settings
from app.core.errors import error_payload

limiter = Limiter(key_func=get_remote_address, headers_enabled=True)


def auth_limit() -> str:
    return get_settings().rate_limit_auth


def register_rate_limiting(app: FastAPI, settings: Settings) -> None:
    limiter.enabled = settings.rate_limit_enabled
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def _rate_limited(_: Request, exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content=error_payload("RATE_LIMITED", "Demasiados intentos. Espera un momento e inténtalo de nuevo."),
            headers={"Retry-After": "60"},
        )
