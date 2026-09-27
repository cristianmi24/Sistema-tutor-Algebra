"""Cookie HttpOnly del refresh token."""

from __future__ import annotations

from fastapi import Request, Response

from app.core.config import Settings


def refresh_cookie_path(settings: Settings) -> str:
    return f"{settings.api_prefix}/auth"


def set_refresh_cookie(response: Response, settings: Settings, raw_refresh: str) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=raw_refresh,
        max_age=settings.refresh_token_expire_days * 24 * 3600,
        path=refresh_cookie_path(settings),
        httponly=True,
        secure=settings.is_production,
        samesite="strict",
    )


def clear_refresh_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        path=refresh_cookie_path(settings),
        httponly=True,
        secure=settings.is_production,
        samesite="strict",
    )


def read_refresh_cookie(request: Request, settings: Settings) -> str | None:
    return request.cookies.get(settings.refresh_cookie_name)
