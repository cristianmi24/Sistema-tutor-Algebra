"""ADAPTAR: selección de andamiaje del banco con memoria de intervención y política de fading."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.modules.tutor.evidence import ScaffoldRecord

# Tipos del banco compatibles con cada tipo de intervención decidido por las reglas.
INTERVENTION_TYPES: dict[str, list[str]] = {
    "FOCUSING": ["FOCUSING", "METACOGNITIVE"],
    "METACOGNITIVE": ["METACOGNITIVE", "FOCUSING"],
    "GUIDING_QUESTION": ["GUIDING_QUESTION", "SELF_EXPLANATION"],
    "SELF_EXPLANATION": ["SELF_EXPLANATION", "METACOGNITIVE", "GUIDING_QUESTION"],
    "HINT": ["HINT", "TASK_DIVISION", "ERROR_REFLECTION"],
    "TASK_DIVISION": ["TASK_DIVISION", "HINT"],
    "ERROR_REFLECTION": ["ERROR_REFLECTION", "HINT", "GUIDING_QUESTION"],
    "REPRESENTATION_CHANGE": ["REPRESENTATION_CHANGE", "STRATEGY_COMPARISON"],
    "STRATEGY_COMPARISON": ["STRATEGY_COMPARISON", "REPRESENTATION_CHANGE"],
    "RECOVERY": ["RECOVERY", "REPRESENTATION_CHANGE"],
}

LEVEL_TYPES: dict[int, list[str]] = {
    1: ["FOCUSING", "METACOGNITIVE"],
    2: ["GUIDING_QUESTION", "SELF_EXPLANATION"],
    3: ["HINT", "TASK_DIVISION", "ERROR_REFLECTION"],
    4: ["REPRESENTATION_CHANGE", "STRATEGY_COMPARISON"],
    5: ["RECOVERY"],
}


@dataclass(slots=True)
class ScaffoldCandidate:
    code: str
    scaffold_type: str
    level: int
    applicable_task_types: list[str]
    applicable_skills: list[str]
    content: dict[str, Any]


@dataclass(slots=True)
class Selection:
    selected: ScaffoldCandidate | None
    candidates: list[str]
    excluded: dict[str, str]
    reason: str


def _applicable(c: ScaffoldCandidate, task_type: str, skill: str) -> bool:
    return (not c.applicable_task_types or task_type in c.applicable_task_types) and (
        not c.applicable_skills or skill in c.applicable_skills
    )


def select_scaffold(
    bank: list[ScaffoldCandidate],
    *,
    task_type: str,
    skill: str,
    level: int,
    intervention: str | None,
    memory: list[ScaffoldRecord],
) -> Selection:
    """Elige la ayuda de MENOR explicitud compatible, evitando repetir lo rechazado o lo ineficaz.

    Memoria: ninguna ayuda ya ofrecida en la tarea se repite idénticamente (rechazada, sin mejora o
    ya usada); se prefieren tipos no usados. Si el banco se agota, se sugiere acompañamiento docente.
    """
    if level <= 0:
        return Selection(selected=None, candidates=[], excluded={}, reason="Nivel 0: observar sin intervenir.")

    excluded: dict[str, str] = {}
    persisted_counts: dict[str, int] = {}
    used_types: set[str] = set()
    for m in memory:
        if m.code is None:
            continue
        if m.scaffold_type:
            used_types.add(m.scaffold_type)
        if m.rejected or m.result == "REJECTED":
            excluded[m.code] = "rechazada por el estudiante"
        elif m.result == "PERSISTED":
            persisted_counts[m.code] = persisted_counts.get(m.code, 0) + 1
            excluded[m.code] = "ya ofrecida en esta tarea sin mejora"
        elif m.result == "PENDING":
            excluded[m.code] = "ya ofrecida y aún sin resolver"
        else:
            # IMPROVED / UNKNOWN / ABANDONED: no se repite la misma ayuda dentro de la tarea.
            excluded[m.code] = "ya ofrecida en esta tarea"
    for code, count in persisted_counts.items():
        if count >= 2:
            excluded[code] = "sin mejora tras dos usos"

    preferred_types = INTERVENTION_TYPES.get(intervention or "", []) or LEVEL_TYPES.get(level, [])
    applicable = [c for c in bank if _applicable(c, task_type, skill) and c.code not in excluded]

    def rank(c: ScaffoldCandidate) -> tuple[int, int, int, int, str]:
        type_rank = (
            preferred_types.index(c.scaffold_type) if c.scaffold_type in preferred_types else len(preferred_types) + 1
        )
        level_gap = abs(c.level - level)
        over = 1 if c.level > level else 0
        reused = 1 if c.scaffold_type in used_types else 0
        return (over, level_gap, type_rank, reused, c.code)

    ordered = sorted(applicable, key=rank)
    # Primero las del nivel objetivo o inferior; solo si no hay, se admite una de nivel superior.
    at_or_below = [c for c in ordered if c.level <= level]
    pool = at_or_below or ordered
    selected = pool[0] if pool else None
    reason = (
        f"Seleccionada {selected.code} ({selected.scaffold_type}, nivel {selected.level}) como la ayuda de menor "
        f"explicitud compatible con {intervention or 'nivel ' + str(level)}; excluidas: {excluded or 'ninguna'}."
        if selected
        else "No queda ninguna ayuda compatible en el banco: se sugiere acompañamiento docente."
    )
    return Selection(selected=selected, candidates=[c.code for c in pool[:6]], excluded=excluded, reason=reason)


def fading_action(previous_level: int, new_level: int, rule_fading: str) -> str:
    if rule_fading in {"REDUCE", "INCREASE"}:
        return rule_fading
    if new_level < previous_level:
        return "REDUCE"
    if new_level > previous_level:
        return "INCREASE"
    return "KEEP"
