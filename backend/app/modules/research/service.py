"""Servicios de investigación: participantes, episodios (timeline y comparación), memos y entrevistas."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.core.errors import ForbiddenError, NotFoundError
from app.modules.common.enums import Role
from app.modules.identity.models import Institution, Researcher, Student, Teacher
from app.modules.learning.models import (
    Interaction,
    LearningSession,
    ScaffoldEvent,
    SessionTask,
    StudentResponse,
    Task,
    TeacherIntervention,
)
from app.modules.learning.scope import accessible_student_ids, require_student_access
from app.modules.research.episodes import ACTOR_BY_EVENT, PHASE_BY_EVENT, compute_summary, episode_interactions
from app.modules.research.models import Episode, EpisodeInteraction, Interview, InterviewResponse, ResearchMemo
from app.modules.research.schemas import (
    ComparisonOut,
    EpisodeDetail,
    EpisodeOut,
    InterviewIn,
    InterviewOut,
    InterviewResponseOut,
    MemoIn,
    MemoOut,
    ParticipantOut,
    TimelineStep,
)
from app.modules.tutor.models import StudentStateHistory

# ------------------------------------------------------------------ participantes


async def participants(db: AsyncSession, actor: CurrentUser) -> list[ParticipantOut]:
    ids = await accessible_student_ids(db, actor)
    stmt = select(Student, Institution.code).join(Institution, Institution.id == Student.institution_id)
    if ids is not None:
        stmt = stmt.where(Student.id.in_(ids))
    rows = (await db.execute(stmt.order_by(Institution.code, Student.participant_code))).all()
    out: list[ParticipantOut] = []
    for student, institution_code in rows:
        sessions = (
            await db.scalar(
                select(func.count()).select_from(LearningSession).where(LearningSession.student_id == student.id)
            )
            or 0
        )
        tasks_worked = (
            await db.scalar(
                select(func.count(func.distinct(SessionTask.task_id)))
                .join(LearningSession, LearningSession.id == SessionTask.session_id)
                .where(LearningSession.student_id == student.id, SessionTask.status != "PENDING")
            )
            or 0
        )
        interactions = (
            await db.scalar(select(func.count()).select_from(Interaction).where(Interaction.student_id == student.id))
            or 0
        )
        episodes = (
            await db.scalar(select(func.count()).select_from(Episode).where(Episode.student_id == student.id)) or 0
        )
        out.append(
            ParticipantOut(
                student_id=student.id,
                participant_code=student.participant_code,
                grade=student.grade,
                group_code=student.group_code,
                institution_code=institution_code,
                research_status=student.research_status,
                sessions=sessions,
                tasks_worked=tasks_worked,
                interactions=interactions,
                episodes=episodes,
            )
        )
    return out


# ------------------------------------------------------------------ episodios


async def _codes(db: AsyncSession, student_ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not student_ids:
        return {}
    rows = (await db.execute(select(Student.id, Student.participant_code).where(Student.id.in_(student_ids)))).all()
    return {sid: code for sid, code in rows}


async def episode_out(db: AsyncSession, episode: Episode, code: str | None = None) -> EpisodeOut:
    task = await db.get(Task, episode.task_id)
    count = (
        await db.scalar(
            select(func.count()).select_from(EpisodeInteraction).where(EpisodeInteraction.episode_id == episode.id)
        )
        or 0
    )
    summary = episode.summary or (await compute_summary(db, episode))
    if code is None:
        code = (await _codes(db, {episode.student_id})).get(episode.student_id)
    return EpisodeOut(
        id=episode.id,
        student_id=episode.student_id,
        participant_code=code,
        session_id=episode.session_id,
        task_id=episode.task_id,
        task_code=task.code if task else None,
        task_title=task.title if task else None,
        trigger=episode.trigger,
        status=episode.status,
        close_reason=episode.close_reason,
        summary=summary,
        created_at=episode.created_at,
        closed_at=episode.closed_at,
        interaction_count=count,
    )


async def list_episodes(
    db: AsyncSession,
    actor: CurrentUser,
    *,
    student_id: uuid.UUID | None = None,
    session_id: uuid.UUID | None = None,
    task_id: uuid.UUID | None = None,
    trigger: str | None = None,
    limit: int = 100,
) -> list[EpisodeOut]:
    ids = await accessible_student_ids(db, actor)
    stmt = select(Episode)
    if ids is not None:
        stmt = stmt.where(Episode.student_id.in_(ids))
    if student_id:
        stmt = stmt.where(Episode.student_id == student_id)
    if session_id:
        stmt = stmt.where(Episode.session_id == session_id)
    if task_id:
        stmt = stmt.where(Episode.task_id == task_id)
    if trigger:
        stmt = stmt.where(Episode.trigger == trigger)
    episodes = list((await db.execute(stmt.order_by(Episode.created_at.desc()).limit(limit))).scalars())
    codes = await _codes(db, {e.student_id for e in episodes})
    return [await episode_out(db, e, codes.get(e.student_id)) for e in episodes]


async def get_accessible_episode(db: AsyncSession, actor: CurrentUser, episode_id: uuid.UUID) -> Episode:
    episode = await db.get(Episode, episode_id)
    if episode is None:
        raise NotFoundError("Episodio no encontrado.")
    await require_student_access(db, actor, episode.student_id)
    return episode


async def timeline(db: AsyncSession, interactions: list[Interaction]) -> list[TimelineStep]:
    ids = [i.id for i in interactions]
    response_ids = [i.response_id for i in interactions if i.response_id]
    scaffold_ids = [i.scaffold_event_id for i in interactions if i.scaffold_event_id]
    teacher_ids = [i.teacher_intervention_id for i in interactions if i.teacher_intervention_id]
    responses = (
        {
            r.id: r
            for r in (await db.execute(select(StudentResponse).where(StudentResponse.id.in_(response_ids)))).scalars()
        }
        if response_ids
        else {}
    )
    scaffolds = (
        {s.id: s for s in (await db.execute(select(ScaffoldEvent).where(ScaffoldEvent.id.in_(scaffold_ids)))).scalars()}
        if scaffold_ids
        else {}
    )
    teacher = (
        {
            t.id: t
            for t in (
                await db.execute(select(TeacherIntervention).where(TeacherIntervention.id.in_(teacher_ids)))
            ).scalars()
        }
        if teacher_ids
        else {}
    )
    states = (
        {
            h.interaction_id: h
            for h in (
                await db.execute(select(StudentStateHistory).where(StudentStateHistory.interaction_id.in_(ids)))
            ).scalars()
        }
        if ids
        else {}
    )

    steps: list[TimelineStep] = []
    for i in interactions:
        response = responses.get(i.response_id) if i.response_id else None
        scaffold = scaffolds.get(i.scaffold_event_id) if i.scaffold_event_id else None
        intervention = teacher.get(i.teacher_intervention_id) if i.teacher_intervention_id else None
        state = states.get(i.id)
        steps.append(
            TimelineStep(
                sequence=i.sequence,
                timestamp=i.timestamp,
                phase=PHASE_BY_EVENT.get(i.event_type, i.event_type),
                event_type=i.event_type,
                actor=ACTOR_BY_EVENT.get(i.event_type, "STUDENT"),
                representation=i.representation,
                content=i.student_response,
                help_level=i.help_level,
                help_type=i.help_type,
                help_text=i.help_content,
                evaluation=response.evaluation if response else None,
                teacher_intervention=(
                    {
                        "type": intervention.intervention_type,
                        "content": intervention.content,
                        "visibility": intervention.visibility,
                    }
                    if intervention
                    else None
                ),
                system_interpretation=(
                    {
                        "label": "interpretación operativa del sistema",
                        "previous_state": state.previous_state,
                        "inferred_state": state.inferred_state,
                        "current_state": state.current_state,
                        "rule_fired": state.rule_fired,
                        "help_level": state.help_level,
                        "fading_action": state.fading_action,
                        "posterior": state.posterior,
                    }
                    if state
                    else None
                ),
                scaffold_decision=scaffold.decision if scaffold else None,
                client_meta=i.client_meta,
            )
        )
    return steps


async def memo_out(db: AsyncSession, memo: ResearchMemo) -> MemoOut:
    researcher = await db.get(Researcher, memo.researcher_id)
    code = (await _codes(db, {memo.student_id})).get(memo.student_id) if memo.student_id else None
    return MemoOut(
        id=memo.id,
        researcher_code=researcher.display_code if researcher else None,
        title=memo.title,
        episode_id=memo.episode_id,
        participant_code=code,
        session_id=memo.session_id,
        task_id=memo.task_id,
        observation=memo.observation,
        interpretation=memo.interpretation,
        emerging_question=memo.emerging_question,
        contradiction=memo.contradiction,
        negative_case=memo.negative_case,
        possible_category=memo.possible_category,
        theoretical_sampling_need=memo.theoretical_sampling_need,
        tags=list(memo.tags),
        created_at=memo.created_at,
        updated_at=memo.updated_at,
    )


async def episode_detail(db: AsyncSession, episode: Episode) -> EpisodeDetail:
    base = await episode_out(db, episode)
    interactions = await episode_interactions(db, episode.id)
    task = await db.get(Task, episode.task_id)
    memos = (
        await db.execute(
            select(ResearchMemo).where(ResearchMemo.episode_id == episode.id).order_by(ResearchMemo.created_at)
        )
    ).scalars()
    context = {
        "task": {
            "code": task.code,
            "title": task.title,
            "task_type": task.task_type,
            "skill": task.skill,
            "difficulty": task.difficulty,
            "prompt": task.statement.get("prompt"),
        }
        if task
        else None,
        "trigger": episode.trigger,
        "trigger_label": "disparador registrado por el sistema",
    }
    return EpisodeDetail(
        **base.model_dump(),
        context=context,
        timeline=await timeline(db, interactions),
        memos=[await memo_out(db, m) for m in memos],
    )


async def compare(db: AsyncSession, a: Episode, b: Episode) -> ComparisonOut:
    """Comparación descriptiva lado a lado. No produce conclusiones."""
    out_a, out_b = await episode_out(db, a), await episode_out(db, b)
    steps_a = await timeline(db, await episode_interactions(db, a.id))
    steps_b = await timeline(db, await episode_interactions(db, b.id))

    def dims(ep: EpisodeOut, steps: list[TimelineStep]) -> dict[str, Any]:
        s = ep.summary
        return {
            "contexto": {"task_code": ep.task_code, "task_title": ep.task_title, "trigger": ep.trigger},
            "estrategia": {
                "observed_dimensions": s.get("observed_dimensions", []),
                "error_patterns": s.get("error_patterns", []),
            },
            "representación": s.get("representations_sequence", []),
            "ayuda": {"levels": s.get("help_levels_sequence", []), "types": s.get("help_types_sequence", [])},
            "reacción": {
                "accepted": s.get("help_accepted", 0),
                "rejected": s.get("help_rejected", 0),
                "reformulated": s.get("help_reformulated", 0),
            },
            "intervención_docente": [st.teacher_intervention for st in steps if st.teacher_intervention],
            "trayectoria": [st.phase for st in steps],
            "cierre": ep.close_reason,
        }

    keys = [
        "contexto",
        "estrategia",
        "representación",
        "ayuda",
        "reacción",
        "intervención_docente",
        "trayectoria",
        "cierre",
    ]
    da, db_ = dims(out_a, steps_a), dims(out_b, steps_b)
    return ComparisonOut(
        a=out_a,
        b=out_b,
        dimensions={k: {"a": da[k], "b": db_[k]} for k in keys},
        note="Comparación descriptiva de registros. El sistema no produce conclusiones ni categorías teóricas.",
    )


# ------------------------------------------------------------------ memos y entrevistas


async def _student_by_code(db: AsyncSession, actor: CurrentUser, code: str | None) -> Student | None:
    if not code:
        return None
    stmt = select(Student).where(Student.participant_code == code)
    if actor.institution_id is not None:
        stmt = stmt.where(Student.institution_id == actor.institution_id)
    student = await db.scalar(stmt)
    if student is None:
        raise NotFoundError("Participante no encontrado.")
    return await require_student_access(db, actor, student.id)


def require_researcher(actor: CurrentUser) -> uuid.UUID:
    if actor.role != Role.RESEARCHER or actor.researcher_id is None:
        raise ForbiddenError("Solo el personal investigador puede crear o editar memos y entrevistas.")
    return actor.researcher_id


async def save_memo(
    db: AsyncSession, actor: CurrentUser, payload: MemoIn, memo: ResearchMemo | None = None
) -> ResearchMemo:
    researcher_id = require_researcher(actor)
    if memo is not None and memo.researcher_id != researcher_id:
        raise ForbiddenError("Solo quien escribió el memo puede editarlo.")
    student = await _student_by_code(db, actor, payload.participant_code)
    if payload.episode_id:
        episode = await get_accessible_episode(db, actor, payload.episode_id)
        student = student or await db.get(Student, episode.student_id)
    data = payload.model_dump(exclude={"participant_code"})
    if memo is None:
        memo = ResearchMemo(researcher_id=researcher_id, **data)
        db.add(memo)
    else:
        for key, value in data.items():
            setattr(memo, key, value)
    memo.student_id = student.id if student else None
    await db.flush()
    await db.refresh(memo)
    return memo


async def interview_out(db: AsyncSession, interview: Interview) -> InterviewOut:
    researcher = await db.get(Researcher, interview.researcher_id)
    code = (await _codes(db, {interview.student_id})).get(interview.student_id) if interview.student_id else None
    teacher = await db.get(Teacher, interview.teacher_id) if interview.teacher_id else None
    responses = (
        await db.execute(
            select(InterviewResponse)
            .where(InterviewResponse.interview_id == interview.id)
            .order_by(InterviewResponse.order_index)
        )
    ).scalars()
    return InterviewOut(
        id=interview.id,
        researcher_code=researcher.display_code if researcher else None,
        title=interview.title,
        interviewee_kind=interview.interviewee_kind,
        participant_code=code,
        teacher_code=teacher.display_code if teacher else None,
        session_id=interview.session_id,
        task_id=interview.task_id,
        episode_id=interview.episode_id,
        conducted_at=interview.conducted_at,
        notes=interview.notes,
        created_at=interview.created_at,
        responses=[
            InterviewResponseOut(
                id=r.id,
                order_index=r.order_index,
                question=r.question,
                answer=r.answer,
                related_episode_id=r.related_episode_id,
                observations=r.observations,
                memo_id=r.memo_id,
            )
            for r in responses
        ],
    )


async def create_interview(db: AsyncSession, actor: CurrentUser, payload: InterviewIn) -> Interview:
    researcher_id = require_researcher(actor)
    student = (
        await _student_by_code(db, actor, payload.participant_code) if payload.interviewee_kind == "STUDENT" else None
    )
    teacher: Teacher | None = None
    if payload.interviewee_kind == "TEACHER":
        stmt = select(Teacher).where(Teacher.display_code == payload.teacher_code)
        if actor.institution_id is not None:
            stmt = stmt.where(Teacher.institution_id == actor.institution_id)
        teacher = await db.scalar(stmt)
        if teacher is None:
            raise NotFoundError("Docente no encontrado.")
    if payload.episode_id:
        await get_accessible_episode(db, actor, payload.episode_id)
    interview = Interview(
        researcher_id=researcher_id,
        interviewee_kind=payload.interviewee_kind,
        student_id=student.id if student else None,
        teacher_id=teacher.id if teacher else None,
        session_id=payload.session_id,
        task_id=payload.task_id,
        episode_id=payload.episode_id,
        title=payload.title,
        conducted_at=payload.conducted_at,
        notes=payload.notes,
    )
    db.add(interview)
    await db.flush()
    for index, response in enumerate(payload.responses, start=1):
        db.add(InterviewResponse(interview_id=interview.id, order_index=index, **response.model_dump()))
    await db.flush()
    await db.refresh(interview)
    return interview


async def add_interview_response(
    db: AsyncSession, actor: CurrentUser, interview: Interview, payload: Any
) -> InterviewResponse:
    researcher_id = require_researcher(actor)
    if interview.researcher_id != researcher_id:
        raise ForbiddenError("Solo quien registró la entrevista puede añadir respuestas.")
    current = await db.scalar(
        select(func.max(InterviewResponse.order_index)).where(InterviewResponse.interview_id == interview.id)
    )
    row = InterviewResponse(interview_id=interview.id, order_index=(current or 0) + 1, **payload.model_dump())
    db.add(row)
    await db.flush()
    return row
