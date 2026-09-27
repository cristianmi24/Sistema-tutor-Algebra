"""Fase 2: registro con consentimiento, login, bloqueo, refresh rotativo, logout, recuperación, RBAC."""

from __future__ import annotations

import uuid
from datetime import timedelta

import httpx
import jwt
import pytest
from app.core.config import Settings
from app.core.security import create_access_token
from app.modules.identity.models import Consent, RefreshToken, Student, User
from app.modules.ops.models import AuditLog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import TEST_PASSWORD, LoginFn, SeededWorld


def use_refresh_cookie(client: httpx.AsyncClient, value: str) -> None:
    """Envía exactamente esta cookie de refresh (el jar de httpx no casa dominios sin punto)."""
    client.cookies.clear()
    client.headers["Cookie"] = f"sti_refresh={value}"


def register_payload(world: SeededWorld, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "identifier": "nuevo.estudiante",
        "password": "Patrones-Figurales-2026",
        "institution_code": world.institution_code,
        "grade": "8",
        "group_code": "A",
        "birth_year": 2012,
        "consents": [
            {
                "party": "STUDENT",
                "privacy_policy_version": "2026.1",
                "terms_version": "2026.1",
                "status": "ACCEPTED",
            }
        ],
    }
    payload.update(overrides)
    return payload


# ------------------------------------------------------------------------------ registro


async def test_register_student_records_consent_and_pending_research_status(
    client: httpx.AsyncClient, world: SeededWorld, db: AsyncSession
) -> None:
    response = await client.post("/api/v1/auth/register", json=register_payload(world))
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["participant_code"] == "STU-002"
    # La institución exige acudiente: el estudiante puede trabajar, pero no entra a investigación.
    assert body["status"] == "PENDING_CONSENT"
    assert body["research_status"] == "PENDING"

    consents = (await db.execute(select(Consent))).scalars().all()
    assert len(consents) == 1
    assert consents[0].consent_party == "STUDENT"
    assert consents[0].privacy_policy_version == "2026.1"
    assert consents[0].evidence["method"] == "web_form"
    audit_actions = set((await db.execute(select(AuditLog.action))).scalars())
    assert {"USER_CREATED", "CONSENT_RECORDED"} <= audit_actions


async def test_register_rejects_outdated_legal_version(client: httpx.AsyncClient, world: SeededWorld) -> None:
    payload = register_payload(
        world,
        consents=[{"party": "STUDENT", "privacy_policy_version": "2020.1", "terms_version": "2026.1"}],
    )
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "CONSENT_VERSION_MISMATCH"


async def test_register_requires_student_consent_and_strong_password(
    client: httpx.AsyncClient, world: SeededWorld
) -> None:
    weak = await client.post("/api/v1/auth/register", json=register_payload(world, password="12345678"))
    assert weak.status_code == 422
    declined = await client.post(
        "/api/v1/auth/register",
        json=register_payload(
            world,
            consents=[
                {
                    "party": "STUDENT",
                    "privacy_policy_version": "2026.1",
                    "terms_version": "2026.1",
                    "status": "DECLINED",
                }
            ],
        ),
    )
    assert declined.status_code == 422
    extra = await client.post("/api/v1/auth/register", json={**register_payload(world), "role": "ADMIN"})
    assert extra.status_code == 422  # extra="forbid": nadie elige su rol


async def test_register_duplicate_identifier_conflicts(client: httpx.AsyncClient, world: SeededWorld) -> None:
    payload = register_payload(world, identifier=world.student_username)
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409


