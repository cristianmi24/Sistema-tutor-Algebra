"""Sesiones de aprendizaje: inicio/fin, eventos, respuestas, ayuda y consulta con alcance por rol."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.tasks import task_out
from app.core.auth import AnyUserDep, CurrentUser, StudentDep
from app.core.deps import DbDep
from app.core.errors import ForbiddenError, NotFoundError
from app.modules.common.enums import InteractionEventType, Representation, Role, ScaffoldType
from app.modules.identity.models import Student
from app.modules.learning import service
from app.modules.learning.models import Interaction, LearningSession, ScaffoldEvent, SessionTask, StudentResponse
from app.modules.learning.schemas import (
    ClientEvent,
    HelpOffer,
    HelpRequest,
    InteractionOut,
    ResponseOut,
    ResponseSubmit,
    ScaffoldEventOut,
    ScaffoldFeedback,
    SessionCreate,
    SessionEnd,
    SessionOut,
    SessionSummaryOut,
    SessionTaskOut,
    SubmitResult,
)
from app.modules.learning.scope import accessible_student_ids, require_student_access

router = APIRouter()


async def _current_student(db: AsyncSession, user: CurrentUser) -> Student:
    if user.student_id is None:
        raise ForbiddenError("Solo los estudiantes pueden realizar esta acción.")
    student = await db.get(Student, user.student_id)
    if student is None:
        raise NotFoundError("Perfil de estudiante no encontrado.")
    return student


async def _accessible_session(db: AsyncSession, user: CurrentUser, session_id: uuid.UUID) -> LearningSession:
    session = await service.load_session(db, session_id)
    await require_student_access(db, user, session.student_id)
    return session


def session_out(session: LearningSession, participant_code: str | None = None) -> SessionOut:
    return SessionOut(
        id=session.id,
        student_id=session.student_id,
        participant_code=participant_code,
        started_at=session.started_at,
        ended_at=session.ended_at,
        status=session.status,
        context=session.context,
        tasks=[
            SessionTaskOut(
                id=st.id,
                task=task_out(st.task),
                order_index=st.order_index,
                status=st.status,
                opened_at=st.opened_at,
                completed_at=st.completed_at,
            )
            for st in session.tasks
        ],
    )


def interaction_out(i: Interaction) -> InteractionOut:
    return InteractionOut(
        id=i.id,
        session_id=i.session_id,
        student_id=i.student_id,
        task_id=i.task_id,
        timestamp=i.timestamp,
        sequence=i.sequence,
        event_type=InteractionEventType(i.event_type),
        student_action=i.student_action,
        student_response=i.student_response,
        representation=i.representation,
        help_requested=i.help_requested,
        help_level=i.help_level,
        help_type=i.help_type,
        help_content=i.help_content,
        help_accepted=i.help_accepted,
        help_rejected=i.help_rejected,
        scaffold_event_id=i.scaffold_event_id,
        ai_interpretation=i.ai_interpretation,
        teacher_intervention_id=i.teacher_intervention_id,
        next_student_action=i.next_student_action,
        client_meta=i.client_meta,
    )


def scaffold_event_out(e: ScaffoldEvent) -> ScaffoldEventOut:
    return ScaffoldEventOut(
        id=e.id,
        session_id=e.session_id,
        student_id=e.student_id,
        task_id=e.task_id,
        interaction_id=e.interaction_id,
        scaffold_id=e.scaffold_id,
        scaffold_code=e.scaffold.code if e.scaffold else None,
        scaffold_type=ScaffoldType(e.scaffold.scaffold_type) if e.scaffold else None,
        decision=e.decision,
        previous_help_level=e.previous_help_level,
        current_help_level=e.current_help_level,
        reason_for_change=e.reason_for_change,
        source=e.source,
        delivered_text=e.delivered_text,
        accepted=e.accepted,
        rejected=e.rejected,
        reformulations=e.reformulations,
        result=e.result,
        subsequent_strategy=e.subsequent_strategy,
        created_at=e.created_at,
        resolved_at=e.resolved_at,
    )


def response_out(r: StudentResponse, actor: CurrentUser) -> ResponseOut:
    return ResponseOut(
        id=r.id,
        task_id=r.task_id,
        question_id=r.question_id,
        attempt_number=r.attempt_number,
        representation=Representation(r.representation),
        content=r.content,
        is_edit_of=r.is_edit_of,
        submitted_at=r.submitted_at,
        evaluation=service.visible_evaluation(r.evaluation, actor),
    )


# ---------------------------------------------------------------- ciclo de vida


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED, summary="Iniciar sesión de trabajo")
async def start(payload: SessionCreate, user: StudentDep, db: DbDep) -> SessionOut:
    student = await _current_student(db, user)
    session = await service.start_session(db, student, payload)
    return session_out(session, student.participant_code)


@router.get("", response_model=list[SessionSummaryOut], summary="Sesiones visibles según el rol")
async def list_sessions(
    user: AnyUserDep,
    db: DbDep,
    student_id: uuid.UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status", pattern=r"^(ACTIVE|COMPLETED|ABANDONED)$"),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[SessionSummaryOut]:
    ids = await accessible_student_ids(db, user)
    stmt = select(LearningSession, Student.participant_code).join(Student, Student.id == LearningSession.student_id)
    if ids is not None:
        stmt = stmt.where(LearningSession.student_id.in_(ids))
    if student_id is not None:
        stmt = stmt.where(LearningSession.student_id == student_id)
    if status_filter:
        stmt = stmt.where(LearningSession.status == status_filter)
    rows = (await db.execute(stmt.order_by(LearningSession.started_at.desc()).limit(limit))).all()
    out: list[SessionSummaryOut] = []
    for session, code in rows:
        task_count = (
            await db.scalar(select(func.count()).select_from(SessionTask).where(SessionTask.session_id == session.id))
            or 0
        )
        completed = (
            await db.scalar(
                select(func.count())
                .select_from(SessionTask)
                .where(SessionTask.session_id == session.id, SessionTask.status == "COMPLETED")
            )
            or 0
        )
        interactions = (
            await db.scalar(select(func.count()).select_from(Interaction).where(Interaction.session_id == session.id))
            or 0
        )
        helps = (
            await db.scalar(
                select(func.count())
                .select_from(Interaction)
                .where(Interaction.session_id == session.id, Interaction.event_type == "HELP_OFFERED")
            )
            or 0
        )
        out.append(
            SessionSummaryOut(
                id=session.id,
                student_id=session.student_id,
                participant_code=code,
                started_at=session.started_at,
                ended_at=session.ended_at,
                status=session.status,
                task_count=task_count,
                completed_count=completed,
                interaction_count=interactions,
                help_count=helps,
            )
        )
    return out


@router.get("/{session_id}", response_model=SessionOut)
async def get_session(session_id: uuid.UUID, user: AnyUserDep, db: DbDep) -> SessionOut:
    session = await _accessible_session(db, user, session_id)
    code = await db.scalar(select(Student.participant_code).where(Student.id == session.student_id))
    return session_out(session, code)


@router.patch("/{session_id}/end", response_model=SessionOut, summary="Terminar sesión")
async def end(session_id: uuid.UUID, payload: SessionEnd, user: StudentDep, db: DbDep) -> SessionOut:
    session = await _accessible_session(db, user, session_id)
    await service.end_session(db, session, payload.status)
    return session_out(await service.load_session(db, session.id), user.participant_code)


# ---------------------------------------------------------------- eventos, respuestas, ayuda


@router.post(
    "/{session_id}/events",
    response_model=InteractionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Evento del cliente",
)
async def client_event(session_id: uuid.UUID, payload: ClientEvent, user: StudentDep, db: DbDep) -> InteractionOut:
    session = await _accessible_session(db, user, session_id)
    return interaction_out(await service.record_client_event(db, session, payload))


@router.post(
    "/{session_id}/responses",
    response_model=SubmitResult,
    status_code=status.HTTP_201_CREATED,
    summary="Enviar respuesta",
)
async def submit(session_id: uuid.UUID, payload: ResponseSubmit, user: StudentDep, db: DbDep) -> SubmitResult:
    session = await _accessible_session(db, user, session_id)
    student = await _current_student(db, user)
    response, _evaluation, outcome = await service.submit_response(db, session, student, payload)
    return SubmitResult(
        response=response_out(response, user), help=outcome.offer, state_label=service.student_label(outcome.state)
    )


@router.post("/{session_id}/help", response_model=HelpOffer, summary="Pedir ayuda")
async def help_request(session_id: uuid.UUID, payload: HelpRequest, user: StudentDep, db: DbDep) -> HelpOffer:
    session = await _accessible_session(db, user, session_id)
    student = await _current_student(db, user)
    _, outcome = await service.request_help(
        db, session, student, payload.task_id, payload.question_id, payload.client_meta
    )
    return outcome.offer or HelpOffer(
        scaffold_event_id=None,
        offered=False,
        level=0,
        scaffold_type=None,
        text=None,
        message="Por ahora, intenta seguir por tu cuenta.",
    )


@router.post(
    "/{session_id}/scaffold-events/{event_id}/feedback",
    response_model=HelpOffer | ScaffoldEventOut,
    summary="Aceptar, rechazar o reformular una ayuda",
)
async def feedback(
    session_id: uuid.UUID, event_id: uuid.UUID, payload: ScaffoldFeedback, user: StudentDep, db: DbDep
) -> HelpOffer | ScaffoldEventOut:
    session = await _accessible_session(db, user, session_id)
    event, offer = await service.scaffold_feedback(db, session, event_id, payload.action, payload.client_meta)
    if offer is not None:
        return offer
    return scaffold_event_out(event)


# ---------------------------------------------------------------- consultas (trazabilidad)


@router.get(
    "/{session_id}/interactions", response_model=list[InteractionOut], summary="Eventos de la sesión (append-only)"
)
async def interactions(
    session_id: uuid.UUID, user: AnyUserDep, db: DbDep, task_id: uuid.UUID | None = None
) -> list[InteractionOut]:
    session = await _accessible_session(db, user, session_id)
    return [interaction_out(i) for i in await service.session_interactions(db, session.id, task_id=task_id)]


@router.get("/{session_id}/responses", response_model=list[ResponseOut], summary="Respuestas de la sesión")
async def responses(
    session_id: uuid.UUID, user: AnyUserDep, db: DbDep, task_id: uuid.UUID | None = None
) -> list[ResponseOut]:
    session = await _accessible_session(db, user, session_id)
    stmt = select(StudentResponse).where(StudentResponse.session_id == session.id)
    if task_id is not None:
        stmt = stmt.where(StudentResponse.task_id == task_id)
    rows = (await db.execute(stmt.order_by(StudentResponse.submitted_at))).scalars()
    return [response_out(r, user) for r in rows]


@router.get(
    "/{session_id}/scaffold-events", response_model=list[ScaffoldEventOut], summary="Ayudas ofrecidas en la sesión"
)
async def scaffold_events(session_id: uuid.UUID, user: AnyUserDep, db: DbDep) -> list[ScaffoldEventOut]:
    session = await _accessible_session(db, user, session_id)
    if user.role == Role.STUDENT:
        raise ForbiddenError("Las decisiones del tutor solo son visibles para personal autorizado.")
    from sqlalchemy.orm import selectinload

    rows = (
        await db.execute(
            select(ScaffoldEvent)
            .options(selectinload(ScaffoldEvent.scaffold))
            .where(ScaffoldEvent.session_id == session.id)
            .order_by(ScaffoldEvent.created_at)
        )
    ).scalars()
    return [scaffold_event_out(e) for e in rows]
