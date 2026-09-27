"""Administración: usuarios, instituciones y auditoría (solo ADMIN)."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.auth import AdminDep
from app.core.deps import DbDep
from app.core.errors import ConflictError, NotFoundError
from app.modules.common.enums import AuditAction, AuditOutcome, Role
from app.modules.identity import service
from app.modules.identity.models import Institution, User
from app.modules.identity.schemas import (
    AuditLogOut,
    InstitutionIn,
    InstitutionOut,
    Page,
    StaffUserCreate,
    UserStatusUpdate,
    UserSummary,
)
from app.modules.ops.audit import record_audit
from app.modules.ops.models import AuditLog

router = APIRouter()


def _institution_out(i: Institution) -> InstitutionOut:
    return InstitutionOut(
        id=i.id,
        code=i.code,
        name=i.name,
        country=i.country,
        city=i.city,
        consent_policy=i.consent_policy,
        retention_days=i.retention_days,
        is_active=i.is_active,
    )


# ----------------------------------------------------------------- instituciones


@router.get("/institutions", response_model=list[InstitutionOut])
async def list_institutions(_: AdminDep, db: DbDep) -> list[InstitutionOut]:
    rows = (await db.execute(select(Institution).order_by(Institution.code))).scalars()
    return [_institution_out(i) for i in rows]


@router.post("/institutions", response_model=InstitutionOut, status_code=status.HTTP_201_CREATED)
async def create_institution(request: Request, payload: InstitutionIn, admin: AdminDep, db: DbDep) -> InstitutionOut:
    if await db.scalar(select(Institution.id).where(Institution.code == payload.code)):
        raise ConflictError("Ya existe una institución con ese código.")
    row = Institution(**payload.model_dump())
    db.add(row)
    await db.flush()
    await record_audit(
        db,
        action=AuditAction.SETTINGS_UPDATED,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=admin.id,
        actor_role=admin.role.value,
        resource_type="institution",
        resource_id=row.id,
        details={"created": payload.code},
        request=request,
    )
    return _institution_out(row)


@router.put("/institutions/{institution_id}", response_model=InstitutionOut)
async def update_institution(
    request: Request, institution_id: uuid.UUID, payload: InstitutionIn, admin: AdminDep, db: DbDep
) -> InstitutionOut:
    row = await db.get(Institution, institution_id)
    if row is None:
        raise NotFoundError("Institución no encontrada.")
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    await record_audit(
        db,
        action=AuditAction.SETTINGS_UPDATED,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=admin.id,
        actor_role=admin.role.value,
        resource_type="institution",
        resource_id=row.id,
        details={"updated": payload.code},
        request=request,
    )
    return _institution_out(row)


# ----------------------------------------------------------------- usuarios


@router.get("/users", response_model=Page[UserSummary])
async def list_users(
    _: AdminDep,
    db: DbDep,
    role: Role | None = None,
    institution_id: uuid.UUID | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> Page[UserSummary]:
    stmt = select(User).options(
        selectinload(User.student_profile),
        selectinload(User.teacher_profile),
        selectinload(User.researcher_profile),
    )
    count_stmt = select(func.count()).select_from(User)
    if role is not None:
        stmt = stmt.where(User.role == role.value)
        count_stmt = count_stmt.where(User.role == role.value)
    if institution_id is not None:
        stmt = stmt.where(User.institution_id == institution_id)
        count_stmt = count_stmt.where(User.institution_id == institution_id)
    total = await db.scalar(count_stmt) or 0
    rows = (
        await db.execute(stmt.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size))
    ).scalars()
    return Page(items=[service.user_summary(u) for u in rows], page=page, page_size=page_size, total=total)


@router.post("/users", response_model=UserSummary, status_code=status.HTTP_201_CREATED)
async def create_user(request: Request, payload: StaffUserCreate, admin: AdminDep, db: DbDep) -> UserSummary:
    user = await service.create_staff_user(db, payload, actor=admin, request=request)
    return service.user_summary(user)


@router.patch("/users/{user_id}/status", response_model=UserSummary)
async def update_status(
    request: Request, user_id: uuid.UUID, payload: UserStatusUpdate, admin: AdminDep, db: DbDep
) -> UserSummary:
    user = await service.set_user_status(db, user_id=user_id, status=payload.status, actor=admin, request=request)
    return service.user_summary(user)


# ----------------------------------------------------------------- auditoría


@router.get("/audit", response_model=Page[AuditLogOut])
async def audit(
    _: AdminDep,
    db: DbDep,
    action: str | None = Query(default=None, max_length=64),
    actor_user_id: uuid.UUID | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> Page[AuditLogOut]:
    stmt = select(AuditLog)
    count_stmt = select(func.count()).select_from(AuditLog)
    filters = []
    if action:
        filters.append(AuditLog.action == action)
    if actor_user_id:
        filters.append(AuditLog.actor_user_id == actor_user_id)
    if since:
        filters.append(AuditLog.occurred_at >= since)
    if until:
        filters.append(AuditLog.occurred_at <= until)
    for f in filters:
        stmt = stmt.where(f)
        count_stmt = count_stmt.where(f)
    total = await db.scalar(count_stmt) or 0
    rows = (
        await db.execute(stmt.order_by(AuditLog.occurred_at.desc()).offset((page - 1) * page_size).limit(page_size))
    ).scalars()
    return Page(
        items=[
            AuditLogOut(
                id=r.id,
                occurred_at=r.occurred_at,
                actor_user_id=r.actor_user_id,
                actor_role=r.actor_role,
                action=r.action,
                resource_type=r.resource_type,
                resource_id=r.resource_id,
                outcome=r.outcome,
                request_id=r.request_id,
                details=r.details,
            )
            for r in rows
        ],
        page=page,
        page_size=page_size,
        total=total,
    )
