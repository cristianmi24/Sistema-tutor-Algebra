"""IA opcional: configuración visible (sin secretos) y trazabilidad de cada llamada."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import select

from app.core.auth import AdminDep, ResearchStaffDep
from app.core.deps import DbDep, SettingsDep
from app.modules.learning.scope import accessible_student_ids
from app.modules.tutor.models import AIInteraction

router = APIRouter()


class AIConfigOut(BaseModel):
    enabled: bool
    provider: str
    model: str | None
    timeout_ms: int
    max_calls_per_session: int
    key_configured: bool
    purposes: list[str]
    guarantees: list[str]


class AIInteractionOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID | None
    interaction_id: uuid.UUID | None
    scaffold_event_id: uuid.UUID | None
    provider: str
    model: str | None
    purpose: str
    prompt: dict[str, Any]
    raw_output: str | None
    validation: dict[str, Any]
    approved: bool
    latency_ms: int | None
    created_at: datetime


@router.get("/config", response_model=AIConfigOut, summary="Configuración de la IA opcional (sin secretos)")
async def config(_: AdminDep, settings: SettingsDep) -> AIConfigOut:
    return AIConfigOut(
        enabled=settings.llm_enabled and settings.llm_provider != "null",
        provider=settings.llm_provider,
        model=settings.llm_model if settings.llm_provider == "anthropic" else None,
        timeout_ms=settings.llm_timeout_ms,
        max_calls_per_session=settings.llm_max_calls_per_session,
        key_configured=bool(settings.llm_api_key),
        purposes=["ADAPT_LANGUAGE", "INTERPRET_OPEN_ANSWER"],
        guarantees=[
            "El LLM no decide si intervenir, cuándo ni con qué nivel.",
            "Toda salida pasa por validadores pedagógico, de seguridad y de dominio.",
            "Nada no validado llega al estudiante; ante rechazo se usa el banco.",
            "El LLM no recibe datos personales.",
        ],
    )


@router.get("/interactions", response_model=list[AIInteractionOut], summary="Trazabilidad de llamadas a la IA")
async def interactions(
    user: ResearchStaffDep,
    db: DbDep,
    session_id: uuid.UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[AIInteractionOut]:
    stmt = select(AIInteraction)
    scope = await accessible_student_ids(db, user)
    if scope is not None:
        stmt = stmt.where(AIInteraction.student_id.in_(scope))
    if session_id:
        stmt = stmt.where(AIInteraction.session_id == session_id)
    rows = (await db.execute(stmt.order_by(AIInteraction.created_at.desc()).limit(limit))).scalars()
    return [
        AIInteractionOut(
            id=r.id,
            session_id=r.session_id,
            interaction_id=r.interaction_id,
            scaffold_event_id=r.scaffold_event_id,
            provider=r.provider,
            model=r.model,
            purpose=r.purpose,
            prompt=r.prompt,
            raw_output=r.raw_output,
            validation=r.validation,
            approved=r.approved,
            latency_ms=r.latency_ms,
            created_at=r.created_at,
        )
        for r in rows
    ]
