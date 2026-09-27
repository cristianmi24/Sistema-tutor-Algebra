"""Servicios de identidad: registro, autenticación, tokens, recuperación y consentimiento."""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Any

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import CurrentUser, build_current_user, load_user
from app.core.config import Settings
from app.core.errors import AppError, ConflictError, NotFoundError, UnauthorizedError
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    generate_opaque_token,
    hash_password,
    hash_token,
    utcnow,
    verify_password,
)
from app.modules.common.enums import (
    AuditAction,
    AuditOutcome,
    ConsentParty,
    ConsentStatus,
    LegalDocumentKind,
    Role,
    UserStatus,
)
from app.modules.identity.email import EmailMessage, EmailSender
from app.modules.identity.models import (
    Consent,
    Institution,
    LegalDocument,
    PasswordResetToken,
    RefreshToken,
    Researcher,
    Student,
    Teacher,
    TeacherGroupAssignment,
    User,
)
from app.modules.identity.schemas import (
    ConsentIn,
    RegisterStudentRequest,
    StaffUserCreate,
    UserSummary,
)
from app.modules.ops.audit import record_audit

RESEARCH_ELIGIBLE = "ELIGIBLE"
RESEARCH_PENDING = "PENDING"
RESEARCH_EXCLUDED = "EXCLUDED"


class InvalidCredentialsError(UnauthorizedError):
    code = "INVALID_CREDENTIALS"


class AccountLockedError(AppError):
    status_code = 423
    code = "ACCOUNT_LOCKED"


class ConsentVersionError(AppError):
    code = "CONSENT_VERSION_MISMATCH"


# --------------------------------------------------------------------------- helpers


def user_summary(user: User) -> UserSummary:
    student = user.student_profile
    teacher = user.teacher_profile
    researcher = user.researcher_profile
    display_code = (
        student.participant_code
        if student
        else teacher.display_code
        if teacher
        else researcher.display_code
        if researcher
        else "ADM"
    )
    return UserSummary(
        id=user.id,
        role=Role(user.role),
        status=user.status,
        display_code=display_code,
        institution_id=user.institution_id,
        email=user.email,
        username=user.username,
        grade=student.grade if student else None,
        group_code=student.group_code if student else None,
        research_status=student.research_status if student else None,
    )


async def get_current_legal_versions(db: AsyncSession, settings: Settings) -> dict[str, str]:
    """Versión vigente por tipo de documento (BD primero; configuración como respaldo)."""
    result = await db.execute(select(LegalDocument).where(LegalDocument.is_current.is_(True)))
    versions = {settings.privacy_policy_version: None, settings.terms_version: None}  # placeholder
    current = {
        LegalDocumentKind.PRIVACY_POLICY.value: settings.privacy_policy_version,
        LegalDocumentKind.TERMS.value: settings.terms_version,
    }
    for doc in result.scalars():
        current[doc.kind] = doc.version
    del versions
    return current


async def next_code(
    db: AsyncSession, model: type[Student] | type[Teacher], institution_id: uuid.UUID, prefix: str
) -> str:
    count = await db.scalar(select(func.count()).select_from(model).where(model.institution_id == institution_id))
    return f"{prefix}-{(count or 0) + 1:03d}"


def required_parties(institution: Institution) -> list[str]:
    policy = institution.consent_policy or {}
    parties = policy.get("required_parties")
    if isinstance(parties, list) and parties:
        return [str(p) for p in parties]
    return [ConsentParty.STUDENT.value]


async def compute_research_status(db: AsyncSession, student: Student, institution: Institution) -> str:
    result = await db.execute(select(Consent).where(Consent.user_id == student.user_id))
    consents = list(result.scalars())
    accepted = {c.consent_party for c in consents if c.consent_status == ConsentStatus.ACCEPTED.value}
    declined_or_revoked = {
        c.consent_party
        for c in consents
        if c.consent_status in (ConsentStatus.DECLINED.value, ConsentStatus.REVOKED.value)
    }
    needed = set(required_parties(institution))
    if needed & (declined_or_revoked - accepted):
        return RESEARCH_EXCLUDED
    if needed <= accepted:
        return RESEARCH_ELIGIBLE
    return RESEARCH_PENDING


