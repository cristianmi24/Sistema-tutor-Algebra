"""Punto de entrada de la aplicación FastAPI (STI-GA).

Ejecutar en desarrollo:  uvicorn app.main:app --reload --port 8000
Documentación OpenAPI:   http://localhost:8000/docs
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1 import api_router
from app.core.config import Settings, get_settings
from app.core.database import build_engine, build_session_factory
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import register_middleware
from app.core.ratelimit import register_rate_limiting
from app.modules.identity.email import build_email_sender

log = get_logger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, json_output=settings.is_production)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = build_engine(settings)
        app.state.engine = engine
        app.state.session_factory = build_session_factory(engine)
        log.info(
            "app_started",
            environment=settings.app_env,
            version=settings.app_version,
            llm_enabled=settings.llm_enabled,
        )
        try:
            yield
        finally:
            await engine.dispose()
            log.info("app_stopped")

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "API del Sistema Tutor Inteligente para la Generalización Algebraica. "
            "Observar mucho, intervenir poco y adaptar cuando sea necesario."
        ),
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url=f"{settings.api_prefix}/openapi.json" if not settings.is_production else None,
    )

    app.state.settings = settings
    app.state.email_sender = build_email_sender(settings)
    register_middleware(app, settings)
    register_rate_limiting(app, settings)
    register_error_handlers(app)
    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
