"""Fixtures compartidas.

Las pruebas de integración usan PostgreSQL (``TEST_DATABASE_URL`` o ``DATABASE_URL``). Las migraciones
se aplican una vez por sesión en un subproceso (``alembic/env.py`` usa ``asyncio.run``) y las tablas
se vacían entre pruebas.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import httpx
import pytest
from app.core.config import Settings
from app.main import create_app
from app.models import Base
from app.modules.identity.email import MemoryEmailSender
from app.seed.demo import (
    create_admin,
    create_researcher,
    create_student,
    create_teacher,
    ensure_institution,
)
from app.seed.legal import seed_legal_documents
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

TEST_PASSWORD = "Prueba-Segura-2026!"


def _test_database_url() -> str:
    return (
        os.environ.get("TEST_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or "postgresql+psycopg://sti_app:sti_app@localhost:5432/sti_test"
    )


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        app_env="test",
        debug=False,
        database_url=_test_database_url(),
        cors_origins=["http://localhost:5173"],
        jwt_secret_key="test-secret-key-with-at-least-32-characters!!",
        rate_limit_enabled=False,
        email_backend="memory",
        access_token_expire_minutes=15,
        log_level="WARNING",
    )


def _database_reachable(url: str) -> bool:
    from sqlalchemy import create_engine

    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
    finally:
        engine.dispose()


def run_alembic(url: str, *args: str) -> None:
    env = {**os.environ, "DATABASE_URL": url, "APP_ENV": "test"}
    env.pop("ALEMBIC_DATABASE_URL", None)
    subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        check=True,
        env=env,
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="session")
def database_available(settings: Settings) -> bool:
    return _database_reachable(settings.database_url)


@pytest.fixture(scope="session")
def migrated_database(settings: Settings, database_available: bool) -> bool:
    if not database_available:
        return False
    run_alembic(settings.database_url, "upgrade", "head")
    return True


@pytest.fixture(scope="session")
async def engine(settings: Settings, migrated_database: bool) -> AsyncIterator[AsyncEngine]:
    if not migrated_database:
        pytest.skip("PostgreSQL no disponible")
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Sesión limpia: vacía todas las tablas de la app antes de cada prueba."""
    tables = ", ".join(f'"{t.schema}"."{t.name}"' for t in Base.metadata.sorted_tables)
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


class _Lifespan:
    def __init__(self, app: Any) -> None:
        self._app = app
        self._cm: Any = None

    async def __aenter__(self) -> None:
        self._cm = self._app.router.lifespan_context(self._app)
        await self._cm.__aenter__()

    async def __aexit__(self, *exc: object) -> None:
        await self._cm.__aexit__(*exc)


@pytest.fixture
async def app(settings: Settings) -> Any:
    return create_app(settings)


@pytest.fixture
async def client(app: Any) -> AsyncIterator[httpx.AsyncClient]:
    async with (
        _Lifespan(app),
        httpx.ASGITransport(app=app) as transport,  # type: ignore[arg-type]
        httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers={"Origin": "http://localhost:5173"},
        ) as ac,
    ):
        yield ac


@pytest.fixture
def outbox(app: Any) -> list[Any]:
    sender = app.state.email_sender
    assert isinstance(sender, MemoryEmailSender)
    return sender.outbox


# ----------------------------------------------------------------------------- datos semilla


@dataclass
class SeededWorld:
    institution_id: str
    institution_code: str
    admin_email: str
    teacher_email: str
    researcher_email: str
    student_username: str
    student_id: str
    student_participant_code: str
    teacher_id: str
    researcher_id: str
    password: str = TEST_PASSWORD


@pytest.fixture
async def world(db: AsyncSession, settings: Settings) -> SeededWorld:
    await seed_legal_documents(db, settings)
    institution = await ensure_institution(
        db, code="TEST", name="Institución de prueba", required_parties=["STUDENT", "GUARDIAN"]
    )
    await create_admin(db, email="admin@test.edu", password=TEST_PASSWORD)
    teacher = await create_teacher(
        db,
        email="teacher@test.edu",
        password=TEST_PASSWORD,
        institution=institution,
        groups=[("8", "A")],
    )
    researcher = await create_researcher(
        db, email="researcher@test.edu", password=TEST_PASSWORD, institution=institution
    )
    student = await create_student(
        db,
        username="stu1",
        password=TEST_PASSWORD,
        institution=institution,
        grade="8",
        group_code="A",
    )
    await db.commit()
    return SeededWorld(
        institution_id=str(institution.id),
        institution_code=institution.code,
        admin_email="admin@test.edu",
        teacher_email="teacher@test.edu",
        researcher_email="researcher@test.edu",
        student_username="stu1",
        student_id=str(student.id),
        student_participant_code=student.participant_code,
        teacher_id=str(teacher.id),
        researcher_id=str(researcher.id),
    )


LoginFn = Callable[[str], Awaitable[dict[str, str]]]


@pytest.fixture
def login(client: httpx.AsyncClient) -> LoginFn:
    async def _login(identifier: str, password: str = TEST_PASSWORD) -> dict[str, str]:
        response = await client.post("/api/v1/auth/login", json={"identifier": identifier, "password": password})
        assert response.status_code == 200, response.text
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _login  # type: ignore[return-value]
