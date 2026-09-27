"""Esquemas Pydantic del módulo de aprendizaje."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.common.enums import InteractionEventType, Representation, ScaffoldType, TaskType, WorkedExampleType


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# ---------------------------------------------------------------- tareas y ejemplos


class TaskOut(BaseModel):
    """Vista para el estudiante: NUNCA incluye ``solution``."""

    id: uuid.UUID
    code: str
    task_type: TaskType
    title: str
    skill: str
    difficulty: int
    grade_min: str
    grade_max: str
    statement: dict[str, Any]
    related_task_id: uuid.UUID | None
    order_index: int


class TaskAdminOut(TaskOut):
    solution: dict[str, Any]
    version: int
    is_active: bool


class TaskIn(StrictModel):
    code: str = Field(min_length=2, max_length=32, pattern=r"^[A-Z0-9_-]+$")
    task_type: TaskType
    title: str = Field(min_length=2, max_length=200)
    skill: str = Field(min_length=2, max_length=48)
    difficulty: int = Field(default=2, ge=1, le=5)
    grade_min: Literal["7", "8", "9"] = "7"
    grade_max: Literal["7", "8", "9"] = "9"
    statement: dict[str, Any]
    solution: dict[str, Any]
    related_task_code: str | None = None
    order_index: int = 0
    is_active: bool = True


class WorkedExampleOut(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    example_type: WorkedExampleType
    title: str
    content: dict[str, Any]
    order_index: int


class WorkedExampleIn(StrictModel):
    task_code: str
    example_type: WorkedExampleType
    title: str = Field(min_length=2, max_length=200)
    content: dict[str, Any]
    order_index: int = 0
    is_active: bool = True


class ScaffoldOut(BaseModel):
    id: uuid.UUID
    code: str
    scaffold_type: ScaffoldType
    level: int
    applicable_task_types: list[str]
    applicable_skills: list[str]
    content: dict[str, Any]
    version: int
    is_active: bool


class ScaffoldIn(StrictModel):
    code: str = Field(min_length=2, max_length=48, pattern=r"^[A-Z0-9_-]+$")
    scaffold_type: ScaffoldType
    level: int = Field(ge=1, le=5)
    applicable_task_types: list[TaskType] = Field(default_factory=list)
    applicable_skills: list[str] = Field(default_factory=list)
    content: dict[str, Any]
    is_active: bool = True
    reviewed_by: str | None = None


# ---------------------------------------------------------------- sesiones


class SessionCreate(StrictModel):
    task_codes: list[str] | None = Field(
        default=None, max_length=20, description="Si se omite, se asignan las tareas del grado"
    )
    context: dict[str, Any] = Field(default_factory=dict)


class SessionTaskOut(BaseModel):
    id: uuid.UUID
    task: TaskOut
    order_index: int
    status: str
    opened_at: datetime | None
    completed_at: datetime | None


class SessionOut(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    participant_code: str | None = None
    started_at: datetime
    ended_at: datetime | None
    status: str
    tasks: list[SessionTaskOut]
    context: dict[str, Any]


class SessionSummaryOut(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    participant_code: str | None = None
    started_at: datetime
    ended_at: datetime | None
    status: str
    task_count: int
    completed_count: int
    interaction_count: int
    help_count: int


class SessionEnd(StrictModel):
    status: Literal["COMPLETED", "ABANDONED"] = "COMPLETED"


# ---------------------------------------------------------------- respuestas y eventos


class ClientMeta(StrictModel):
    time_on_task_ms: int | None = Field(default=None, ge=0, le=24 * 3600 * 1000)
    clicks: int | None = Field(default=None, ge=0, le=100000)
    edits: int | None = Field(default=None, ge=0, le=100000)
    device: str | None = Field(default=None, max_length=32)


class ResponseSubmit(StrictModel):
    task_id: uuid.UUID
    question_id: str = Field(min_length=1, max_length=32)
    representation: Representation
    content: dict[str, Any]
    is_edit_of: uuid.UUID | None = None
    client_meta: ClientMeta = Field(default_factory=ClientMeta)

    @model_validator(mode="after")
    def _content_shape(self) -> ResponseSubmit:
        required = {
            Representation.VERBAL: "text",
            Representation.NUMERIC: "value",
            Representation.TABULAR: "rows",
            Representation.GRAPHIC: "points",
            Representation.SYMBOLIC: "expression",
        }[self.representation]
        if required not in self.content:
            raise ValueError(f"El contenido de una respuesta {self.representation.value} requiere '{required}'.")
        if self.representation == Representation.VERBAL and len(str(self.content["text"])) > 4000:
            raise ValueError("La explicación es demasiado larga.")
        return self


class ResponseOut(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    question_id: str
    attempt_number: int
    representation: Representation
    content: dict[str, Any]
    is_edit_of: uuid.UUID | None
    submitted_at: datetime
    # Para el estudiante no se envía 'correct' (APRENDIZAJE > CORRECCIÓN INMEDIATA).
    evaluation: dict[str, Any] | None = None


CLIENT_EVENT_TYPES = {
    InteractionEventType.TASK_OPENED,
    InteractionEventType.EXAMPLE_OPENED,
    InteractionEventType.REPRESENTATION_CHANGED,
    InteractionEventType.SELF_EXPLANATION,
    InteractionEventType.TASK_COMPLETED,
    InteractionEventType.TASK_ABANDONED,
}


class ClientEvent(StrictModel):
    event_type: InteractionEventType
    task_id: uuid.UUID | None = None
    representation: Representation | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    client_meta: ClientMeta = Field(default_factory=ClientMeta)

    @model_validator(mode="after")
    def _allowed(self) -> ClientEvent:
        if self.event_type not in CLIENT_EVENT_TYPES:
            raise ValueError("Ese tipo de evento lo genera el servidor, no el cliente.")
        if self.event_type != InteractionEventType.SESSION_ENDED and self.task_id is None:
            raise ValueError("task_id es obligatorio para eventos de tarea.")
        return self


class InteractionOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    student_id: uuid.UUID
    task_id: uuid.UUID | None
    timestamp: datetime
    sequence: int
    event_type: InteractionEventType
    student_action: str | None
    student_response: dict[str, Any] | None
    representation: str | None
    help_requested: bool
    help_level: int | None
    help_type: str | None
    help_content: str | None
    help_accepted: bool | None
    help_rejected: bool | None
    scaffold_event_id: uuid.UUID | None
    ai_interpretation: dict[str, Any] | None
    teacher_intervention_id: uuid.UUID | None
    next_student_action: str | None
    client_meta: dict[str, Any]


# ---------------------------------------------------------------- ayuda


class HelpRequest(StrictModel):
    task_id: uuid.UUID
    question_id: str | None = Field(default=None, max_length=32)
    client_meta: ClientMeta = Field(default_factory=ClientMeta)


class HelpOffer(BaseModel):
    """Lo que ve el estudiante: la ayuda concreta, sin etiquetas de estado."""

    scaffold_event_id: uuid.UUID | None
    offered: bool
    level: int
    scaffold_type: ScaffoldType | None
    text: str | None
    follow_up: str | None = None
    can_reformulate: bool = False
    message: str


class ScaffoldFeedback(StrictModel):
    action: Literal["ACCEPTED", "REJECTED", "REFORMULATE"]
    client_meta: ClientMeta = Field(default_factory=ClientMeta)


class ScaffoldEventOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    student_id: uuid.UUID
    task_id: uuid.UUID
    interaction_id: uuid.UUID | None
    scaffold_id: uuid.UUID | None
    scaffold_code: str | None
    scaffold_type: ScaffoldType | None
    decision: dict[str, Any]
    previous_help_level: int
    current_help_level: int
    reason_for_change: str | None
    source: str
    delivered_text: str | None
    accepted: bool | None
    rejected: bool | None
    reformulations: int
    result: str
    subsequent_strategy: str | None
    created_at: datetime
    resolved_at: datetime | None


class SubmitResult(BaseModel):
    """Respuesta al estudiante tras enviar: registro + (opcional) ayuda decidida por el tutor."""

    response: ResponseOut
    help: HelpOffer | None
    state_label: str  # etiqueta neutral visible ("En marcha", "Explorando", ...)
