"""Alcance (scope) de acceso a datos de estudiantes por rol.

* STUDENT: solo sus propios datos.
* TEACHER: estudiantes de los grupos asignados (institución + grado + grupo).
* RESEARCHER: estudiantes ELIGIBLE (consentimiento efectivo) de su institución (o de todas si es global).
* ADMIN: todo.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.core.errors import ForbiddenError, NotFoundError
from app.modules.common.enums import Role
from app.modules.identity.models import Student, TeacherGroupAssignment


async def teacher_groups(db: AsyncSession, teacher_id: uuid.UUID) -> list[TeacherGroupAssignment]:
    result = await db.execute(select(TeacherGroupAssignment).where(TeacherGroupAssignment.teacher_id == teacher_id))
    return list(result.scalars())


async def can_access_student(db: AsyncSession, actor: CurrentUser, student: Student) -> bool:
    if actor.role == Role.ADMIN:
        return True
    if actor.role == Role.STUDENT:
        return actor.student_id == student.id
    if actor.role == Role.TEACHER:
        if actor.teacher_id is None or actor.institution_id != student.institution_id:
            return False
        for group in await teacher_groups(db, actor.teacher_id):
            if group.grade == student.grade and group.group_code == (student.group_code or ""):
                return True
        return False
    if actor.role == Role.RESEARCHER:
        if student.research_status != "ELIGIBLE":
            return False
        return actor.institution_id is None or actor.institution_id == student.institution_id
    return False


async def require_student_access(db: AsyncSession, actor: CurrentUser, student_id: uuid.UUID) -> Student:
    student = await db.get(Student, student_id)
    if student is None:
        raise NotFoundError("Participante no encontrado.")
    if not await can_access_student(db, actor, student):
        # 404 para no revelar existencia a quien no tiene alcance.
        raise NotFoundError("Participante no encontrado.")
    return student


async def accessible_student_ids(db: AsyncSession, actor: CurrentUser) -> list[uuid.UUID] | None:
    """Lista de estudiantes accesibles; ``None`` significa sin restricción (ADMIN / investigador global)."""
    if actor.role == Role.ADMIN:
        return None
    if actor.role == Role.STUDENT:
        return [actor.student_id] if actor.student_id else []
    if actor.role == Role.TEACHER:
        if actor.teacher_id is None:
            return []
        groups = await teacher_groups(db, actor.teacher_id)
        if not groups:
            return []
        ids: list[uuid.UUID] = []
        for group in groups:
            result = await db.execute(
                select(Student.id).where(
                    Student.institution_id == group.institution_id,
                    Student.grade == group.grade,
                    Student.group_code == group.group_code,
                )
            )
            ids.extend(result.scalars())
        return ids
    if actor.role == Role.RESEARCHER:
        stmt = select(Student.id).where(Student.research_status == "ELIGIBLE")
        if actor.institution_id is not None:
            stmt = stmt.where(Student.institution_id == actor.institution_id)
        return list((await db.execute(stmt)).scalars())
    raise ForbiddenError("Rol sin alcance definido.")