# --------------------------------------------------------------------------- registro


async def register_student(
    db: AsyncSession,
    settings: Settings,
    payload: RegisterStudentRequest,
    request: Request | None,
) -> tuple[User, Student]:
    institution = await db.scalar(
        select(Institution).where(Institution.code == payload.institution_code, Institution.is_active.is_(True))
    )
    if institution is None:
        raise NotFoundError("La institución indicada no existe o no está activa.")

    current = await get_current_legal_versions(db, settings)
    for consent in payload.consents:
        if (
            consent.privacy_policy_version != current[LegalDocumentKind.PRIVACY_POLICY.value]
            or consent.terms_version != current[LegalDocumentKind.TERMS.value]
        ):
            raise ConsentVersionError(
                "La versión aceptada de la política o los términos no es la vigente.",
                details={"current": current},
            )

    is_email = "@" in payload.identifier
    exists = await db.scalar(
        select(User.id).where(
            (func.lower(User.email) == payload.identifier) if is_email else (User.username == payload.identifier)
        )
    )
    if exists:
        raise ConflictError("Ya existe una cuenta con ese identificador.")

    user = User(
        institution_id=institution.id,
        email=payload.identifier if is_email else None,
        username=None if is_email else payload.identifier,
        password_hash=hash_password(payload.password),
        role=Role.STUDENT.value,
        status=UserStatus.ACTIVE.value,
        password_changed_at=utcnow(),
    )
    db.add(user)
    await db.flush()

    student = Student(
        user_id=user.id,
        institution_id=institution.id,
        participant_code=await next_code(db, Student, institution.id, "STU"),
        grade=payload.grade.value,
        group_code=payload.group_code,
        birth_year=payload.birth_year,
        research_status=RESEARCH_PENDING,
    )
    db.add(student)
    await db.flush()

    for consent in payload.consents:
        await _add_consent(db, user.id, consent, request)
    student.research_status = await compute_research_status(db, student, institution)
    if student.research_status != RESEARCH_ELIGIBLE:
        user.status = UserStatus.PENDING_CONSENT.value

    await record_audit(
        db,
        action=AuditAction.USER_CREATED,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=user.id,
        actor_role=Role.STUDENT.value,
        resource_type="user",
        resource_id=user.id,
        details={"participant_code": student.participant_code, "self_registration": True},
        request=request,
    )
    await db.flush()
    await db.refresh(user, attribute_names=["student_profile"])
    return user, student


async def _add_consent(db: AsyncSession, user_id: uuid.UUID, consent: ConsentIn, request: Request | None) -> Consent:
    from app.modules.ops.audit import client_context

    ctx = client_context(request)
    evidence: dict[str, Any] = {"method": "web_form", **ctx}
    if consent.guardian_reference:
        evidence["guardian_reference"] = consent.guardian_reference
    row = Consent(
        user_id=user_id,
        consent_party=consent.party.value,
        privacy_policy_version=consent.privacy_policy_version,
        terms_version=consent.terms_version,
        consent_status=consent.status,
        accepted_at=utcnow() if consent.status == "ACCEPTED" else None,
        evidence=evidence,
    )
    db.add(row)
    await record_audit(
        db,
        action=AuditAction.CONSENT_RECORDED,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=user_id,
        resource_type="consent",
        resource_id=user_id,
        details={"party": consent.party.value, "status": consent.status},
        request=request,
    )
    await db.flush()  # autoflush está desactivado: hacer visible el consentimiento a las consultas
    return row


