"""Fixtures compartidas.

Las pruebas que requieren PostgreSQL usan ``TEST_DATABASE_URL`` (o ``DATABASE_URL``) y se
omiten automáticamente si la base de datos no está disponible.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import httpx
import pytest
from app.core.config import Settings
from app.main import create_app
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


def _test_database_url() -> str | None:
    return os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")


@pytest.fixture(scope="session")
def settings() -> Settings:
    url = _test_database_url() or "postgresql+psycopg://sti_app:sti_app@localhost:5432/sti_test"
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        app_env="test",
        debug=False,
        database_url=url,
        cors_origins=["http://localhost:5173"],
        jwt_secret_key="test-secret-key-with-at-least-32-characters!!",
    )


@pytest.fixture(scope="session")
async def database_available(settings: Settings) -> bool:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
    finally:
        await engine.dispose()


@pytest.fixture
async def client(settings: Settings) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(settings)
    async with (
        httpx.ASGITransport(app=app) as transport,  # type: ignore[arg-type]
        _lifespan(app),
        httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers={"Origin": "http://localhost:5173"},
        ) as ac,
    ):
        yield ac


class _lifespan:  # noqa: N801 - helper de contexto
    def __init__(self, app: object) -> None:
        self._app = app
        self._cm: object | None = None

    async def __aenter__(self) -> None:
        router = self._app.router  # type: ignore[attr-defined]
        self._cm = router.lifespan_context(self._app)
        await self._cm.__aenter__()  # type: ignore[union-attr]

    async def __aexit__(self, *exc: object) -> None:
        assert self._cm is not None
        await self._cm.__aexit__(*exc)  # type: ignore[union-attr]