async def test_guardian_consent_makes_student_eligible(
    client: httpx.AsyncClient, world: SeededWorld, login: LoginFn, db: AsyncSession
) -> None:
    created = await client.post("/api/v1/auth/register", json=register_payload(world))
    user_id = created.json()["user_id"]
    headers = await login("nuevo.estudiante", "Patrones-Figurales-2026")
    response = await client.post(
        "/api/v1/consents",
        json={
            "user_id": user_id,
            "consent": {
                "party": "GUARDIAN",
                "privacy_policy_version": "2026.1",
                "terms_version": "2026.1",
                "guardian_reference": "acudiente firmó formato institucional F-03",
            },
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    student = await db.scalar(select(Student).where(Student.user_id == uuid.UUID(user_id)))
    assert student is not None
    assert student.research_status == "ELIGIBLE"
    user = await db.get(User, uuid.UUID(user_id))
    assert user is not None and user.status == "ACTIVE"

    # Un estudiante no puede registrar consentimientos sobre otra cuenta.
    other = await client.post(
        "/api/v1/consents",
        json={
            "participant_code": world.student_participant_code,
            "consent": {
                "party": "GUARDIAN",
                "privacy_policy_version": "2026.1",
                "terms_version": "2026.1",
            },
        },
        headers=headers,
    )
    assert other.status_code == 403


# ------------------------------------------------------------------------------ login


async def test_login_returns_access_token_and_refresh_cookie(client: httpx.AsyncClient, world: SeededWorld) -> None:
    response = await client.post(
        "/api/v1/auth/login", json={"identifier": world.student_username, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["role"] == "STUDENT"
    assert body["user"]["display_code"] == world.student_participant_code
    cookie = response.headers.get("set-cookie", "")
    assert "sti_refresh=" in cookie
    assert "HttpOnly" in cookie
    assert "Path=/api/v1/auth" in cookie
    assert "SameSite=strict" in cookie.lower() or "samesite=strict" in cookie.lower()
    assert "sti_refresh" not in response.text  # el refresh nunca viaja en el cuerpo


async def test_login_failure_is_uniform_and_locks_after_attempts(
    client: httpx.AsyncClient, world: SeededWorld, db: AsyncSession, settings: Settings
) -> None:
    unknown = await client.post("/api/v1/auth/login", json={"identifier": "nadie@test.edu", "password": "x" * 12})
    wrong = await client.post("/api/v1/auth/login", json={"identifier": world.student_username, "password": "x" * 12})
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["error"]["message"] == wrong.json()["error"]["message"]

    for _ in range(settings.login_max_failed_attempts - 1):
        await client.post("/api/v1/auth/login", json={"identifier": world.student_username, "password": "x" * 12})
    locked = await client.post(
        "/api/v1/auth/login", json={"identifier": world.student_username, "password": TEST_PASSWORD}
    )
    assert locked.status_code == 423
    assert locked.json()["error"]["code"] == "ACCOUNT_LOCKED"
    actions = list((await db.execute(select(AuditLog.action))).scalars())
    assert "ACCOUNT_LOCKED" in actions
    assert actions.count("LOGIN_FAILED") >= settings.login_max_failed_attempts


async def test_disabled_user_cannot_login(
    client: httpx.AsyncClient, world: SeededWorld, login: LoginFn, db: AsyncSession
) -> None:
    admin = await login(world.admin_email)
    student_user_id = await db.scalar(select(Student.user_id).where(Student.id == uuid.UUID(world.student_id)))
    response = await client.patch(
        f"/api/v1/admin/users/{student_user_id}/status", json={"status": "DISABLED"}, headers=admin
    )
    assert response.status_code == 200
    denied = await client.post(
        "/api/v1/auth/login", json={"identifier": world.student_username, "password": TEST_PASSWORD}
    )
    assert denied.status_code == 401


# ------------------------------------------------------------------------------ refresh / logout


async def test_refresh_rotates_and_detects_reuse(
    client: httpx.AsyncClient, world: SeededWorld, db: AsyncSession
) -> None:
    login = await client.post(
        "/api/v1/auth/login", json={"identifier": world.student_username, "password": TEST_PASSWORD}
    )
    first_cookie = login.cookies["sti_refresh"]

    use_refresh_cookie(client, first_cookie)
    refreshed = await client.post("/api/v1/auth/refresh")
    assert refreshed.status_code == 200, refreshed.text
    second_cookie = refreshed.cookies["sti_refresh"]
    assert second_cookie != first_cookie
    assert refreshed.json()["access_token"] != login.json()["access_token"]

    # Reuso del primer token (ya rotado) ⇒ toda la familia queda revocada.
    use_refresh_cookie(client, first_cookie)
    reuse = await client.post("/api/v1/auth/refresh")
    assert reuse.status_code == 401
    use_refresh_cookie(client, second_cookie)
    after = await client.post("/api/v1/auth/refresh")
    assert after.status_code == 401

    tokens = (await db.execute(select(RefreshToken))).scalars().all()
    assert all(t.revoked_at is not None for t in tokens)
    assert "TOKEN_REUSE_DETECTED" in set((await db.execute(select(AuditLog.action))).scalars())


async def test_refresh_without_cookie_is_unauthorized(client: httpx.AsyncClient, world: SeededWorld) -> None:
    response = await client.post("/api/v1/auth/refresh")
    assert response.status_code == 401


async def test_logout_revokes_family_and_clears_cookie(client: httpx.AsyncClient, world: SeededWorld) -> None:
    login = await client.post(
        "/api/v1/auth/login", json={"identifier": world.student_username, "password": TEST_PASSWORD}
    )
    token = login.json()["access_token"]
    cookie = login.cookies["sti_refresh"]
    response = await client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 204
    set_cookie = response.headers.get("set-cookie", "")
    assert 'sti_refresh=""' in set_cookie or "Max-Age=0" in set_cookie
    use_refresh_cookie(client, cookie)
    again = await client.post("/api/v1/auth/refresh")
    assert again.status_code == 401


# ------------------------------------------------------------------------------ recuperación


async def test_forgot_and_reset_password_flow(
    client: httpx.AsyncClient, world: SeededWorld, outbox: list[object], db: AsyncSession
) -> None:
    unknown = await client.post("/api/v1/auth/forgot-password", json={"email": "nadie@test.edu"})
    known = await client.post("/api/v1/auth/forgot-password", json={"email": world.teacher_email})
    assert unknown.status_code == known.status_code == 202
    assert unknown.json() == known.json()  # anti-enumeración
    assert len(outbox) == 1
    body = outbox[0].body_text  # type: ignore[attr-defined]
    assert "?token=" in body and TEST_PASSWORD not in body
    token = body.split("?token=")[1].split()[0]

    bad = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": "x" * 40, "new_password": "Nueva-Clave-Segura-1"},
    )
    assert bad.status_code == 400
    ok = await client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "Nueva-Clave-Segura-1"})
    assert ok.status_code == 204
    reused = await client.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": "Otra-Clave-Segura-2"}
    )
    assert reused.status_code == 400

    old = await client.post("/api/v1/auth/login", json={"identifier": world.teacher_email, "password": TEST_PASSWORD})
    new = await client.post(
        "/api/v1/auth/login",
        json={"identifier": world.teacher_email, "password": "Nueva-Clave-Segura-1"},
    )
    assert old.status_code == 401 and new.status_code == 200
    assert "PASSWORD_RESET" in set((await db.execute(select(AuditLog.action))).scalars())


