"""Servicio de IA opcional: reformulación de ayudas del banco e interpretación de explicaciones.

Siempre: límite de llamadas por sesión, validación triple, registro en ``ai_interactions`` y
respaldo determinista. El LLM nunca recibe datos personales (solo contenido de la tarea).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.logging import get_logger
from app.modules.ai.providers import LLMRequest, LLMResponse, build_provider
from app.modules.ai.validators import OBSERVABLE_DIMENSIONS, ValidationResult, validate_hint, validate_interpretation
from app.modules.learning.models import LearningSession, Task
from app.modules.tutor.models import AIInteraction

log = get_logger("app.ai")

_settings: Settings | None = None


def configure_ai(settings: Settings) -> None:
    global _settings
    _settings = settings


def current_settings() -> Settings | None:
    return _settings


def ai_enabled() -> bool:
    return bool(_settings and _settings.llm_enabled and _settings.llm_provider != "null")


GRADE_STYLE = {"7": "12–13 años", "8": "13–14 años", "9": "14–15 años"}

HINT_SYSTEM = (
    "Eres un asistente de redacción para un tutor de matemáticas escolar en español. Reformulas UNA ayuda pedagógica "
    "ya aprobada por docentes para que suene natural a estudiantes de {age}. Reglas estrictas: conserva exactamente la "
    "intención y el nivel de ayuda; no añadas pasos, pistas, números ni ejemplos nuevos; nunca des la respuesta, "
    "la regla ni la fórmula; no evalúes al estudiante; si la ayuda original es una pregunta, la reformulación "
    "también lo es; máximo dos frases. Responde solo con el JSON pedido."
)

INTERPRET_SYSTEM = (
    "Eres un asistente de codificación descriptiva para una investigación educativa. Recibes la explicación escrita de "
    "un estudiante sobre un patrón. Marca SOLO las dimensiones observables del vocabulario cerrado que aparecen "
    "explícitamente en el texto. No juzgues si es correcta, no infieras comprensión, no propongas categorías nuevas. "
    "Vocabulario: {vocab}. Responde solo con el JSON pedido."
)

HINT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"text": {"type": "string"}},
    "required": ["text"],
    "additionalProperties": False,
}

INTERPRET_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "dimensions": {"type": "array", "items": {"type": "string", "enum": list(OBSERVABLE_DIMENSIONS)}},
        "confidence": {"type": "number"},
        "note": {"type": "string"},
    },
    "required": ["dimensions", "confidence", "note"],
    "additionalProperties": False,
}


@dataclass(slots=True)
class AIOutcome:
    approved: bool
    value: Any
    interaction_id: Any
    reasons: list[str]


def _hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


async def _within_budget(db: AsyncSession, settings: Settings, session_id: Any) -> bool:
    used = (
        await db.scalar(select(func.count()).select_from(AIInteraction).where(AIInteraction.session_id == session_id))
        or 0
    )
    return used < settings.llm_max_calls_per_session


async def _record(
    db: AsyncSession,
    *,
    session: LearningSession,
    purpose: str,
    request: LLMRequest,
    response: LLMResponse | None,
    validation: ValidationResult,
    interaction_id: Any = None,
    scaffold_event_id: Any = None,
    provider: str,
    model: str | None,
) -> AIInteraction:
    prompt = {"system": request.system, "user": request.user, "schema": request.json_schema}
    row = AIInteraction(
        session_id=session.id,
        student_id=session.student_id,
        interaction_id=interaction_id,
        scaffold_event_id=scaffold_event_id,
        provider=provider,
        model=model,
        purpose=purpose,
        prompt_hash=_hash(prompt),
        prompt=prompt,
        raw_output=response.text if response else None,
        validation={
            **validation.as_dict(),
            "provider_error": response.error if response else "not_called",
            "meta": response.meta if response else {},
        },
        approved=validation.approved,
        latency_ms=response.latency_ms if response else None,
    )
    db.add(row)
    await db.flush()
    return row


def protected_positions(task: Task) -> list[int]:
    positions: list[int] = []
    for q in task.statement.get("questions", []):
        if isinstance(q.get("position"), int):
            positions.append(q["position"])
        positions.extend(p for p in q.get("positions", []) if isinstance(p, int))
    return positions


async def reformulate_hint(
    db: AsyncSession,
    settings: Settings,
    *,
    session: LearningSession,
    task: Task,
    grade: str,
    original: str,
    scaffold_type: str | None,
    scaffold_event_id: Any,
) -> AIOutcome | None:
    """Propone una reformulación validada. ``None`` si la IA está desactivada o sin presupuesto."""
    provider = build_provider(settings)
    if provider.name == "null" or not await _within_budget(db, settings, session.id):
        return None
    request = LLMRequest(
        purpose="ADAPT_LANGUAGE",
        system=HINT_SYSTEM.format(age=GRADE_STYLE.get(grade, "12–15 años")),
        user=json.dumps(
            {
                "ayuda_original": original,
                "tipo_de_ayuda": scaffold_type,
                "contexto_de_la_tarea": task.statement.get("prompt"),
            },
            ensure_ascii=False,
        ),
        json_schema=HINT_SCHEMA,
        max_tokens=1024,
    )
    response = await provider.complete(request)
    if response.ok:
        text, validation = validate_hint(
            response.data,
            original=original,
            scaffold_type=scaffold_type,
            rule=task.solution.get("expression"),
            protected_positions=protected_positions(task),
        )
    else:
        text, validation = None, ValidationResult(approved=False, reasons=[f"proveedor: {response.error}"])
    row = await _record(
        db,
        session=session,
        purpose="ADAPT_LANGUAGE",
        request=request,
        response=response,
        validation=validation,
        scaffold_event_id=scaffold_event_id,
        provider=provider.name,
        model=provider.model,
    )
    log.info("ai_reformulation", approved=validation.approved, reasons=validation.reasons)
    return AIOutcome(approved=validation.approved, value=text, interaction_id=row.id, reasons=validation.reasons)


async def interpret_explanation(
    db: AsyncSession,
    settings: Settings,
    *,
    session: LearningSession,
    task: Task,
    text: str,
    interaction_id: Any,
) -> AIOutcome | None:
    provider = build_provider(settings)
    if provider.name == "null" or not text.strip() or not await _within_budget(db, settings, session.id):
        return None
    request = LLMRequest(
        purpose="INTERPRET_OPEN_ANSWER",
        system=INTERPRET_SYSTEM.format(vocab=", ".join(OBSERVABLE_DIMENSIONS)),
        user=json.dumps(
            {"tarea": task.statement.get("prompt"), "explicacion_del_estudiante": text[:2000]}, ensure_ascii=False
        ),
        json_schema=INTERPRET_SCHEMA,
        max_tokens=1024,
    )
    response = await provider.complete(request)
    value, validation = (
        validate_interpretation(response.data)
        if response.ok
        else (None, ValidationResult(approved=False, reasons=[f"proveedor: {response.error}"]))
    )
    row = await _record(
        db,
        session=session,
        purpose="INTERPRET_OPEN_ANSWER",
        request=request,
        response=response,
        validation=validation,
        interaction_id=interaction_id,
        provider=provider.name,
        model=provider.model,
    )
    return AIOutcome(approved=validation.approved, value=value, interaction_id=row.id, reasons=validation.reasons)
