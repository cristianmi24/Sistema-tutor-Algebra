"""Esquemas Pydantic del módulo de investigación (sin datos personales)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ParticipantOut(BaseModel):
    """Vista pseudonimizada: nunca nombre, correo ni usuario."""

    student_id: uuid.UUID
    participant_code: str
    grade: str
    group_code: str | None
    institution_code: str
    research_status: str
    sessions: int
    tasks_worked: int
    interactions: int
    episodes: int


class EpisodeOut(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    participant_code: str | None
    session_id: uuid.UUID
    task_id: uuid.UUID
    task_code: str | None
    task_title: str | None
    trigger: str
    status: str
    close_reason: str | None
    summary: dict[str, Any]
    created_at: datetime
    closed_at: datetime | None
    interaction_count: int


class TimelineStep(BaseModel):
    sequence: int
    timestamp: datetime
    phase: str
    event_type: str
    actor: Literal["STUDENT", "SYSTEM", "TEACHER"]
    representation: str | None
    content: dict[str, Any] | None
    help_level: int | None
    help_type: str | None
    help_text: str | None
    evaluation: dict[str, Any] | None
    teacher_intervention: dict[str, Any] | None
    system_interpretation: dict[str, Any] | None = Field(
        default=None,
        description="Interpretación operativa del sistema (estado estimado, regla). No es una categoría teórica.",
    )
    scaffold_decision: dict[str, Any] | None = None
    ai_interpretation: dict[str, Any] | None = Field(
        default=None, description="Propuesta de IA validada (vocabulario cerrado) o fuente de la reformulación."
    )
    client_meta: dict[str, Any]


class EpisodeDetail(EpisodeOut):
    context: dict[str, Any]
    timeline: list[TimelineStep]
    memos: list[MemoOut]


class ComparisonOut(BaseModel):
    a: EpisodeOut
    b: EpisodeOut
    dimensions: dict[str, dict[str, Any]]
    note: str


class ManualEpisodeIn(StrictModel):
    session_id: uuid.UUID
    task_id: uuid.UUID
    from_sequence: int = Field(ge=1)
    to_sequence: int = Field(ge=1)

    @model_validator(mode="after")
    def _range(self) -> ManualEpisodeIn:
        if self.to_sequence < self.from_sequence:
            raise ValueError("to_sequence debe ser mayor o igual que from_sequence.")
        return self


class MemoIn(StrictModel):
    title: str = Field(min_length=2, max_length=200)
    episode_id: uuid.UUID | None = None
    participant_code: str | None = Field(default=None, max_length=16)
    session_id: uuid.UUID | None = None
    task_id: uuid.UUID | None = None
    observation: str | None = Field(default=None, max_length=20000)
    interpretation: str | None = Field(default=None, max_length=20000)
    emerging_question: str | None = Field(default=None, max_length=20000)
    contradiction: str | None = Field(default=None, max_length=20000)
    negative_case: str | None = Field(default=None, max_length=20000)
    possible_category: str | None = Field(default=None, max_length=2000)
    theoretical_sampling_need: str | None = Field(default=None, max_length=20000)
    tags: list[str] = Field(default_factory=list, max_length=20)


class MemoOut(BaseModel):
    id: uuid.UUID
    researcher_code: str | None
    title: str
    episode_id: uuid.UUID | None
    participant_code: str | None
    session_id: uuid.UUID | None
    task_id: uuid.UUID | None
    observation: str | None
    interpretation: str | None
    emerging_question: str | None
    contradiction: str | None
    negative_case: str | None
    possible_category: str | None
    theoretical_sampling_need: str | None
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    source: Literal["RESEARCHER"] = "RESEARCHER"


class InterviewResponseIn(StrictModel):
    question: str = Field(min_length=1, max_length=4000)
    answer: str | None = Field(default=None, max_length=20000)
    related_episode_id: uuid.UUID | None = None
    observations: str | None = Field(default=None, max_length=20000)
    memo_id: uuid.UUID | None = None


class InterviewIn(StrictModel):
    title: str = Field(min_length=2, max_length=200)
    interviewee_kind: Literal["STUDENT", "TEACHER"]
    participant_code: str | None = Field(default=None, max_length=16)
    teacher_code: str | None = Field(default=None, max_length=16)
    session_id: uuid.UUID | None = None
    task_id: uuid.UUID | None = None
    episode_id: uuid.UUID | None = None
    conducted_at: datetime
    notes: str | None = Field(default=None, max_length=20000)
    responses: list[InterviewResponseIn] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def _interviewee(self) -> InterviewIn:
        if self.interviewee_kind == "STUDENT" and not self.participant_code:
            raise ValueError("Una entrevista a estudiante requiere participant_code.")
        if self.interviewee_kind == "TEACHER" and not self.teacher_code:
            raise ValueError("Una entrevista a docente requiere teacher_code.")
        return self


class InterviewResponseOut(BaseModel):
    id: uuid.UUID
    order_index: int
    question: str
    answer: str | None
    related_episode_id: uuid.UUID | None
    observations: str | None
    memo_id: uuid.UUID | None


class InterviewOut(BaseModel):
    id: uuid.UUID
    researcher_code: str | None
    title: str
    interviewee_kind: str
    participant_code: str | None
    teacher_code: str | None
    session_id: uuid.UUID | None
    task_id: uuid.UUID | None
    episode_id: uuid.UUID | None
    conducted_at: datetime
    notes: str | None
    responses: list[InterviewResponseOut]
    created_at: datetime


EpisodeDetail.model_rebuild()
