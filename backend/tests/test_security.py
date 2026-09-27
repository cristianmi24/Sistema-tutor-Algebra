"""Fase 8: endurecimiento y verificación de seguridad (checklist C.44)."""

from __future__ import annotations

import base64
import json
import uuid

import httpx
import pytest
from app.core.config import Settings
from app.core.ratelimit import limiter
from app.main import create_app
from app.modules.identity.models import Institution, Student, User
from app.modules.identity.privacy import apply_retention
from app.modules.learning.models import Interaction, Task
from app.modules.ops.models import AuditLog
from app.seed.catalog import seed_catalog
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import TEST_PASSWORD, LoginFn, SeededWorld, _Lifespan


@pytest.fixture
async def catalog(db: AsyncSession, world: SeededWorld) -> dict[str, str]:
    await seed_catalog(db)
    await db.commit()
    return {t.code: str(t.id) for t in (await db.execute(select(Task))).scalars()}


async def test_trace_tables_are_append_only_in_the_database(
    client: httpx.AsyncClient, world: SeededWorld, login: LoginFn, catalog: dict[str, str], db: AsyncSession
) -> None:
    student = await login(world.student_username)
    session = (await client.post("/api/v1/sessions", json={}, headers=student)).json()
    first = await db.scalar(select(Interaction).where(Interaction.session_id == uuid.UUID(session["id"])))
    assert first is not None

    for statement in (
        f"UPDATE learning.interactions SET event_type = 'TASK_COMPLETED' WHERE id = '{first.id}'",
        f"DELETE FROM learning.interactions WHERE id = '{first.id}'",
        "UPDATE ops.audit_logs SET outcome = 'SUCCESS'",
        "DELETE FROM ops.audit_logs",
    ):
        with pytest.raises(DBAPIError, match="append-only"):
            async with db.begin_nested():
                await db.execute(text(statement))
    # Completar una vez la acción siguiente sí está permitido (enriquecimiento, no reescritura).
    await db.execute(
        text(
            "UPDATE learning.interactions SET next_student_action = 'X' "
            f"WHERE id = '{first.id}' AND next_student_action IS NULL"
        )
    )
    with pytest.raises(DBAPIError, match="ya fue registrado"):
        async with db.begin_nested():
            await db.execute(
                text(f"UPDATE learning.interactions SET next_student_action = 'Y' WHERE id = '{first.id}'")
            )
    await db.rollback()


