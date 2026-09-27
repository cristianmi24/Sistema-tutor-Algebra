"""Docente: panorama de grupos, intervenciones (separadas del sistema) y anotaciones."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Response, status

from app.core.auth import StaffDep, StudentDep, TeacherDep
from app.core.deps import DbDep
from app.modules.teacher import service
from app.modules.teacher.schemas import GroupOverview, InterventionIn, InterventionOut, StudentMessageOut

router = APIRouter()
student_router = APIRouter()


@router.get("/groups", response_model=list[GroupOverview], summary="Grupos asignados con el estado de cada estudiante")
async def groups(user: TeacherDep, db: DbDep) -> list[GroupOverview]:
    return await service.groups_overview(db, user)


@router.post(
    "/interventions",
    response_model=InterventionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar intervención docente",
)
async def create(payload: InterventionIn, user: TeacherDep, db: DbDep) -> InterventionOut:
    return await service.intervention_out(db, await service.create_intervention(db, user, payload))


@router.get("/interventions", response_model=list[InterventionOut], summary="Intervenciones docentes (alcance por rol)")
async def list_interventions(
    user: StaffDep, db: DbDep, session_id: uuid.UUID | None = None, student_id: uuid.UUID | None = None
) -> list[InterventionOut]:
    rows = await service.list_interventions(db, user, session_id=session_id, student_id=student_id)
    return [await service.intervention_out(db, r) for r in rows]


@student_router.get(
    "/{session_id}/teacher-messages",
    response_model=list[StudentMessageOut],
    summary="Mensajes del docente para el estudiante",
)
async def messages(session_id: uuid.UUID, user: StudentDep, db: DbDep) -> list[StudentMessageOut]:
    return await service.student_messages(db, user, session_id)


@student_router.post("/{session_id}/teacher-messages/{message_id}/seen", status_code=status.HTTP_204_NO_CONTENT)
async def seen(session_id: uuid.UUID, message_id: uuid.UUID, user: StudentDep, db: DbDep) -> Response:
    await service.mark_seen(db, user, session_id, message_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
