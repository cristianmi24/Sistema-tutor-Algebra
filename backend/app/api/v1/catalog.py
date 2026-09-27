"""Catálogo pedagógico (ADMIN edita; investigación lee): actividades, ejemplos y banco de andamiajes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Request, status
from sqlalchemy import select

from app.core.auth import AdminDep, ResearchStaffDep
from app.core.deps import DbDep
from app.core.errors import ConflictError, NotFoundError
from app.modules.common.enums import AuditAction, AuditOutcome, ScaffoldType, TaskType
from app.modules.learning.models import Scaffold, Task, WorkedExample
from app.modules.learning.schemas import (
    ScaffoldIn,
    ScaffoldOut,
    TaskAdminOut,
    TaskIn,
    WorkedExampleIn,
    WorkedExampleOut,
)
from app.modules.ops.audit import record_audit

router = APIRouter()


def _task_admin_out(t: Task) -> TaskAdminOut:
    return TaskAdminOut(
        id=t.id,
        code=t.code,
        task_type=TaskType(t.task_type),
        title=t.title,
        skill=t.skill,
        difficulty=t.difficulty,
        grade_min=t.grade_min,
        grade_max=t.grade_max,
        statement=t.statement,
        solution=t.solution,
        related_task_id=t.related_task_id,
        order_index=t.order_index,
        version=t.version,
        is_active=t.is_active,
    )


def _scaffold_out(s: Scaffold) -> ScaffoldOut:
    return ScaffoldOut(
        id=s.id,
        code=s.code,
        scaffold_type=ScaffoldType(s.scaffold_type),
        level=s.level,
        applicable_task_types=list(s.applicable_task_types),
        applicable_skills=list(s.applicable_skills),
        content=s.content,
        version=s.version,
        is_active=s.is_active,
    )


@router.get("/tasks", response_model=list[TaskAdminOut])
async def list_tasks(_: ResearchStaffDep, db: DbDep) -> list[TaskAdminOut]:
    rows = (await db.execute(select(Task).order_by(Task.order_index, Task.code))).scalars()
    return [_task_admin_out(t) for t in rows]


@router.post("/tasks", response_model=TaskAdminOut, status_code=status.HTTP_201_CREATED)
async def create_task(request: Request, payload: TaskIn, admin: AdminDep, db: DbDep) -> TaskAdminOut:
    if await db.scalar(select(Task.id).where(Task.code == payload.code)):
        raise ConflictError("Ya existe una actividad con ese código.")
    related_id: uuid.UUID | None = None
    if payload.related_task_code:
        related_id = await db.scalar(select(Task.id).where(Task.code == payload.related_task_code))
        if related_id is None:
            raise NotFoundError("La actividad relacionada no existe.")
    data = payload.model_dump(exclude={"related_task_code", "task_type"})
    task = Task(task_type=payload.task_type.value, related_task_id=related_id, **data)
    db.add(task)
    await db.flush()
    await record_audit(
        db,
        action=AuditAction.SETTINGS_UPDATED,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=admin.id,
        actor_role=admin.role.value,
        resource_type="task",
        resource_id=task.id,
        details={"created": payload.code},
        request=request,
    )
    return _task_admin_out(task)


@router.put("/tasks/{task_id}", response_model=TaskAdminOut)
async def update_task(
    request: Request, task_id: uuid.UUID, payload: TaskIn, admin: AdminDep, db: DbDep
) -> TaskAdminOut:
    task = await db.get(Task, task_id)
    if task is None:
        raise NotFoundError("Actividad no encontrada.")
    for key, value in payload.model_dump(exclude={"related_task_code", "task_type"}).items():
        setattr(task, key, value)
    task.task_type = payload.task_type.value
    task.version += 1
    await record_audit(
        db,
        action=AuditAction.SETTINGS_UPDATED,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=admin.id,
        actor_role=admin.role.value,
        resource_type="task",
        resource_id=task.id,
        details={"updated": payload.code, "version": task.version},
        request=request,
    )
    return _task_admin_out(task)


@router.post("/worked-examples", response_model=WorkedExampleOut, status_code=status.HTTP_201_CREATED)
async def create_example(request: Request, payload: WorkedExampleIn, admin: AdminDep, db: DbDep) -> WorkedExampleOut:
    task = await db.scalar(select(Task).where(Task.code == payload.task_code))
    if task is None:
        raise NotFoundError("Actividad no encontrada.")
    example = WorkedExample(
        task_id=task.id,
        example_type=payload.example_type.value,
        title=payload.title,
        content=payload.content,
        order_index=payload.order_index,
        is_active=payload.is_active,
    )
    db.add(example)
    await db.flush()
    await record_audit(
        db,
        action=AuditAction.SETTINGS_UPDATED,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=admin.id,
        actor_role=admin.role.value,
        resource_type="worked_example",
        resource_id=example.id,
        details={"task": payload.task_code},
        request=request,
    )
    return WorkedExampleOut(
        id=example.id,
        task_id=example.task_id,
        example_type=payload.example_type,
        title=example.title,
        content=example.content,
        order_index=example.order_index,
    )


@router.get("/scaffolds", response_model=list[ScaffoldOut])
async def list_scaffolds(_: ResearchStaffDep, db: DbDep) -> list[ScaffoldOut]:
    rows = (await db.execute(select(Scaffold).order_by(Scaffold.level, Scaffold.code))).scalars()
    return [_scaffold_out(s) for s in rows]


@router.post("/scaffolds", response_model=ScaffoldOut, status_code=status.HTTP_201_CREATED)
async def create_scaffold(request: Request, payload: ScaffoldIn, admin: AdminDep, db: DbDep) -> ScaffoldOut:
    if await db.scalar(select(Scaffold.id).where(Scaffold.code == payload.code)):
        raise ConflictError("Ya existe un andamiaje con ese código.")
    scaffold = Scaffold(
        code=payload.code,
        scaffold_type=payload.scaffold_type.value,
        level=payload.level,
        applicable_task_types=[t.value for t in payload.applicable_task_types],
        applicable_skills=payload.applicable_skills,
        content=payload.content,
        is_active=payload.is_active,
        reviewed_by=payload.reviewed_by,
    )
    db.add(scaffold)
    await db.flush()
    await record_audit(
        db,
        action=AuditAction.SCAFFOLD_UPDATED,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=admin.id,
        actor_role=admin.role.value,
        resource_type="scaffold",
        resource_id=scaffold.id,
        details={"created": payload.code},
        request=request,
    )
    return _scaffold_out(scaffold)


@router.put("/scaffolds/{scaffold_id}", response_model=ScaffoldOut)
async def update_scaffold(
    request: Request, scaffold_id: uuid.UUID, payload: ScaffoldIn, admin: AdminDep, db: DbDep
) -> ScaffoldOut:
    scaffold = await db.get(Scaffold, scaffold_id)
    if scaffold is None:
        raise NotFoundError("Andamiaje no encontrado.")
    scaffold.code = payload.code
    scaffold.scaffold_type = payload.scaffold_type.value
    scaffold.level = payload.level
    scaffold.applicable_task_types = [t.value for t in payload.applicable_task_types]
    scaffold.applicable_skills = payload.applicable_skills
    scaffold.content = payload.content
    scaffold.is_active = payload.is_active
    scaffold.reviewed_by = payload.reviewed_by
    scaffold.version += 1
    await record_audit(
        db,
        action=AuditAction.SCAFFOLD_UPDATED,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=admin.id,
        actor_role=admin.role.value,
        resource_type="scaffold",
        resource_id=scaffold.id,
        details={"updated": payload.code, "version": scaffold.version},
        request=request,
    )
    return _scaffold_out(scaffold)