# ------------------------------------------------------------------------------ RBAC / tokens (casos 11 y 12)


async def test_role_based_access_is_enforced_in_backend(
    client: httpx.AsyncClient, world: SeededWorld, login: LoginFn
) -> None:
    student = await login(world.student_username)
    teacher = await login(world.teacher_email)
    researcher = await login(world.researcher_email)
    admin = await login(world.admin_email)

    for headers in (student, teacher, researcher):
        denied = await client.get("/api/v1/admin/users", headers=headers)
        assert denied.status_code == 403
        assert denied.json()["error"]["code"] == "FORBIDDEN"
    allowed = await client.get("/api/v1/admin/users", headers=admin)
    assert allowed.status_code == 200
    assert allowed.json()["total"] == 4

    anonymous = await client.get("/api/v1/auth/me")
    assert anonymous.status_code == 401
    me = await client.get("/api/v1/auth/me", headers=student)
    assert me.json()["display_code"] == world.student_participant_code
    assert "email" in me.json()


async def test_expired_or_tampered_tokens_are_rejected(
    client: httpx.AsyncClient, world: SeededWorld, settings: Settings, db: AsyncSession
) -> None:
    user_id = await db.scalar(select(Student.user_id).where(Student.id == uuid.UUID(world.student_id)))
    assert user_id is not None
    expired, _ = create_access_token(
        settings,
        user_id=user_id,
        role="STUDENT",
        session_family_id=uuid.uuid4(),
        expires_delta=timedelta(seconds=-5),
    )
    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401
    assert response.json()["error"]["details"] == {"reason": "expired"}

    forged = jwt.encode(
        {
            "sub": str(user_id),
            "role": "ADMIN",
            "sid": uuid.uuid4().hex,
            "jti": "x",
            "iat": 0,
            "exp": 2**31 - 1,
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "typ": "access",
        },
        "wrong-secret-wrong-secret-wrong-secret!!",
        algorithm="HS256",
    )
    forged_response = await client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {forged}"})
    assert forged_response.status_code == 401

    # Token válido pero con rol distinto al real (p.ej. rol cambiado tras emitirlo) ⇒ 401.
    escalated, _ = create_access_token(settings, user_id=user_id, role="ADMIN", session_family_id=uuid.uuid4())
    esc = await client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {escalated}"})
    assert esc.status_code == 401