async def record_consent(
    db: AsyncSession,
    settings: Settings,
    *,
    target_user: User,
    consent: ConsentIn,
    actor: CurrentUser | None,
    request: Request | None,
) -> tuple[Consent, str | None]:
    current = await get_current_legal_versions(db, settings)
    if (
        consent.privacy_policy_version != current[LegalDocumentKind.PRIVACY_POLICY.value]
        or consent.terms_version != current[LegalDocumentKind.TERMS.value]
    ):
        raise ConsentVersionError("La versión aceptada no es la vigente.", details={"current": current})
    row = await _add_consent(db, target_user.id, consent, request)
    if actor is not None:
        row.evidence = {
            **row.evidence,
            "recorded_by_role": actor.role.value,
            "recorded_by": str(actor.id),
        }
    research_status: str | None = None
    student = await db.scalar(
        select(Student).options(selectinload(Student.user)).where(Student.user_id == target_user.id)
    )
    if student is not None:
        institution = await db.get(Institution, student.institution_id)
        assert institution is not None
        student.research_status = await compute_research_status(db, student, institution)
        research_status = student.research_status
        target_user.status = (
            UserStatus.ACTIVE.value
            if research_status == RESEARCH_ELIGIBLE
            else UserStatus.PENDING_CONSENT.value
            if target_user.status in (UserStatus.ACTIVE.value, UserStatus.PENDING_CONSENT.value)
            else target_user.status
        )
    await db.flush()
    return row, research_status


async def revoke_consent(
    db: AsyncSession,
    *,
    target_user: User,
    party: ConsentParty,
    actor: CurrentUser,
    request: Request | None,
) -> str | None:
    result = await db.execute(
        select(Consent).where(
            Consent.user_id == target_user.id,
            Consent.consent_party == party.value,
            Consent.consent_status == ConsentStatus.ACCEPTED.value,
        )
    )
    now = utcnow()
    for row in result.scalars():
        row.consent_status = ConsentStatus.REVOKED.value
        row.revoked_at = now
    await record_audit(
        db,
        action=AuditAction.CONSENT_REVOKED,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=actor.id,
        actor_role=actor.role.value,
        resource_type="consent",
        resource_id=target_user.id,
        details={"party": party.value},
        request=request,
    )
    student = await db.scalar(select(Student).where(Student.user_id == target_user.id))
    if student is None:
        return None
    institution = await db.get(Institution, student.institution_id)
    assert institution is not None
    student.research_status = await compute_research_status(db, student, institution)
    return student.research_status


# --------------------------------------------------------------------------- login / tokens


async def _find_user_by_identifier(db: AsyncSession, identifier: str) -> User | None:
    ident = identifier.strip().lower()
    stmt = (
        select(User)
        .options(
            selectinload(User.student_profile),
            selectinload(User.teacher_profile),
            selectinload(User.researcher_profile),
        )
        .where((func.lower(User.email) == ident) | (User.username == ident))
    )
    return await db.scalar(stmt)


async def issue_tokens(
    db: AsyncSession,
    settings: Settings,
    user: User,
    *,
    family_id: uuid.UUID | None = None,
    request: Request | None,
) -> tuple[str, int, str, RefreshToken]:
    family = family_id or uuid.uuid4()
    access, expires_at = create_access_token(settings, user_id=user.id, role=user.role, session_family_id=family)
    raw_refresh = generate_opaque_token()
    from app.modules.ops.audit import client_context

    ctx = client_context(request)
    refresh = RefreshToken(
        user_id=user.id,
        family_id=family,
        token_hash=hash_token(raw_refresh),
        expires_at=utcnow() + timedelta(days=settings.refresh_token_expire_days),
        user_agent=ctx["user_agent"],
        ip_truncated=ctx["ip_truncated"],
    )
    db.add(refresh)
    await db.flush()
    expires_in = int((expires_at - utcnow()).total_seconds())
    return access, expires_in, raw_refresh, refresh


