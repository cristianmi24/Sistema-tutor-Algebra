"""Esquemas Pydantic del motor adaptativo (consulta y administración)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StudentStateOut(BaseModel):
    student_id: uuid.UUID
    participant_code: str | None = None
    session_id: uuid.UUID | None
    task_id: uuid.UUID | None
    current_skill: str | None
    current_difficulty: int | None
    recent_accuracy: float | None
    average_response_time_ms: int | None
    click_pattern: str | None
    attempt_count: int
    repetition_count: int
    error_pattern: str | None
    confidence: float | None
    current_state: str
    previous_state: str | None
    current_help_level: int
    last_intervention_id: uuid.UUID | None
    intervention_result: str | None
    posterior: dict[str, Any]
    updated_at: datetime


class StudentStateHistoryOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    task_id: uuid.UUID | None
    interaction_id: uuid.UUID | None
    previous_state: str
    evidence_snapshot: dict[str, Any]
    posterior: dict[str, Any]
    inferred_state: str
    rule_fired: str | None
    current_state: str
    help_level: int
    fading_action: str
    created_at: datetime


class EvidenceOut(BaseModel):
    id: uuid.UUID
    interaction_id: uuid.UUID
    session_id: uuid.UUID
    task_id: uuid.UUID
    window_size: int
    evidence: dict[str, Any]
    created_at: datetime


class SimulationRequest(StrictModel):
    """Simulación del motor con evidencias dadas (sin tocar datos de estudiantes)."""

    evidence: dict[str, Any] = Field(description="Campos de Evidence; los omitidos toman valores neutros")
    previous_state: str = "NORMAL"
    task_type: str = "FIGURAL_PATTERN"
    skill: str = "FUNCTIONAL_RELATION"
    memory: list[dict[str, Any]] = Field(default_factory=list)


class SimulationResult(BaseModel):
    evidence: dict[str, Any]
    posterior: dict[str, Any]
    rule_result: dict[str, Any]
    decision: dict[str, Any]


class TutorRuleOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None
    priority: int
    min_consecutive: int
    conditions: dict[str, Any]
    actions: dict[str, Any]
    version: int
    is_active: bool


class TutorRuleIn(StrictModel):
    code: str = Field(min_length=2, max_length=48, pattern=r"^[A-Z0-9_-]+$")
    name: str = Field(min_length=2, max_length=200)
    description: str | None = None
    priority: int = 0
    min_consecutive: int = Field(default=1, ge=1, le=5)
    conditions: dict[str, Any]
    actions: dict[str, Any]
    is_active: bool = True


class BayesianConfigOut(BaseModel):
    id: uuid.UUID
    name: str
    version: int
    priors: dict[str, Any]
    likelihoods: dict[str, Any]
    thresholds: dict[str, Any]
    is_active: bool


class BayesianConfigIn(StrictModel):
    name: str = Field(min_length=2, max_length=64)
    priors: dict[str, float]
    likelihoods: dict[str, dict[str, dict[str, float]]]
    thresholds: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
