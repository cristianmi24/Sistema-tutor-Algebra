"""Esquemas del módulo docente."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


InterventionType = Literal["QUESTION", "COMMENT", "OBSERVATION", "REDIRECTION", "ENCOURAGEMENT"]


class InterventionIn(StrictModel):
    session_id: uuid.UUID
    task_id: uuid.UUID | None = None
    intervention_type: InterventionType
    content: str = Field(min_length=1, max_length=2000)
    visibility: Literal["STUDENT", "RESEARCH_ONLY"] = "STUDENT"


class InterventionOut(BaseModel):
    id: uuid.UUID
    teacher_code: str | None
    student_id: uuid.UUID
    participant_code: str | None
    session_id: uuid.UUID
    task_id: uuid.UUID | None
    interaction_id: uuid.UUID | None
    intervention_type: str
    content: str
    visibility: str
    student_seen_at: datetime | None
    created_at: datetime
    source: Literal["TEACHER"] = "TEACHER"


class StudentMessageOut(BaseModel):
    """Lo que ve el estudiante: el mensaje de su docente (sin metadatos internos)."""

    id: uuid.UUID
    task_id: uuid.UUID | None
    intervention_type: str
    content: str
    created_at: datetime
    seen: bool


class StudentOverview(BaseModel):
    student_id: uuid.UUID
    participant_code: str
    grade: str
    group_code: str | None
    account_status: str
    active_session_id: uuid.UUID | None
    current_task_code: str | None
    current_task_title: str | None
    last_event_at: datetime | None
    last_event_type: str | None
    system_helps_in_session: int
    help_requests_in_session: int
    teacher_interventions_in_session: int
    state_label: str | None = Field(description="Etiqueta neutral (la misma que ve el estudiante)")
    operational_state: str | None = Field(
        description="Interpretación operativa del sistema; nunca visible para el estudiante"
    )
    suggest_teacher: bool = Field(description="El tutor agotó sus ayudas o alcanzó su tope en la tarea actual")


class GroupOverview(BaseModel):
    institution_id: uuid.UUID
    grade: str
    group_code: str
    students: list[StudentOverview]