async def login(
    db: AsyncSession, settings: Settings, *, identifier: str, password: str, request: Request | None
) -> tuple[User, str, int, str]:
    user = await _find_user_by_identifier(db, identifier)
    now = utcnow()

    if user is None:
        # Igualar tiempo de respuesta y auditar sin revelar existencia.
        verify_password(password, DUMMY_PASSWORD_HASH)
        await record_audit(
            db,
            action=AuditAction.LOGIN_FAILED,
            outcome=AuditOutcome.FAILURE,
            details={"reason": "unknown_identifier"},
            request=request,
        )
        await db.commit()  # los registros de seguridad persisten aunque la respuesta sea un error
        raise InvalidCredentialsError("Credenciales inválidas.")

    if user.status == UserStatus.DISABLED.value:
        verify_password(password, DUMMY_PASSWORD_HASH)
        await record_audit(
            db,
            action=AuditAction.LOGIN_FAILED,
            outcome=AuditOutcome.DENIED,
            actor_user_id=user.id,
            actor_role=user.role,
            details={"reason": "disabled"},
            request=request,
        )
        await db.commit()
        raise InvalidCredentialsError("Credenciales inválidas.")

    if user.locked_until is not None and user.locked_until > now:
        await record_audit(
            db,
            action=AuditAction.LOGIN_FAILED,
            outcome=AuditOutcome.DENIED,
            actor_user_id=user.id,
            actor_role=user.role,
            details={"reason": "locked"},
            request=request,
        )
        await db.commit()
        raise AccountLockedError(
            "La cuenta está bloqueada temporalmente. Inténtalo más tarde.",
            details={"locked_until": user.locked_until.isoformat()},
        )

    valid, needs_rehash = verify_password(password, user.password_hash)
    if not valid:
        user.failed_login_attempts += 1
        details: dict[str, Any] = {"reason": "bad_password", "attempts": user.failed_login_attempts}
        if user.failed_login_attempts >= settings.login_max_failed_attempts:
            user.locked_until = now + timedelta(minutes=settings.login_lockout_minutes)
            user.failed_login_attempts = 0
            await record_audit(
                db,
                action=AuditAction.ACCOUNT_LOCKED,
                outcome=AuditOutcome.SUCCESS,
                actor_user_id=user.id,
                actor_role=user.role,
                details={"locked_until": user.locked_until.isoformat()},
                request=request,
            )
        await record_audit(
            db,
            action=AuditAction.LOGIN_FAILED,
            outcome=AuditOutcome.FAILURE,
            actor_user_id=user.id,
            actor_role=user.role,
            details=details,
            request=request,
        )
        await db.commit()
        raise InvalidCredentialsError("Credenciales inválidas.")

    if needs_rehash:
        user.password_hash = hash_password(password)
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    if user.status == UserStatus.LOCKED.value:
        user.status = UserStatus.ACTIVE.value

    access, expires_in, raw_refresh, _ = await issue_tokens(db, settings, user, request=request)
    await record_audit(
        db,
        action=AuditAction.LOGIN_SUCCESS,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=user.id,
        actor_role=user.role,
        request=request,
    )
    return user, access, expires_in, raw_refresh


async def refresh_session(
    db: AsyncSession, settings: Settings, *, raw_refresh: str | None, request: Request | None
) -> tuple[User, str, int, str]:
    if not raw_refresh:
        raise UnauthorizedError("No hay sesión que renovar.")
    token_hash = hash_token(raw_refresh)
    stored = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    now = utcnow()
    if stored is None:
        raise UnauthorizedError("La sesión no es válida.")

    if stored.revoked_at is not None or stored.rotated_to is not None:
        # Reuso de un token ya rotado/revocado ⇒ posible robo: revocar toda la familia.
        await revoke_family(db, stored.family_id, reason="reuse_detected")
        await record_audit(
            db,
            action=AuditAction.TOKEN_REUSE_DETECTED,
            outcome=AuditOutcome.DENIED,
            actor_user_id=stored.user_id,
            resource_type="refresh_family",
            resource_id=stored.family_id,
            request=request,
        )
        await db.commit()
        raise UnauthorizedError("La sesión fue invalidada por seguridad. Inicia sesión de nuevo.")

    if stored.expires_at <= now:
        stored.revoked_at = now
        stored.revoked_reason = "expired"
        await db.commit()
        raise UnauthorizedError("La sesión expiró.")

    user = await load_user(db, stored.user_id)
    if user is None or user.status in (UserStatus.DISABLED.value, UserStatus.LOCKED.value):
        await revoke_family(db, stored.family_id, reason="account_unavailable")
        await db.commit()
        raise UnauthorizedError("La cuenta no está disponible.")

    access, expires_in, new_raw, new_row = await issue_tokens(
        db, settings, user, family_id=stored.family_id, request=request
    )
    stored.rotated_to = new_row.id
    stored.revoked_at = now
    stored.revoked_reason = "rotated"
    await record_audit(
        db,
        action=AuditAction.TOKEN_REFRESHED,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=user.id,
        actor_role=user.role,
        resource_type="refresh_family",
        resource_id=stored.family_id,
        request=request,
    )
    return user, access, expires_in, new_raw


