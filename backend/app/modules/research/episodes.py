"""Episodios: detección automática, reconstrucción de trayectoria y resumen descriptivo.

Un episodio se abre ante una solicitud de ayuda, una ayuda ofrecida por el sistema o una
intervención docente, e incorpora el contexto inmediato previo (la "dificultad"). Se cierra cuando
la tarea se completa/abandona, la sesión termina, el estudiante cambia de tarea, o responde
correctamente después de una ayuda ("RESOLVED" es un hecho observable, no una afirmación de
comprensión). El resumen es AUTOMÁTICO y solo contiene conteos y secuencias; nunca categorías.
"""

from __future__ import annotations

import uuid
from collections import Counter
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import utcnow
from app.modules.learning.models import Interaction, LearningSession, ScaffoldEvent, StudentResponse
from app.modules.research.models import Episode, EpisodeInteraction

OPENING_EVENTS = {"HELP_REQUESTED", "HELP_OFFERED", "TEACHER_INTERVENTION"}
CLOSING_EVENTS = {
    "TASK_COMPLETED": "TASK_COMPLETED",
    "TASK_ABANDONED": "TASK_ABANDONED",
    "SESSION_ENDED": "SESSION_ENDED",
}
RESPONSE_EVENTS = {"STUDENT_RESPONSE", "STUDENT_REATTEMPT", "STUDENT_EDITED_RESPONSE"}
CONTEXT_EVENTS_BEFORE = 4

NEED_TO_TRIGGER = {
    "DIFFICULTY": "DIFFICULTY",
    "STAGNATION": "STAGNATION",
    "UNCERTAINTY": "UNCERTAINTY",
    "IMPULSIVITY": "IMPULSIVITY",
    "HELP_REQUESTED": "HELP_REQUEST",
}

# Fases del timeline (C.31): TAREA → RESPUESTA → AYUDA → REACCIÓN → NUEVA RESPUESTA → CAMBIO → RESULTADO.
PHASE_BY_EVENT: dict[str, str] = {
    "SESSION_STARTED": "SESIÓN",
    "SESSION_ENDED": "SESIÓN",
    "TASK_OPENED": "TAREA",
    "STUDENT_RESPONSE": "RESPUESTA",
    "STUDENT_REATTEMPT": "NUEVA RESPUESTA",
    "STUDENT_EDITED_RESPONSE": "NUEVA RESPUESTA",
    "ERROR_DETECTED": "DIFICULTAD",
    "HELP_REQUESTED": "SOLICITUD DE AYUDA",
    "HELP_OFFERED": "AYUDA",
    "HELP_REFORMULATED": "AYUDA",
    "HELP_ACCEPTED": "REACCIÓN",
    "HELP_REJECTED": "REACCIÓN",
    "REPRESENTATION_CHANGED": "CAMBIO",
    "SELF_EXPLANATION": "CAMBIO",
    "EXAMPLE_OPENED": "CAMBIO",
    "TEACHER_INTERVENTION": "INTERVENCIÓN DOCENTE",
    "TASK_COMPLETED": "RESULTADO",
    "TASK_ABANDONED": "RESULTADO",
}

ACTOR_BY_EVENT: dict[str, Literal["STUDENT", "SYSTEM", "TEACHER"]] = {
    "HELP_OFFERED": "SYSTEM",
    "HELP_REFORMULATED": "SYSTEM",
    "ERROR_DETECTED": "SYSTEM",
    "TEACHER_INTERVENTION": "TEACHER",
}


async def open_episode(db: AsyncSession, session_id: uuid.UUID) -> Episode | None:
    return await db.scalar(
        select(Episode)
        .where(Episode.session_id == session_id, Episode.status == "OPEN")
        .order_by(Episode.created_at.desc())
    )


async def _next_order(db: AsyncSession, episode_id: uuid.UUID) -> int:
    current = await db.scalar(
        select(func.max(EpisodeInteraction.order_index)).where(EpisodeInteraction.episode_id == episode_id)
    )
    return (current or 0) + 1


async def _attach(db: AsyncSession, episode: Episode, interaction: Interaction) -> None:
    exists = await db.scalar(
        select(EpisodeInteraction.order_index).where(
            EpisodeInteraction.episode_id == episode.id, EpisodeInteraction.interaction_id == interaction.id
        )
    )
    if exists is None:
        db.add(
            EpisodeInteraction(
                episode_id=episode.id, interaction_id=interaction.id, order_index=await _next_order(db, episode.id)
            )
        )
        await db.flush()


async def close_episode(db: AsyncSession, episode: Episode, reason: str, ended: Interaction | None) -> None:
    episode.status = "CLOSED"
    episode.close_reason = reason
    episode.closed_at = utcnow()
    episode.ended_interaction_id = ended.id if ended else episode.ended_interaction_id
    episode.summary = await compute_summary(db, episode)
    await db.flush()


async def _trigger_for(db: AsyncSession, interaction: Interaction) -> str:
    if interaction.event_type == "HELP_REQUESTED":
        return "HELP_REQUEST"
    if interaction.event_type == "TEACHER_INTERVENTION":
        return "TEACHER"
    if interaction.scaffold_event_id:
        event = await db.get(ScaffoldEvent, interaction.scaffold_event_id)
        if event is not None:
            need = str(event.decision.get("need_detected", ""))
            return NEED_TO_TRIGGER.get(need, "DIFFICULTY")
    return "DIFFICULTY"


