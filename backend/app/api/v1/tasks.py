"""Actividades y ejemplos trabajados (vista del estudiante; sin solución)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.core.auth import AnyUserDep
from app.core.deps import DbDep
from app.core.errors import NotFoundError
from app.modules.common.enums import TaskType, WorkedExampleType
from app.modules.learning import service
from app.modules.learning.models import Task
from app.modules.learning.schemas import TaskOut, WorkedExampleOut

router = APIRouter()


def task_out(task: Task) -> TaskOut:
    return TaskOut(
        id=task.id,
        code=task.code,
        task_type=TaskType(task.task_type),
        title=task.title,
        skill=task.skill,
        difficulty=task.difficulty,
        grade_min=task.grade_min,
        grade_max=task.grade_max,
        statement=task.statement,
        related_task_id=task.related_task_id,
        order_index=task.order_index,
    )


@router.get("", response_model=list[TaskOut], summary="Actividades disponibles")
async def list_tasks(
    user: AnyUserDep,
    db: DbDep,
    grade: str | None = Query(default=None, pattern=r"^[789]$"),
    task_type: TaskType | None = None,
) -> list[TaskOut]:
    stmt = select(Task).where(Task.is_active.is_(True))
    if grade:
        stmt = stmt.where(Task.grade_min <= grade, Task.grade_max >= grade)
    if task_type:
        stmt = stmt.where(Task.task_type == task_type.value)
    rows = (await db.execute(stmt.order_by(Task.order_index, Task.code))).scalars()
    return [task_out(t) for t in rows]


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(task_id: uuid.UUID, _: AnyUserDep, db: DbDep) -> TaskOut:
    task = await db.get(Task, task_id)
    if task is None or not task.is_active:
        raise NotFoundError("Actividad no encontrada.")
    return task_out(task)


@router.get(
    "/{task_id}/worked-examples", response_model=list[WorkedExampleOut], summary="Ejemplos trabajados de la actividad"
)
async def worked_examples(task_id: uuid.UUID, _: AnyUserDep, db: DbDep) -> list[WorkedExampleOut]:
    task = await db.get(Task, task_id)
    if task is None:
        raise NotFoundError("Actividad no encontrada.")
    return [
        WorkedExampleOut(
            id=e.id,
            task_id=e.task_id,
            example_type=WorkedExampleType(e.example_type),
            title=e.title,
            content=e.content,
            order_index=e.order_index,
        )
        for e in await service.list_examples(db, task_id)
    ]
