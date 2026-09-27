"""Servicios de aprendizaje: sesiones, eventos append-only, respuestas y ayuda.

La decisión pedagógica está desacoplada mediante ``TutorPolicy`` (Fase 3: política estática del
banco; Fase 4: motor adaptativo). El servicio garantiza la trazabilidad: cada acción genera un evento.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import CurrentUser
from app.core.errors import AppError, ConflictError, NotFoundError
from app.core.security import utcnow
from app.modules.common.enums import STUDENT_FACING_STATE_LABELS, InteractionEventType, Role, StudentState
from app.modules.identity.models import Student
from app.modules.learning.evaluation import Evaluation, evaluate_response
from app.modules.learning.models import (
    Interaction,
    LearningSession,
    Scaffold,
    ScaffoldEvent,
    SessionTask,
    StudentResponse,
    Task,
    WorkedExample,
)
from app.modules.learning.schemas import (
    ClientEvent,
    ClientMeta,
    HelpOffer,
    ResponseSubmit,
    SessionCreate,
)

# --------------------------------------------------------------------------- eventos


async def _next_sequence(db: AsyncSession, session: LearningSession) -> int:
    """Secuencia monótona por sesión; bloquea la fila de la sesión para serializar."""
    locked = await db.execute(select(LearningSession).where(LearningSession.id == session.id).with_for_update())
    row = locked.scalar_one()
    row.last_sequence += 1
    session.last_sequence = row.last_sequence
    return row.last_sequence


async def record_event(
    db: AsyncSession,
    session: LearningSession,
    event_type: InteractionEventType,
    *,
    task_id: uuid.UUID | None = None,
    student_action: str | None = None,
    student_response: dict[str, Any] | None = None,
    response_id: uuid.UUID | None = None,
    representation: str | None = None,
    help_requested: bool = False,
    help_level: int | None = None,
    help_type: str | None = None,
    help_content: str | None = None,
    help_accepted: bool | None = None,
    help_rejected: bool | None = None,
    scaffold_event_id: uuid.UUID | None = None,
    ai_interpretation: dict[str, Any] | None = None,
    teacher_intervention_id: uuid.UUID | None = None,
    client_meta: ClientMeta | dict[str, Any] | None = None,
) -> Interaction:
    meta = client_meta.model_dump(exclude_none=True) if isinstance(client_meta, ClientMeta) else (client_meta or {})
    sequence = await _next_sequence(db, session)
    # Encadenar: el evento anterior conoce la siguiente acción del estudiante.
    previous = await db.scalar(
        select(Interaction).where(Interaction.session_id == session.id, Interaction.sequence == sequence - 1)
    )
    if (
        previous is not None
        and previous.next_student_action is None
        and event_type
        not in (
            InteractionEventType.HELP_OFFERED,
            InteractionEventType.ERROR_DETECTED,
            InteractionEventType.TEACHER_INTERVENTION,
        )
    ):
        previous.next_student_action = event_type.value
    row = Interaction(
        session_id=session.id,
        student_id=session.student_id,
        task_id=task_id,
        sequence=sequence,
        event_type=event_type.value,
        student_action=student_action or event_type.value,
        student_response=student_response,
        response_id=response_id,
        representation=representation,
        help_requested=help_requested,
        help_level=help_level,
        help_type=help_type,
        help_content=help_content,
        help_accepted=help_accepted,
        help_rejected=help_rejected,
        scaffold_event_id=scaffold_event_id,
        ai_interpretation=ai_interpretation,
        teacher_intervention_id=teacher_intervention_id,
        client_meta=meta,
    )
    db.add(row)
    await db.flush()
    # Episodios de investigación (import tardío para evitar dependencia circular entre módulos).
    from app.modules.research.episodes import track_event

    await track_event(db, session, row)
    return row


# --------------------------------------------------------------------------- política de tutor


@dataclass(slots=True)
class TutorContext:
    session: LearningSession
    student: Student
    task: Task
    trigger: InteractionEventType
    trigger_interaction: Interaction
    latest_response: StudentResponse | None
    latest_evaluation: Evaluation | None
    question_id: str | None
    help_requested: bool
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TutorOutcome:
    scaffold_event: ScaffoldEvent | None
    offer: HelpOffer | None
    state: StudentState


class TutorPolicy(Protocol):
    async def decide(self, db: AsyncSession, ctx: TutorContext) -> TutorOutcome: ...


def _ai_on() -> bool:
    from app.modules.ai.service import ai_enabled

    return ai_enabled()


async def enrich_with_ai_interpretation(
    db: AsyncSession, session: LearningSession, task: Task, interaction: Interaction, text: str
) -> None:
    """Interpretación opcional (vocabulario cerrado, validada) de una explicación abierta. Solo para personal."""
    from app.modules.ai.service import ai_enabled, current_settings, interpret_explanation

    settings = current_settings()
    if settings is None or not ai_enabled() or not text.strip():
        return
    outcome = await interpret_explanation(
        db, settings, session=session, task=task, text=text, interaction_id=interaction.id
    )
    if outcome is None:
        return
    interaction.ai_interpretation = (
        {**outcome.value, "ai_interaction_id": str(outcome.interaction_id)}
        if outcome.approved
        else {"approved": False, "ai_interaction_id": str(outcome.interaction_id), "reasons": outcome.reasons}
    )
    await db.flush()


def student_label(state: StudentState) -> str:
    return STUDENT_FACING_STATE_LABELS[state]


async def scaffold_candidates(db: AsyncSession, task: Task, *, max_level: int, min_level: int = 1) -> list[Scaffold]:
    result = await db.execute(
        select(Scaffold)
        .where(
            Scaffold.is_active.is_(True),
            Scaffold.level >= min_level,
            Scaffold.level <= max_level,
        )
        .order_by(Scaffold.level, Scaffold.code)
    )
    rows = list(result.scalars())
    return [
        s
        for s in rows
        if (not s.applicable_task_types or task.task_type in s.applicable_task_types)
        and (not s.applicable_skills or task.skill in s.applicable_skills)
    ]


async def used_scaffold_ids(
    db: AsyncSession, session_id: uuid.UUID, task_id: uuid.UUID
) -> dict[uuid.UUID, ScaffoldEvent]:
    result = await db.execute(
        select(ScaffoldEvent).where(ScaffoldEvent.session_id == session_id, ScaffoldEvent.task_id == task_id)
    )
    return {e.scaffold_id: e for e in result.scalars() if e.scaffold_id is not None}


async def deliver_scaffold(
    db: AsyncSession,
    ctx: TutorContext,
    scaffold: Scaffold | None,
    *,
    level: int,
    previous_level: int,
    decision: dict[str, Any],
    reason: str,
    source: str = "SYSTEM",
) -> tuple[ScaffoldEvent, HelpOffer]:
    text = str(scaffold.content.get("text", "")) if scaffold else None
    event = ScaffoldEvent(
        session_id=ctx.session.id,
        student_id=ctx.student.id,
        task_id=ctx.task.id,
        interaction_id=ctx.trigger_interaction.id,
        scaffold_id=scaffold.id if scaffold else None,
        decision=decision,
        previous_help_level=previous_level,
        current_help_level=level,
        reason_for_change=reason,
        source=source,
        delivered_text=text,
        result="PENDING",
    )
    db.add(event)
    await db.flush()
    await record_event(
        db,
        ctx.session,
        InteractionEventType.HELP_OFFERED,
        task_id=ctx.task.id,
        student_action="SYSTEM_HELP_OFFERED",
        help_level=level,
        help_type=scaffold.scaffold_type if scaffold else None,
        help_content=text,
        scaffold_event_id=event.id,
    )
    offer = HelpOffer(
        scaffold_event_id=event.id,
        offered=True,
        level=level,
        scaffold_type=scaffold.scaffold_type if scaffold else None,
        text=text,
        follow_up=str(scaffold.content.get("follow_up")) if scaffold and scaffold.content.get("follow_up") else None,
        can_reformulate=bool(scaffold and (scaffold.content.get("variants") or _ai_on())),
        message="Aquí tienes una pista. Puedes usarla, pedirla de otra forma o seguir por tu cuenta.",
    )
    return event, offer


class StaticBankPolicy:
    """Fase 3: solo interviene cuando el estudiante PIDE ayuda; entrega la ayuda de menor nivel no usada."""

    async def decide(self, db: AsyncSession, ctx: TutorContext) -> TutorOutcome:
        if not ctx.help_requested:
            return TutorOutcome(scaffold_event=None, offer=None, state=StudentState.NORMAL)
        used = await used_scaffold_ids(db, ctx.session.id, ctx.task.id)
        rejected = {sid for sid, ev in used.items() if ev.rejected}
        previous_level = max((ev.current_help_level for ev in used.values()), default=0)
        level = min(5, max(1, previous_level + (1 if used else 0)))
        candidates = [
            s
            for s in await scaffold_candidates(db, ctx.task, max_level=level)
            if s.id not in rejected and s.id not in used
        ]
        if not candidates:
            candidates = [s for s in await scaffold_candidates(db, ctx.task, max_level=5) if s.id not in rejected]
        scaffold = candidates[0] if candidates else None
        reason = "El estudiante solicitó ayuda; se entrega la ayuda de menor nivel aún no usada (política estática)."
        decision: dict[str, Any] = {
            "need_detected": "HELP_REQUESTED",
            "evidence": ["help_requested=true"],
            "candidate_supports": [s.code for s in candidates[:5]],
            "selected_support": scaffold.code if scaffold else None,
            "explicitness_level": scaffold.level if scaffold else 0,
            "confidence": 1.0,
            "reason": reason,
            "validation_status": "NOT_REQUIRED",
            "rule_code": "STATIC-HELP-REQUESTED",
            "previous_help_level": previous_level,
            "fading_action": "INCREASE" if scaffold and scaffold.level > previous_level else "KEEP",
        }
        if scaffold is None:
            return TutorOutcome(
                scaffold_event=None,
                offer=HelpOffer(
                    scaffold_event_id=None,
                    offered=False,
                    level=0,
                    scaffold_type=None,
                    text=None,
                    message="Ya usaste las ayudas disponibles para esta tarea. Tu docente puede acompañarte.",
                ),
                state=StudentState.NORMAL,
            )
        event, offer = await deliver_scaffold(
            db,
            ctx,
            scaffold,
            level=scaffold.level,
            previous_level=previous_level,
            decision=decision,
            reason=reason,
            source="STATIC",
        )
        return TutorOutcome(scaffold_event=event, offer=offer, state=StudentState.NORMAL)


PolicyFactory = Callable[[], TutorPolicy]
_policy_factory: PolicyFactory = StaticBankPolicy


def set_tutor_policy_factory(factory: PolicyFactory) -> None:
    global _policy_factory
    _policy_factory = factory


def get_tutor_policy() -> TutorPolicy:
    return _policy_factory()


# --------------------------------------------------------------------------- sesiones


async def tasks_for_grade(db: AsyncSession, grade: str) -> list[Task]:
    result = await db.execute(
        select(Task)
        .where(Task.is_active.is_(True), Task.grade_min <= grade, Task.grade_max >= grade)
        .order_by(Task.order_index, Task.code)
    )
    return list(result.scalars())


async def load_session(db: AsyncSession, session_id: uuid.UUID) -> LearningSession:
    session = await db.scalar(
        select(LearningSession)
        .options(selectinload(LearningSession.tasks).selectinload(SessionTask.task))
        .where(LearningSession.id == session_id)
    )
    if session is None:
        raise NotFoundError("Sesión no encontrada.")
    return session


async def start_session(db: AsyncSession, student: Student, payload: SessionCreate) -> LearningSession:
    active = await db.scalar(
        select(LearningSession).where(LearningSession.student_id == student.id, LearningSession.status == "ACTIVE")
    )
    if active is not None:
        raise ConflictError(
            "Ya tienes una sesión activa. Termínala antes de iniciar otra.", details={"session_id": str(active.id)}
        )
    if payload.task_codes:
        result = await db.execute(select(Task).where(Task.code.in_(payload.task_codes), Task.is_active.is_(True)))
        by_code = {t.code: t for t in result.scalars()}
        tasks = [by_code[c] for c in payload.task_codes if c in by_code]
        if len(tasks) != len(payload.task_codes):
            raise NotFoundError("Alguna de las actividades no existe o no está activa.")
    else:
        tasks = await tasks_for_grade(db, student.grade)
    if not tasks:
        raise AppError("No hay actividades disponibles para tu grado todavía.")
    session = LearningSession(student_id=student.id, institution_id=student.institution_id, context=payload.context)
    db.add(session)
    await db.flush()
    for index, task in enumerate(tasks):
        db.add(SessionTask(session_id=session.id, task_id=task.id, order_index=index))
    await db.flush()
    await record_event(db, session, InteractionEventType.SESSION_STARTED, client_meta={"task_count": len(tasks)})
    return await load_session(db, session.id)


async def end_session(db: AsyncSession, session: LearningSession, status: str) -> LearningSession:
    if session.status != "ACTIVE":
        raise ConflictError("La sesión ya terminó.")
    now = utcnow()
    for st in session.tasks:
        if st.status in ("PENDING", "OPEN"):
            st.status = "ABANDONED" if status == "ABANDONED" else st.status
    session.status = status
    session.ended_at = now
    await record_event(db, session, InteractionEventType.SESSION_ENDED, client_meta={"status": status})
    return session


def ensure_active(session: LearningSession) -> None:
    if session.status != "ACTIVE":
        raise ConflictError("La sesión no está activa.")


def session_task(session: LearningSession, task_id: uuid.UUID) -> SessionTask:
    for st in session.tasks:
        if st.task_id == task_id:
            return st
    raise NotFoundError("La actividad no pertenece a esta sesión.")


async def record_client_event(db: AsyncSession, session: LearningSession, payload: ClientEvent) -> Interaction:
    ensure_active(session)
    st = session_task(session, payload.task_id) if payload.task_id else None
    now = utcnow()
    if payload.event_type == InteractionEventType.TASK_OPENED and st is not None:
        if st.status == "PENDING":
            st.status = "OPEN"
            st.opened_at = now
    elif payload.event_type == InteractionEventType.TASK_COMPLETED and st is not None:
        st.status = "COMPLETED"
        st.completed_at = now
    elif payload.event_type == InteractionEventType.TASK_ABANDONED and st is not None:
        st.status = "ABANDONED"
    student_response = None
    if payload.event_type == InteractionEventType.SELF_EXPLANATION:
        student_response = {"text": str(payload.payload.get("text", ""))[:4000]}
    elif payload.payload:
        student_response = payload.payload
    event = await record_event(
        db,
        session,
        payload.event_type,
        task_id=payload.task_id,
        student_response=student_response,
        representation=payload.representation.value if payload.representation else None,
        client_meta=payload.client_meta,
    )
    if payload.event_type == InteractionEventType.SELF_EXPLANATION and st is not None and student_response:
        await enrich_with_ai_interpretation(db, session, st.task, event, str(student_response.get("text", "")))
    return event


# --------------------------------------------------------------------------- respuestas


def find_question(task: Task, question_id: str) -> dict[str, Any]:
    for q in task.statement.get("questions", []):
        if q.get("id") == question_id:
            return q  # type: ignore[no-any-return]
    raise NotFoundError("La pregunta no existe en esta actividad.")


async def submit_response(
    db: AsyncSession, session: LearningSession, student: Student, payload: ResponseSubmit
) -> tuple[StudentResponse, Evaluation, TutorOutcome]:
    ensure_active(session)
    st = session_task(session, payload.task_id)
    task = st.task
    question = find_question(task, payload.question_id)
    if st.status == "PENDING":
        st.status = "OPEN"
        st.opened_at = utcnow()

    attempts = await db.scalar(
        select(func.count())
        .select_from(StudentResponse)
        .where(
            StudentResponse.session_id == session.id,
            StudentResponse.task_id == task.id,
            StudentResponse.question_id == payload.question_id,
        )
    )
    attempt_number = (attempts or 0) + 1
    if payload.is_edit_of is not None:
        original = await db.get(StudentResponse, payload.is_edit_of)
        if original is None or original.session_id != session.id:
            raise NotFoundError("La respuesta que intentas editar no existe.")

    rule = task.solution.get("expression")
    evaluation = evaluate_response(
        rule=str(rule) if rule else None,
        question=question,
        representation=payload.representation.value,
        content=payload.content,
    )
    response = StudentResponse(
        session_id=session.id,
        task_id=task.id,
        student_id=student.id,
        question_id=payload.question_id,
        attempt_number=attempt_number,
        representation=payload.representation.value,
        content=payload.content,
        is_edit_of=payload.is_edit_of,
        evaluation=evaluation.as_dict(),
    )
    db.add(response)
    await db.flush()

    if payload.is_edit_of is not None:
        event_type = InteractionEventType.STUDENT_EDITED_RESPONSE
    elif attempt_number > 1:
        event_type = InteractionEventType.STUDENT_REATTEMPT
    else:
        event_type = InteractionEventType.STUDENT_RESPONSE
    interaction = await record_event(
        db,
        session,
        event_type,
        task_id=task.id,
        student_response={"question_id": payload.question_id, **payload.content},
        response_id=response.id,
        representation=payload.representation.value,
        client_meta=payload.client_meta,
    )
    if evaluation.correct is False:
        await record_event(
            db,
            session,
            InteractionEventType.ERROR_DETECTED,
            task_id=task.id,
            student_action="SYSTEM_EVALUATION",
            student_response={"question_id": payload.question_id, "error_pattern": evaluation.error_pattern},
            response_id=response.id,
            representation=payload.representation.value,
        )

    if payload.representation.value == "VERBAL":
        await enrich_with_ai_interpretation(db, session, task, interaction, str(payload.content.get("text", "")))

    await resolve_pending_scaffolds(db, session, task.id, evaluation, payload.representation.value)

    ctx = TutorContext(
        session=session,
        student=student,
        task=task,
        trigger=event_type,
        trigger_interaction=interaction,
        latest_response=response,
        latest_evaluation=evaluation,
        question_id=payload.question_id,
        help_requested=False,
    )
    outcome = await get_tutor_policy().decide(db, ctx)
    return response, evaluation, outcome


async def resolve_pending_scaffolds(
    db: AsyncSession, session: LearningSession, task_id: uuid.UUID, evaluation: Evaluation, representation: str
) -> None:
    """Memoria de intervención: qué ocurrió después de cada ayuda pendiente."""
    result = await db.execute(
        select(ScaffoldEvent).where(
            ScaffoldEvent.session_id == session.id,
            ScaffoldEvent.task_id == task_id,
            ScaffoldEvent.result == "PENDING",
            ScaffoldEvent.rejected.is_not(True),
        )
    )
    now = utcnow()
    for event in result.scalars():
        if evaluation.correct is True:
            event.result = "IMPROVED"
        elif evaluation.correct is False:
            event.result = "PERSISTED"
        else:
            event.result = "UNKNOWN"
        event.student_response = evaluation.as_dict()
        event.subsequent_strategy = f"RESPONDED_{representation}"
        event.resolved_at = now


# --------------------------------------------------------------------------- ayuda


async def request_help(
    db: AsyncSession,
    session: LearningSession,
    student: Student,
    task_id: uuid.UUID,
    question_id: str | None,
    client_meta: ClientMeta,
) -> tuple[Interaction, TutorOutcome]:
    ensure_active(session)
    st = session_task(session, task_id)
    interaction = await record_event(
        db,
        session,
        InteractionEventType.HELP_REQUESTED,
        task_id=task_id,
        help_requested=True,
        student_response={"question_id": question_id} if question_id else None,
        client_meta=client_meta,
    )
    latest = await db.scalar(
        select(StudentResponse)
        .where(StudentResponse.session_id == session.id, StudentResponse.task_id == task_id)
        .order_by(StudentResponse.submitted_at.desc())
    )
    ctx = TutorContext(
        session=session,
        student=student,
        task=st.task,
        trigger=InteractionEventType.HELP_REQUESTED,
        trigger_interaction=interaction,
        latest_response=latest,
        latest_evaluation=None,
        question_id=question_id,
        help_requested=True,
    )
    outcome = await get_tutor_policy().decide(db, ctx)
    return interaction, outcome


async def scaffold_feedback(
    db: AsyncSession, session: LearningSession, event_id: uuid.UUID, action: str, client_meta: ClientMeta
) -> tuple[ScaffoldEvent, HelpOffer | None]:
    ensure_active(session)
    event = await db.scalar(
        select(ScaffoldEvent).options(selectinload(ScaffoldEvent.scaffold)).where(ScaffoldEvent.id == event_id)
    )
    if event is None or event.session_id != session.id:
        raise NotFoundError("La ayuda no existe en esta sesión.")
    now = utcnow()
    if action == "ACCEPTED":
        event.accepted = True
        event.rejected = False
        await record_event(
            db,
            session,
            InteractionEventType.HELP_ACCEPTED,
            task_id=event.task_id,
            help_level=event.current_help_level,
            help_type=event.scaffold.scaffold_type if event.scaffold else None,
            help_accepted=True,
            scaffold_event_id=event.id,
            client_meta=client_meta,
        )
        return event, None
    if action == "REJECTED":
        event.rejected = True
        event.accepted = False
        event.result = "REJECTED"
        event.resolved_at = now
        await record_event(
            db,
            session,
            InteractionEventType.HELP_REJECTED,
            task_id=event.task_id,
            help_level=event.current_help_level,
            help_type=event.scaffold.scaffold_type if event.scaffold else None,
            help_rejected=True,
            scaffold_event_id=event.id,
            client_meta=client_meta,
        )
        return event, None
    # REFORMULATE: primero IA opcional validada; si no está activa, falla o es rechazada → variante del banco.
    variants = list(event.scaffold.content.get("variants", [])) if event.scaffold else []
    original = str(event.scaffold.content.get("text", "")) if event.scaffold else (event.delivered_text or "")
    text: str | None = None
    ai_info: dict[str, Any] | None = None
    from app.modules.ai.service import ai_enabled, current_settings, reformulate_hint

    settings = current_settings()
    if settings is not None and ai_enabled() and original:
        task = await db.get(Task, event.task_id)
        student = await db.get(Student, session.student_id)
        if task is not None and student is not None:
            outcome = await reformulate_hint(
                db,
                settings,
                session=session,
                task=task,
                grade=student.grade,
                original=original,
                scaffold_type=event.scaffold.scaffold_type if event.scaffold else None,
                scaffold_event_id=event.id,
            )
            if outcome is not None:
                ai_info = {
                    "ai_interaction_id": str(outcome.interaction_id),
                    "approved": outcome.approved,
                    "reasons": outcome.reasons,
                }
                if outcome.approved and isinstance(outcome.value, str):
                    text = outcome.value
    source = "AI_VALIDATED" if text is not None else "BANK_VARIANT"
    if text is None:
        if not variants:
            raise AppError("Esta ayuda no tiene otra formulación disponible.")
        text = str(variants[event.reformulations % len(variants)])
    event.reformulations += 1
    event.delivered_text = text
    if source == "AI_VALIDATED":
        event.source = "AI_VALIDATED"
        event.decision = {**event.decision, "validation_status": "APPROVED"}
    await record_event(
        db,
        session,
        InteractionEventType.HELP_REFORMULATED,
        task_id=event.task_id,
        help_level=event.current_help_level,
        help_type=event.scaffold.scaffold_type if event.scaffold else None,
        help_content=text,
        scaffold_event_id=event.id,
        client_meta=client_meta,
        ai_interpretation={"reformulation_source": source, **(ai_info or {})},
    )
    offer = HelpOffer(
        scaffold_event_id=event.id,
        offered=True,
        level=event.current_help_level,
        scaffold_type=event.scaffold.scaffold_type if event.scaffold else None,
        text=text,
        can_reformulate=ai_enabled() or event.reformulations < len(variants),
        message="Aquí está la misma idea dicha de otra forma.",
    )
    return event, offer


# --------------------------------------------------------------------------- consultas


async def list_examples(db: AsyncSession, task_id: uuid.UUID) -> list[WorkedExample]:
    result = await db.execute(
        select(WorkedExample)
        .where(WorkedExample.task_id == task_id, WorkedExample.is_active.is_(True))
        .order_by(WorkedExample.order_index)
    )
    return list(result.scalars())


async def session_interactions(
    db: AsyncSession, session_id: uuid.UUID, *, task_id: uuid.UUID | None = None
) -> list[Interaction]:
    stmt = select(Interaction).where(Interaction.session_id == session_id)
    if task_id is not None:
        stmt = stmt.where(Interaction.task_id == task_id)
    result = await db.execute(stmt.order_by(Interaction.sequence))
    return list(result.scalars())


def visible_evaluation(evaluation: dict[str, Any], actor: CurrentUser) -> dict[str, Any] | None:
    """El estudiante no recibe 'correct' ni el patrón de error; sí las dimensiones observadas de su texto."""
    if actor.role == Role.STUDENT:
        dims = evaluation.get("observed_dimensions") or []
        return {"observed_dimensions": dims} if dims else None
    return evaluation