async def revoke_family(db: AsyncSession, family_id: uuid.UUID, *, reason: str) -> int:
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
    )
    now = utcnow()
    count = 0
    for token in result.scalars():
        token.revoked_at = now
        token.revoked_reason = reason
        count += 1
    return count


async def revoke_all_user_tokens(db: AsyncSession, user_id: uuid.UUID, *, reason: str) -> int:
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
    )
    now = utcnow()
    count = 0
    for token in result.scalars():
        token.revoked_at = now
        token.revoked_reason = reason
        count += 1
    return count


async def logout(db: AsyncSession, user: CurrentUser, *, raw_refresh: str | None, request: Request | None) -> None:
    family_id = user.session_family_id
    if raw_refresh:
        stored = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw_refresh)))
        if stored is not None and stored.user_id == user.id:
            family_id = stored.family_id
    await revoke_family(db, family_id, reason="logout")
    await record_audit(
        db,
        action=AuditAction.LOGOUT,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=user.id,
        actor_role=user.role.value,
        request=request,
    )


# --------------------------------------------------------------------------- recuperación


async def request_password_reset(
    db: AsyncSession,
    settings: Settings,
    email_sender: EmailSender,
    *,
    email: str,
    request: Request | None,
) -> None:
    """Siempre responde igual (anti-enumeración). Envía enlace solo si procede."""
    user = await _find_user_by_identifier(db, email)
    if user is None or user.role not in settings.password_reset_roles or user.email is None:
        await record_audit(
            db,
            action=AuditAction.PASSWORD_RESET_REQUESTED,
            outcome=AuditOutcome.FAILURE,
            details={"reason": "not_applicable"},
            request=request,
        )
        return
    raw = generate_opaque_token()
    from app.modules.ops.audit import client_context

    row = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_token(raw),
        expires_at=utcnow() + timedelta(minutes=settings.password_reset_token_expire_minutes),
        requested_ip_truncated=client_context(request)["ip_truncated"],
    )
    db.add(row)
    await record_audit(
        db,
        action=AuditAction.PASSWORD_RESET_REQUESTED,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=user.id,
        actor_role=user.role,
        request=request,
    )
    link = f"{settings.frontend_base_url.rstrip('/')}/reset-password?token={raw}"
    await email_sender.send(
        EmailMessage(
            to=user.email,
            subject="Restablecer tu contraseña — STI-GA",
            body_text=(
                "Recibimos una solicitud para restablecer tu contraseña.\n"
                f"Abre este enlace (válido {settings.password_reset_token_expire_minutes} minutos):\n{link}\n\n"
                "Si no fuiste tú, ignora este mensaje."
            ),
        )
    )


async def reset_password(db: AsyncSession, *, token: str, new_password: str, request: Request | None) -> None:
    row = await db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_token(token)))
    now = utcnow()
    if row is None or row.used_at is not None or row.expires_at <= now:
        await record_audit(
            db,
            action=AuditAction.PASSWORD_RESET,
            outcome=AuditOutcome.FAILURE,
            details={"reason": "invalid_or_expired_token"},
            request=request,
        )
        await db.commit()
        raise AppError(
            "El enlace no es válido o expiró. Solicita uno nuevo.",
            details={"code": "RESET_TOKEN_INVALID"},
        )
    user = await db.get(User, row.user_id)
    if user is None:
        raise AppError("El enlace no es válido.")
    user.password_hash = hash_password(new_password)
    user.password_changed_at = now
    user.failed_login_attempts = 0
    user.locked_until = None
    row.used_at = now
    await revoke_all_user_tokens(db, user.id, reason="password_reset")
    await record_audit(
        db,
        action=AuditAction.PASSWORD_RESET,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=user.id,
        actor_role=user.role,
        request=request,
    )


