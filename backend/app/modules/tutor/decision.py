"""EXPLICAR: estructura de la decisión de andamiaje (validada con Pydantic)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ScaffoldDecision(BaseModel):
    need_detected: str = Field(description="Estado/necesidad estimada, p.ej. STAGNATION o HELP_REQUESTED")
    evidence: list[str] = Field(description="Evidencias observadas, legibles: 'error_pattern=PERSISTENT'")
    candidate_supports: list[str] = Field(default_factory=list)
    selected_support: str | None = None
    explicitness_level: int = Field(ge=0, le=5)
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    validation_status: Literal["NOT_REQUIRED", "APPROVED", "REJECTED"] = "NOT_REQUIRED"
    rule_code: str | None = None
    rule_name: str | None = None
    matched_rules: list[str] = Field(default_factory=list)
    previous_state: str
    inferred_state: str
    posterior: dict[str, Any] = Field(default_factory=dict)
    previous_help_level: int = Field(ge=0, le=5)
    fading_action: Literal["KEEP", "REDUCE", "INCREASE"] = "KEEP"
    constraints: list[str] = Field(
        default_factory=list, description="Restricciones aplicadas: pausa docente, tope de intervenciones…"
    )
    suggest_teacher: bool = False

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