# ------------------------------------------------------------------------------ administración


async def test_admin_creates_teacher_with_scope_and_audit_is_queryable(
    client: httpx.AsyncClient, world: SeededWorld, login: LoginFn, db: AsyncSession
) -> None:
    admin = await login(world.admin_email)
    created = await client.post(
        "/api/v1/admin/users",
        json={
            "email": "Nueva.Docente@test.edu",
            "password": "Docente-Clave-2026!",
            "role": "TEACHER",
            "institution_code": world.institution_code,
            "group_assignments": [{"grade": "7", "group_code": "B"}],
        },
        headers=admin,
    )
    assert created.status_code == 201, created.text
    assert created.json()["display_code"] == "TEA-002"
    assert created.json()["email"] == "nueva.docente@test.edu"

    audit = await client.get("/api/v1/admin/audit", params={"action": "USER_CREATED"}, headers=admin)
    assert audit.status_code == 200
    assert audit.json()["total"] >= 1
    assert audit.json()["items"][0]["details"]["role"] == "TEACHER"

    total_users = await db.scalar(select(func.count()).select_from(User))
    assert total_users == 5


async def test_legal_documents_and_public_institutions(client: httpx.AsyncClient, world: SeededWorld) -> None:
    docs = await client.get("/api/v1/legal/documents")
    assert docs.status_code == 200
    kinds = {d["kind"] for d in docs.json()}
    assert kinds == {"PRIVACY_POLICY", "TERMS"}
    assert all(d["version"] == "2026.1" for d in docs.json())
    institutions = await client.get("/api/v1/legal/institutions")
    assert institutions.json() == [
        {
            "code": "TEST",
            "name": "Institución de prueba",
            "required_consent_parties": ["STUDENT", "GUARDIAN"],
        }
    ]


@pytest.mark.parametrize("path", ["/api/v1/admin/users", "/api/v1/consents/me", "/api/v1/auth/logout"])
async def test_protected_routes_require_bearer(client: httpx.AsyncClient, world: SeededWorld, path: str) -> None:
    method = client.post if path.endswith("logout") else client.get
    response = await method(path)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
