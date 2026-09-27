"""Investigación: participantes, episodios, timeline, comparación, memos, entrevistas y exportación."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Query, Request, Response, status
from sqlalchemy import select

from app.core.auth import ResearchStaffDep, StaffDep
from app.core.deps import DbDep
from app.core.errors import ForbiddenError, NotFoundError
from app.modules.common.enums import AuditAction, AuditOutcome, Role
from app.modules.learning.scope import require_student_access
from app.modules.learning.service import load_session
from app.modules.ops.audit import record_audit
from app.modules.research import service
from app.modules.research.episodes import create_manual_episode
from app.modules.research.export import MEDIA_TYPES, Dataset, Format, collect_rows, render
from app.modules.research.models import Interview, ResearchMemo
from app.modules.research.schemas import (
    ComparisonOut,
    EpisodeDetail,
    EpisodeOut,
    InterviewIn,
    InterviewOut,
    InterviewResponseIn,
    InterviewResponseOut,
    ManualEpisodeIn,
    MemoIn,
    MemoOut,
    ParticipantOut,
    TimelineStep,
)

router = APIRouter()


@router.get("/participants", response_model=list[ParticipantOut], summary="Participantes pseudonimizados en alcance")
async def participants(user: StaffDep, db: DbDep) -> list[ParticipantOut]:
    return await service.participants(db, user)


# ----------------------------------------------------------------- episodios


@router.get("/episodes", response_model=list[EpisodeOut])
async def list_episodes(
    user: StaffDep,
    db: DbDep,
    student_id: uuid.UUID | None = None,
    session_id: uuid.UUID | None = None,
    task_id: uuid.UUID | None = None,
    trigger: str | None = Query(default=None, max_length=16),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[EpisodeOut]:
    return await service.list_episodes(
        db, user, student_id=student_id, session_id=session_id, task_id=task_id, trigger=trigger, limit=limit
    )


@router.post(
    "/episodes",
    response_model=EpisodeOut,
    status_code=status.HTTP_201_CREATED,
    summary="Crear episodio manual a partir de un rango",
)
async def manual_episode(payload: ManualEpisodeIn, user: ResearchStaffDep, db: DbDep) -> EpisodeOut:
    session = await load_session(db, payload.session_id)
    await require_student_access(db, user, session.student_id)
    episode = await create_manual_episode(db, session, payload.task_id, payload.from_sequence, payload.to_sequence)
    return await service.episode_out(db, episode)


@router.get(
    "/episodes/compare", response_model=ComparisonOut, summary="Comparar Episodio A vs. Episodio B (descriptivo)"
)
async def compare(user: StaffDep, db: DbDep, a: uuid.UUID, b: uuid.UUID) -> ComparisonOut:
    ep_a = await service.get_accessible_episode(db, user, a)
    ep_b = await service.get_accessible_episode(db, user, b)
    return await service.compare(db, ep_a, ep_b)


@router.get("/episodes/{episode_id}", response_model=EpisodeDetail)
async def episode_detail(episode_id: uuid.UUID, user: StaffDep, db: DbDep) -> EpisodeDetail:
    episode = await service.get_accessible_episode(db, user, episode_id)
    return await service.episode_detail(db, episode)


@router.get("/episodes/{episode_id}/timeline", response_model=list[TimelineStep])
async def episode_timeline(episode_id: uuid.UUID, user: StaffDep, db: DbDep) -> list[TimelineStep]:
    from app.modules.research.episodes import episode_interactions

    episode = await service.get_accessible_episode(db, user, episode_id)
    return await service.timeline(db, await episode_interactions(db, episode.id))


@router.get(
    "/sessions/{session_id}/timeline", response_model=list[TimelineStep], summary="Timeline completo de una sesión"
)
async def session_timeline(session_id: uuid.UUID, user: StaffDep, db: DbDep) -> list[TimelineStep]:
    from app.modules.learning.service import session_interactions

    session = await load_session(db, session_id)
    await require_student_access(db, user, session.student_id)
    return await service.timeline(db, await session_interactions(db, session.id))


# ----------------------------------------------------------------- memos


@router.get("/memos", response_model=list[MemoOut])
async def list_memos(
    user: ResearchStaffDep, db: DbDep, episode_id: uuid.UUID | None = None, tag: str | None = None
) -> list[MemoOut]:
    stmt = select(ResearchMemo)
    if user.role == Role.RESEARCHER:
        stmt = stmt.where(ResearchMemo.researcher_id == user.researcher_id)
    if episode_id:
        stmt = stmt.where(ResearchMemo.episode_id == episode_id)
    if tag:
        stmt = stmt.where(ResearchMemo.tags.contains([tag]))
    rows = (await db.execute(stmt.order_by(ResearchMemo.updated_at.desc()))).scalars()
    return [await service.memo_out(db, m) for m in rows]


@router.post("/memos", response_model=MemoOut, status_code=status.HTTP_201_CREATED)
async def create_memo(payload: MemoIn, user: ResearchStaffDep, db: DbDep) -> MemoOut:
    return await service.memo_out(db, await service.save_memo(db, user, payload))


@router.put("/memos/{memo_id}", response_model=MemoOut)
async def update_memo(memo_id: uuid.UUID, payload: MemoIn, user: ResearchStaffDep, db: DbDep) -> MemoOut:
    memo = await db.get(ResearchMemo, memo_id)
    if memo is None:
        raise NotFoundError("Memo no encontrado.")
    return await service.memo_out(db, await service.save_memo(db, user, payload, memo))


@router.delete("/memos/{memo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memo(memo_id: uuid.UUID, user: ResearchStaffDep, db: DbDep) -> Response:
    memo = await db.get(ResearchMemo, memo_id)
    if memo is None:
        raise NotFoundError("Memo no encontrado.")
    if memo.researcher_id != service.require_researcher(user):
        raise ForbiddenError("Solo quien escribió el memo puede eliminarlo.")
    await db.delete(memo)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ----------------------------------------------------------------- entrevistas


@router.get("/interviews", response_model=list[InterviewOut])
async def list_interviews(user: ResearchStaffDep, db: DbDep) -> list[InterviewOut]:
    stmt = select(Interview)
    if user.role == Role.RESEARCHER:
        stmt = stmt.where(Interview.researcher_id == user.researcher_id)
    rows = (await db.execute(stmt.order_by(Interview.conducted_at.desc()))).scalars()
    return [await service.interview_out(db, i) for i in rows]


@router.post("/interviews", response_model=InterviewOut, status_code=status.HTTP_201_CREATED)
async def create_interview(payload: InterviewIn, user: ResearchStaffDep, db: DbDep) -> InterviewOut:
    return await service.interview_out(db, await service.create_interview(db, user, payload))


@router.post(
    "/interviews/{interview_id}/responses", response_model=InterviewResponseOut, status_code=status.HTTP_201_CREATED
)
async def add_response(
    interview_id: uuid.UUID, payload: InterviewResponseIn, user: ResearchStaffDep, db: DbDep
) -> InterviewResponseOut:
    interview = await db.get(Interview, interview_id)
    if interview is None:
        raise NotFoundError("Entrevista no encontrada.")
    row = await service.add_interview_response(db, user, interview, payload)
    return InterviewResponseOut(
        id=row.id,
        order_index=row.order_index,
        question=row.question,
        answer=row.answer,
        related_episode_id=row.related_episode_id,
        observations=row.observations,
        memo_id=row.memo_id,
    )


# ----------------------------------------------------------------- exportación


@router.get("/export", summary="Exportar datos pseudonimizados (auditado)")
async def export(
    request: Request,
    user: StaffDep,
    db: DbDep,
    dataset: Dataset,
    format: Format = "csv",
    session_id: uuid.UUID | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> Response:
    if user.role == Role.TEACHER and dataset not in ("sessions", "interactions", "episodes"):
        raise ForbiddenError(
            "El personal docente solo puede exportar sesiones, interacciones y episodios de sus grupos."
        )
    rows = await collect_rows(db, user, dataset, session_id=session_id, since=since, until=until)
    content = render(rows, format, title=dataset)
    await record_audit(
        db,
        action=AuditAction.EXPORT_GENERATED,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=user.id,
        actor_role=user.role.value,
        resource_type="export",
        resource_id=dataset,
        details={
            "dataset": dataset,
            "format": format,
            "rows": len(rows),
            "session_id": str(session_id) if session_id else None,
        },
        request=request,
    )
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    return Response(
        content=content,
        media_type=MEDIA_TYPES[format],
        headers={"Content-Disposition": f'attachment; filename="sti-ga_{dataset}_{stamp}.{format}"'},
    )