async def track_event(db: AsyncSession, session: LearningSession, interaction: Interaction) -> None:
    """Actualiza episodios tras cada evento (llamado desde ``record_event``)."""
    episode = await open_episode(db, session.id)
    event_type = interaction.event_type

    if episode is not None and interaction.task_id is not None and episode.task_id != interaction.task_id:
        await close_episode(db, episode, "TASK_SWITCH", None)
        episode = None

    if episode is None:
        if event_type not in OPENING_EVENTS or interaction.task_id is None:
            return
        episode = Episode(
            student_id=session.student_id,
            session_id=session.id,
            task_id=interaction.task_id,
            trigger=await _trigger_for(db, interaction),
            status="OPEN",
            summary={},
        )
        db.add(episode)
        await db.flush()
        # Contexto previo (la "dificultad"): eventos inmediatamente anteriores de la misma tarea.
        previous = (
            (
                await db.execute(
                    select(Interaction)
                    .where(
                        Interaction.session_id == session.id,
                        Interaction.task_id == interaction.task_id,
                        Interaction.sequence < interaction.sequence,
                    )
                    .order_by(Interaction.sequence.desc())
                    .limit(CONTEXT_EVENTS_BEFORE)
                )
            )
            .scalars()
            .all()
        )
        for prior in reversed(previous):
            await _attach(db, episode, prior)
        episode.started_interaction_id = previous[-1].id if previous else interaction.id
        await _attach(db, episode, interaction)
        return

    await _attach(db, episode, interaction)
    if event_type in CLOSING_EVENTS:
        await close_episode(db, episode, CLOSING_EVENTS[event_type], interaction)
        return
    if event_type in RESPONSE_EVENTS and interaction.response_id is not None:
        response = await db.get(StudentResponse, interaction.response_id)
        had_help = await db.scalar(
            select(func.count())
            .select_from(EpisodeInteraction)
            .join(Interaction, Interaction.id == EpisodeInteraction.interaction_id)
            .where(
                EpisodeInteraction.episode_id == episode.id,
                Interaction.event_type.in_(["HELP_OFFERED", "TEACHER_INTERVENTION"]),
            )
        )
        if response is not None and response.evaluation.get("correct") is True and had_help:
            await close_episode(db, episode, "RESOLVED", interaction)


async def create_manual_episode(
    db: AsyncSession, session: LearningSession, task_id: uuid.UUID, from_sequence: int, to_sequence: int
) -> Episode:
    rows = (
        (
            await db.execute(
                select(Interaction)
                .where(
                    Interaction.session_id == session.id,
                    Interaction.task_id == task_id,
                    Interaction.sequence >= from_sequence,
                    Interaction.sequence <= to_sequence,
                )
                .order_by(Interaction.sequence)
            )
        )
        .scalars()
        .all()
    )
    episode = Episode(
        student_id=session.student_id,
        session_id=session.id,
        task_id=task_id,
        trigger="MANUAL",
        status="CLOSED",
        close_reason="MANUAL",
        started_interaction_id=rows[0].id if rows else None,
        ended_interaction_id=rows[-1].id if rows else None,
        closed_at=utcnow(),
    )
    db.add(episode)
    await db.flush()
    for index, row in enumerate(rows, start=1):
        db.add(EpisodeInteraction(episode_id=episode.id, interaction_id=row.id, order_index=index))
    await db.flush()
    episode.summary = await compute_summary(db, episode)
    return episode


async def episode_interactions(db: AsyncSession, episode_id: uuid.UUID) -> list[Interaction]:
    rows = (
        (
            await db.execute(
                select(Interaction)
                .join(EpisodeInteraction, EpisodeInteraction.interaction_id == Interaction.id)
                .where(EpisodeInteraction.episode_id == episode_id)
                .order_by(Interaction.sequence)
            )
        )
        .scalars()
        .all()
    )
    return list(rows)


async def compute_summary(db: AsyncSession, episode: Episode) -> dict[str, Any]:
    """Resumen descriptivo automático (conteos y secuencias). No interpreta."""
    interactions = await episode_interactions(db, episode.id)
    counts = Counter(i.event_type for i in interactions)
    response_ids = [i.response_id for i in interactions if i.response_id and i.event_type in RESPONSE_EVENTS]
    evaluations: list[dict[str, Any]] = []
    if response_ids:
        evaluations = [
            r.evaluation
            for r in (await db.execute(select(StudentResponse).where(StudentResponse.id.in_(response_ids)))).scalars()
        ]
    representations = [i.representation for i in interactions if i.representation]
    help_levels = [i.help_level for i in interactions if i.event_type == "HELP_OFFERED" and i.help_level is not None]
    help_types = [i.help_type for i in interactions if i.event_type == "HELP_OFFERED" and i.help_type]
    duration = (interactions[-1].timestamp - interactions[0].timestamp).total_seconds() if len(interactions) > 1 else 0
    return {
        "system_generated": True,
        "note": "Resumen descriptivo automático; no constituye una categoría ni una conclusión teórica.",
        "event_counts": dict(counts),
        "responses": len(response_ids),
        "responses_evaluated_correct": sum(1 for e in evaluations if e.get("correct") is True),
        "responses_evaluated_incorrect": sum(1 for e in evaluations if e.get("correct") is False),
        "error_patterns": [e.get("error_pattern") for e in evaluations if e.get("error_pattern")],
        "observed_dimensions": sorted({d for e in evaluations for d in e.get("observed_dimensions", [])}),
        "representations_sequence": representations,
        "help_levels_sequence": help_levels,
        "help_types_sequence": help_types,
        "help_accepted": counts.get("HELP_ACCEPTED", 0),
        "help_rejected": counts.get("HELP_REJECTED", 0),
        "help_reformulated": counts.get("HELP_REFORMULATED", 0),
        "teacher_interventions": counts.get("TEACHER_INTERVENTION", 0),
        "duration_seconds": round(duration, 1),
        "phase_sequence": [PHASE_BY_EVENT.get(i.event_type, i.event_type) for i in interactions],
    }
