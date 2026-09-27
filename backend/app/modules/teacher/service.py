"""Servicios del módulo docente."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.core.errors import ForbiddenError, NotFoundError
from app.core.security import utcnow
from app.modules.common.enums import STUDENT_FACING_STATE_LABELS, InteractionEventType, Role, StudentState
from app.modules.identity.models import Student, Teacher, User
from app.modules.learning.models import (
    Interaction,
    LearningSession,
    ScaffoldEvent,
    SessionTask,
    Task,
    TeacherIntervention,
)
from app.modules.learning.scope import require_student_access, teacher_groups
from app.modules.learning.service import ensure_active, load_session, record_event, session_task
from app.modules.teacher.schemas import (
    GroupOverview,
    InterventionIn,
    InterventionOut,
    StudentMessageOut,
    StudentOverview,
)
from app.modules.tutor.models import StudentStateRow


async def intervention_out(db: AsyncSession, row: TeacherIntervention) -> InterventionOut:
    teacher = await db.get(Teacher, row.teacher_id)
    student = await db.get(Student, row.student_id)
    return InterventionOut(
        id=row.id,
        teacher_code=teacher.display_code if teacher else None,
        student_id=row.student_id,
        participant_code=student.participant_code if student else None,
        session_id=row.session_id,
        task_id=row.task_id,
        interaction_id=row.interaction_id,
        intervention_type=row.intervention_type,
        content=row.content,
        visibility=row.visibility,
        student_seen_at=row.student_seen_at,
        created_at=row.created_at,
    )


async def create_intervention(db: AsyncSession, actor: CurrentUser, payload: InterventionIn) -> TeacherIntervention:
    if actor.role != Role.TEACHER or actor.teacher_id is None:
        raise ForbiddenError("Solo docentes pueden registrar intervenciones docentes.")
    session = await load_session(db, payload.session_id)
    await require_student_access(db, actor, session.student_id)
    if payload.task_id is not None:
        session_task(session, payload.task_id)
    row = TeacherIntervention(
        teacher_id=actor.teacher_id,
        student_id=session.student_id,
        session_id=session.id,
        task_id=payload.task_id,
        intervention_type=payload.intervention_type,
        content=payload.content,
        visibility=payload.visibility,
    )
    db.add(row)
    await db.flush()
    if payload.visibility == "STUDENT":
        # Evento propio del docente: el tutor pausa sus intervenciones (regla R-TEACHER-PAUSE).
        ensure_active(session)
        event = await record_event(
            db,
            session,
            InteractionEventType.TEACHER_INTERVENTION,
            task_id=payload.task_id,
            student_action=f"TEACHER_{payload.intervention_type}",
            teacher_intervention_id=row.id,
        )
        row.interaction_id = event.id
    await db.flush()
    return row


async def list_interventions(
    db: AsyncSession, actor: CurrentUser, *, session_id: uuid.UUID | None = None, student_id: uuid.UUID | None = None
) -> list[TeacherIntervention]:
    stmt = select(TeacherIntervention)
    if session_id is not None:
        session = await load_session(db, session_id)
        await require_student_access(db, actor, session.student_id)
        stmt = stmt.where(TeacherIntervention.session_id == session_id)
    elif student_id is not None:
        await require_student_access(db, actor, student_id)
        stmt = stmt.where(TeacherIntervention.student_id == student_id)
    elif actor.role == Role.TEACHER:
        stmt = stmt.where(TeacherIntervention.teacher_id == actor.teacher_id)
    return list((await db.execute(stmt.order_by(TeacherIntervention.created_at))).scalars())


async def student_messages(db: AsyncSession, actor: CurrentUser, session_id: uuid.UUID) -> list[StudentMessageOut]:
    session = await load_session(db, session_id)
    if actor.student_id != session.student_id:
        raise NotFoundError("Sesión no encontrada.")
    rows = (
        await db.execute(
            select(TeacherIntervention)
            .where(TeacherIntervention.session_id == session_id, TeacherIntervention.visibility == "STUDENT")
            .order_by(TeacherIntervention.created_at)
        )
    ).scalars()
    return [
        StudentMessageOut(
            id=r.id,
            task_id=r.task_id,
            intervention_type=r.intervention_type,
            content=r.content,
            created_at=r.created_at,
            seen=r.student_seen_at is not None,
        )
        for r in rows
    ]


async def mark_seen(db: AsyncSession, actor: CurrentUser, session_id: uuid.UUID, message_id: uuid.UUID) -> None:
    row = await db.get(TeacherIntervention, message_id)
    if row is None or row.session_id != session_id or row.student_id != actor.student_id or row.visibility != "STUDENT":
        raise NotFoundError("Mensaje no encontrado.")
    if row.student_seen_at is None:
        row.student_seen_at = utcnow()


async def groups_overview(db: AsyncSession, actor: CurrentUser) -> list[GroupOverview]:
    if actor.role != Role.TEACHER or actor.teacher_id is None:
        raise ForbiddenError("Solo docentes tienen grupos asignados.")
    out: list[GroupOverview] = []
    for group in await teacher_groups(db, actor.teacher_id):
        rows = (
            await db.execute(
                select(Student, User.status)
                .join(User, User.id == Student.user_id)
                .where(
                    Student.institution_id == group.institution_id,
                    Student.grade == group.grade,
                    Student.group_code == group.group_code,
                )
                .order_by(Student.participant_code)
            )
        ).all()
        students: list[StudentOverview] = []
        for student, account_status in rows:
            students.append(await _student_overview(db, student, account_status))
        out.append(
            GroupOverview(
                institution_id=group.institution_id, grade=group.grade, group_code=group.group_code, students=students
            )
        )
    return out


async def _student_overview(db: AsyncSession, student: Student, account_status: str) -> StudentOverview:
    session = await db.scalar(
        select(LearningSession)
        .where(LearningSession.student_id == student.id, LearningSession.status == "ACTIVE")
        .order_by(LearningSession.started_at.desc())
    )
    state = await db.scalar(select(StudentStateRow).where(StudentStateRow.student_id == student.id))
    current_task: Task | None = None
    last_event: Interaction | None = None
    helps = requests = teacher_count = 0
    suggest = False
    if session is not None:
        last_event = await db.scalar(
            select(Interaction).where(Interaction.session_id == session.id).order_by(Interaction.sequence.desc())
        )
        open_task = await db.scalar(
            select(Task)
            .join(SessionTask, SessionTask.task_id == Task.id)
            .where(SessionTask.session_id == session.id, SessionTask.status == "OPEN")
            .order_by(SessionTask.opened_at.desc())
        )
        current_task = open_task
        counts = dict(
            (
                await db.execute(
                    select(Interaction.event_type, func.count())
                    .where(
                        Interaction.session_id == session.id,
                        Interaction.event_type.in_(["HELP_OFFERED", "HELP_REQUESTED", "TEACHER_INTERVENTION"]),
                    )
                    .group_by(Interaction.event_type)
                )
            ).all()
        )
        helps, requests, teacher_count = (
            counts.get("HELP_OFFERED", 0),
            counts.get("HELP_REQUESTED", 0),
            counts.get("TEACHER_INTERVENTION", 0),
        )
        if current_task is not None:
            last_decision = await db.scalar(
                select(ScaffoldEvent.decision)
                .where(ScaffoldEvent.session_id == session.id, ScaffoldEvent.task_id == current_task.id)
                .order_by(ScaffoldEvent.created_at.desc())
            )
            suggest = bool(last_decision and last_decision.get("suggest_teacher"))
    operational = state.current_state if state and session is not None and state.session_id == session.id else None
    return StudentOverview(
        student_id=student.id,
        participant_code=student.participant_code,
        grade=student.grade,
        group_code=student.group_code,
        account_status=account_status,
        active_session_id=session.id if session else None,
        current_task_code=current_task.code if current_task else None,
        current_task_title=current_task.title if current_task else None,
        last_event_at=last_event.timestamp if last_event else None,
        last_event_type=last_event.event_type if last_event else None,
        system_helps_in_session=helps,
        help_requests_in_session=requests,
        teacher_interventions_in_session=teacher_count,
        state_label=STUDENT_FACING_STATE_LABELS[StudentState(operational)] if operational else None,
        operational_state=operational,
        suggest_teacher=suggest,
    )