async def change_password(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    current_password: str,
    new_password: str,
    request: Request | None,
) -> None:
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("Usuario no encontrado.")
    valid, _ = verify_password(current_password, user.password_hash)
    if not valid:
        raise InvalidCredentialsError("La contraseña actual no es correcta.")
    user.password_hash = hash_password(new_password)
    user.password_changed_at = utcnow()
    await revoke_all_user_tokens(db, user.id, reason="password_changed")
    await record_audit(
        db,
        action=AuditAction.PASSWORD_CHANGED,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=user.id,
        actor_role=user.role,
        request=request,
    )


# --------------------------------------------------------------------------- administración


async def create_staff_user(
    db: AsyncSession, payload: StaffUserCreate, *, actor: CurrentUser, request: Request | None
) -> User:
    institution: Institution | None = None
    if payload.institution_code:
        institution = await db.scalar(select(Institution).where(Institution.code == payload.institution_code))
        if institution is None:
            raise NotFoundError("La institución indicada no existe.")
    if payload.role in ("TEACHER",) and institution is None:
        raise AppError("Un docente requiere institución.")
    email = payload.email.lower()
    if await db.scalar(select(User.id).where(func.lower(User.email) == email)):
        raise ConflictError("Ya existe una cuenta con ese correo.")

    user = User(
        institution_id=institution.id if institution else None,
        email=email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        status=UserStatus.ACTIVE.value,
        password_changed_at=utcnow(),
    )
    db.add(user)
    await db.flush()

    if payload.role == "TEACHER" and institution is not None:
        teacher = Teacher(
            user_id=user.id,
            institution_id=institution.id,
            display_code=await next_code(db, Teacher, institution.id, "TEA"),
        )
        db.add(teacher)
        await db.flush()
        for assignment in payload.group_assignments:
            db.add(
                TeacherGroupAssignment(
                    teacher_id=teacher.id,
                    institution_id=institution.id,
                    grade=assignment.grade.value,
                    group_code=assignment.group_code,
                )
            )
    elif payload.role == "RESEARCHER":
        count = await db.scalar(select(func.count()).select_from(Researcher))
        db.add(
            Researcher(
                user_id=user.id,
                institution_id=institution.id if institution else None,
                display_code=f"RES-{(count or 0) + 1:03d}",
            )
        )
    await record_audit(
        db,
        action=AuditAction.USER_CREATED,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=actor.id,
        actor_role=actor.role.value,
        resource_type="user",
        resource_id=user.id,
        details={"role": payload.role},
        request=request,
    )
    await db.flush()
    loaded = await load_user(db, user.id)
    assert loaded is not None
    return loaded


async def set_user_status(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    status: str,
    actor: CurrentUser,
    request: Request | None,
) -> User:
    user = await load_user(db, user_id)
    if user is None:
        raise NotFoundError("Usuario no encontrado.")
    if user.id == actor.id and status == UserStatus.DISABLED.value:
        raise AppError("No puedes deshabilitar tu propia cuenta.")
    user.status = status
    if status == UserStatus.DISABLED.value:
        await revoke_all_user_tokens(db, user.id, reason="disabled")
    await record_audit(
        db,
        action=AuditAction.USER_DISABLED if status == UserStatus.DISABLED.value else AuditAction.USER_UPDATED,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=actor.id,
        actor_role=actor.role.value,
        resource_type="user",
        resource_id=user.id,
        details={"status": status},
        request=request,
    )
    return user


def current_user_from_model(user: User, family_id: uuid.UUID) -> CurrentUser:
    return build_current_user(user, family_id)
