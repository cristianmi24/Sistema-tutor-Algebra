"""Consentimientos: consulta propia y registro de partes adicionales (acudiente, institución)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Request, status
from sqlalchemy import select

from app.core.auth import AnyUserDep, CurrentUserDep
from app.core.deps import DbDep, SettingsDep
from app.core.errors import ForbiddenError, NotFoundError
from app.modules.common.enums import ConsentParty, ConsentStatus, Role
from app.modules.identity import service
from app.modules.identity.models import Consent, Student, User
from app.modules.identity.schemas import ConsentOut, ConsentRecordRequest

router = APIRouter()


def _to_out(row: Consent) -> ConsentOut:
    return ConsentOut(
        id=row.id,
        user_id=row.user_id,
        consent_party=ConsentParty(row.consent_party),
        consent_status=ConsentStatus(row.consent_status),
        privacy_policy_version=row.privacy_policy_version,
        terms_version=row.terms_version,
        accepted_at=row.accepted_at,
        revoked_at=row.revoked_at,
        created_at=row.created_at,
    )


@router.get("/me", response_model=list[ConsentOut], summary="Mis consentimientos")
async def my_consents(user: AnyUserDep, db: DbDep) -> list[ConsentOut]:
    rows = (await db.execute(select(Consent).where(Consent.user_id == user.id).order_by(Consent.created_at))).scalars()
    return [_to_out(r) for r in rows]


async def _resolve_target(db: DbDep, payload: ConsentRecordRequest, actor: CurrentUserDep) -> User:
    if payload.user_id is not None:
        user = await db.get(User, payload.user_id)
    else:
        student = await db.scalar(select(Student).where(Student.participant_code == payload.participant_code))
        user = await db.get(User, student.user_id) if student else None
    if user is None:
        raise NotFoundError("Participante no encontrado.")
    same_institution = actor.institution_id is not None and actor.institution_id == user.institution_id
    if actor.role == Role.STUDENT and user.id != actor.id:
        raise ForbiddenError("Solo puedes registrar consentimientos sobre tu propia cuenta.")
    if actor.role in (Role.TEACHER, Role.RESEARCHER) and not same_institution:
        raise ForbiddenError("El participante no pertenece a tu institución.")
    return user


@router.post(
    "",
    response_model=ConsentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar consentimiento (estudiante, acudiente, institución, investigador)",
)
async def record(
    request: Request,
    payload: ConsentRecordRequest,
    actor: AnyUserDep,
    db: DbDep,
    settings: SettingsDep,
) -> ConsentOut:
    target = await _resolve_target(db, payload, actor)
    if actor.role == Role.STUDENT and payload.consent.party not in (
        ConsentParty.STUDENT,
        ConsentParty.GUARDIAN,
    ):
        raise ForbiddenError("Un estudiante solo puede registrar su consentimiento o el de su acudiente.")
    row, _ = await service.record_consent(
        db, settings, target_user=target, consent=payload.consent, actor=actor, request=request
    )
    return _to_out(row)


@router.post(
    "/revoke/{party}",
    response_model=dict[str, str | None],
    summary="Revocar consentimiento de una parte (propio o por personal autorizado)",
)
async def revoke(
    request: Request,
    party: ConsentParty,
    actor: AnyUserDep,
    db: DbDep,
    user_id: uuid.UUID | None = None,
) -> dict[str, str | None]:
    target_id = user_id or actor.id
    if target_id != actor.id and actor.role not in (Role.ADMIN, Role.RESEARCHER):
        raise ForbiddenError("No puedes revocar consentimientos de otra persona.")
    target = await db.get(User, target_id)
    if target is None:
        raise NotFoundError("Usuario no encontrado.")
    research_status = await service.revoke_consent(db, target_user=target, party=party, actor=actor, request=request)
    return {"research_status": research_status}