async def test_oversized_payload_is_rejected(client: httpx.AsyncClient, world: SeededWorld) -> None:
    response = await client.post(
        "/api/v1/auth/login", content=b"x" * 1_100_000, headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


async def test_login_rate_limit(settings: Settings, world: SeededWorld) -> None:
    limiter.reset()
    app = create_app(settings.model_copy(update={"rate_limit_enabled": True, "rate_limit_auth": "5/minute"}))
    try:
        async with (
            _Lifespan(app),
            httpx.ASGITransport(app=app) as transport,  # type: ignore[arg-type]
            httpx.AsyncClient(transport=transport, base_url="http://testserver") as client,
        ):
            statuses = [
                (
                    await client.post("/api/v1/auth/login", json={"identifier": "nobody", "password": "whatever-123"})
                ).status_code
                for _ in range(7)
            ]
        assert statuses[:5] == [401] * 5
        assert statuses[5:] == [429, 429]
    finally:
        limiter.reset()
        limiter.enabled = False


async def test_unsigned_and_malformed_tokens_are_rejected(
    client: httpx.AsyncClient, world: SeededWorld, db: AsyncSession
) -> None:
    user_id = await db.scalar(select(User.id).where(User.email == world.admin_email))

    def b64(obj: dict[str, object]) -> str:
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()

    none_token = (
        f"{b64({'alg': 'none', 'typ': 'JWT'})}.{b64({'sub': str(user_id), 'role': 'ADMIN', 'exp': 9999999999})}."
    )
    for token in (none_token, "not-a-jwt", ""):
        response = await client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
    assert (await client.get("/api/v1/admin/users", headers={"Authorization": "Basic abc"})).status_code == 401


async def test_students_cannot_reach_each_others_data(
    client: httpx.AsyncClient, world: SeededWorld, login: LoginFn, catalog: dict[str, str], db: AsyncSession
) -> None:
    from app.seed.demo import create_student

    institution = await db.get(Institution, uuid.UUID(world.institution_id))
    assert institution is not None
    other = await create_student(
        db, username="vecino", password=TEST_PASSWORD, institution=institution, grade="8", group_code="A"
    )
    await db.commit()
    victim = (await client.post("/api/v1/sessions", json={}, headers=await login("vecino"))).json()["id"]
    attacker = await login(world.student_username)
    task_id = catalog["A-NUM-01"]
    probes = [
        ("GET", f"/api/v1/sessions/{victim}"),
        ("GET", f"/api/v1/sessions/{victim}/interactions"),
        ("GET", f"/api/v1/sessions/{victim}/responses"),
        ("GET", f"/api/v1/sessions/{victim}/teacher-messages"),
        ("POST", f"/api/v1/sessions/{victim}/events"),
        ("POST", f"/api/v1/sessions/{victim}/help"),
        ("GET", f"/api/v1/student-state/{other.id}"),
        ("GET", "/api/v1/research/participants"),
        ("GET", "/api/v1/research/episodes"),
        ("GET", "/api/v1/ai/interactions"),
        ("GET", "/api/v1/tutor-rules"),
        ("GET", "/api/v1/catalog/tasks"),  # contiene soluciones
    ]
    for method, path in probes:
        body = {"event_type": "TASK_OPENED", "task_id": task_id} if path.endswith("/events") else {"task_id": task_id}
        response = await (
            client.post(path, json=body, headers=attacker) if method == "POST" else client.get(path, headers=attacker)
        )
        assert response.status_code in (403, 404), (path, response.status_code)


async def test_admin_anonymization_keeps_pseudonymized_research_data(
    client: httpx.AsyncClient, world: SeededWorld, login: LoginFn, catalog: dict[str, str], db: AsyncSession
) -> None:
    student = await login(world.student_username)
    await client.post("/api/v1/sessions", json={}, headers=student)
    admin = await login(world.admin_email)
    listing = await client.get("/api/v1/admin/users", headers=admin)
    assert listing.status_code == 200
    user_id = await db.scalar(select(Student.user_id).where(Student.id == uuid.UUID(world.student_id)))
    anonymized = await client.post(f"/api/v1/admin/users/{user_id}/anonymize", headers=admin)
    assert anonymized.status_code == 200, anonymized.text
    body = anonymized.json()
    assert body["email"] is None and body["username"].startswith("anon-") and body["status"] == "DISABLED"
    assert body["display_code"] == world.student_participant_code
    assert (
        await client.post("/api/v1/auth/login", json={"identifier": world.student_username, "password": TEST_PASSWORD})
    ).status_code == 401
    researcher = await login(world.researcher_email)
    sessions = (await client.get("/api/v1/sessions", headers=researcher)).json()
    assert sessions and sessions[0]["participant_code"] == world.student_participant_code
    actions = set((await db.execute(select(AuditLog.action))).scalars())
    assert {"PII_ACCESSED", "USER_UPDATED"} <= actions
    self_anon = await client.post(
        f"/api/v1/admin/users/{await db.scalar(select(User.id).where(User.email == world.admin_email))}/anonymize",
        headers=admin,
    )
    assert self_anon.status_code == 400


async def test_retention_anonymizes_inactive_accounts_only(world: SeededWorld, db: AsyncSession) -> None:
    from app.seed.demo import create_student

    institution = await db.get(Institution, uuid.UUID(world.institution_id))
    assert institution is not None
    institution.retention_days = 30
    recent = await create_student(
        db, username="reciente", password=TEST_PASSWORD, institution=institution, grade="7", group_code="B"
    )
    await db.execute(text("UPDATE identity.users SET created_at = now() - interval '200 days' WHERE username = 'stu1'"))
    await db.commit()
    preview = await apply_retention(db, dry_run=True)
    assert len(preview) == 1
    await db.rollback()
    affected = await apply_retention(db)
    await db.commit()
    assert len(affected) == 1
    stu1 = await db.scalar(
        select(User).join(Student, Student.user_id == User.id).where(Student.id == uuid.UUID(world.student_id))
    )
    assert stu1 is not None and stu1.status == "DISABLED" and stu1.username and stu1.username.startswith("anon-")
    kept = await db.get(User, recent.user_id)
    assert kept is not None and kept.username == "reciente"


async def test_error_responses_never_leak_internals(client: httpx.AsyncClient, world: SeededWorld) -> None:
    response = await client.get("/api/v1/sessions/not-a-uuid", headers={"Authorization": "Bearer x"})
    assert response.status_code in (401, 422)
    assert "Traceback" not in response.text and "sqlalchemy" not in response.text.lower()
    assert response.headers["X-Content-Type-Options"] == "nosniff"
