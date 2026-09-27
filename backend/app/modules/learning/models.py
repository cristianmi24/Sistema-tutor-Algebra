"""Modelos SQLAlchemy del esquema ``learning`` (núcleo: Fase 3)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import SCHEMA_IDENTITY, SCHEMA_LEARNING, Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.modules.common.enums import (
    InteractionEventType,
    Representation,
    ScaffoldType,
    TaskType,
    WorkedExampleType,
    values,
)


def _in_list(column: str, options: list[str]) -> str:
    quoted = ", ".join(f"'{option}'" for option in options)
    return f"{column} IN ({quoted})"


STUDENTS_FK = f"{SCHEMA_IDENTITY}.students.id"
TEACHERS_FK = f"{SCHEMA_IDENTITY}.teachers.id"


class Task(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Actividad del banco (tipos A–G). ``statement`` es visible al estudiante; ``solution`` nunca."""

    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(_in_list("task_type", values(TaskType)), name="task_type_allowed"),
        CheckConstraint("difficulty BETWEEN 1 AND 5", name="difficulty_range"),
        Index("ix_learning_tasks_type_active", "task_type", "is_active"),
        {"schema": SCHEMA_LEARNING},
    )

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    task_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    skill: Mapped[str] = mapped_column(String(48), nullable=False)  # RECURSIVE_RELATION, FUNCTIONAL_RELATION, ...
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("2"))
    grade_min: Mapped[str] = mapped_column(String(2), nullable=False, server_default=text("'7'"))
    grade_max: Mapped[str] = mapped_column(String(2), nullable=False, server_default=text("'9'"))
    statement: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    solution: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)  # privado (expresión, notas)
    related_task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(f"{SCHEMA_LEARNING}.tasks.id", ondelete="SET NULL")
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    worked_examples: Mapped[list[WorkedExample]] = relationship(
        back_populates="task", order_by="WorkedExample.order_index"
    )


class WorkedExample(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "worked_examples"
    __table_args__ = (
        CheckConstraint(_in_list("example_type", values(WorkedExampleType)), name="example_type_allowed"),
        Index("ix_learning_worked_examples_task", "task_id"),
        {"schema": SCHEMA_LEARNING},
    )

    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_LEARNING}.tasks.id", ondelete="CASCADE"), nullable=False
    )
    example_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)  # pasos, prompts, estrategias, error
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"), nullable=False)

    task: Mapped[Task] = relationship(back_populates="worked_examples")


class LearningSession(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "learning_sessions"
    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE', 'COMPLETED', 'ABANDONED')", name="status_allowed"),
        Index("ix_learning_sessions_student_started", "student_id", "started_at"),
        {"schema": SCHEMA_LEARNING},
    )

    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(STUDENTS_FK, ondelete="CASCADE"), nullable=False)
    institution_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    started_at: Mapped[datetime] = mapped_column(server_default=text("now()"), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column()
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'ACTIVE'"))
    context: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    last_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"), nullable=False)

    tasks: Mapped[list[SessionTask]] = relationship(back_populates="session", order_by="SessionTask.order_index")


class SessionTask(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "session_tasks"
    __table_args__ = (
        CheckConstraint("status IN ('PENDING', 'OPEN', 'COMPLETED', 'ABANDONED')", name="status_allowed"),
        UniqueConstraint("session_id", "task_id"),
        {"schema": SCHEMA_LEARNING},
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_LEARNING}.learning_sessions.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_LEARNING}.tasks.id", ondelete="RESTRICT"), nullable=False
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'PENDING'"))
    opened_at: Mapped[datetime | None] = mapped_column()
    completed_at: Mapped[datetime | None] = mapped_column()

    session: Mapped[LearningSession] = relationship(back_populates="tasks")
    task: Mapped[Task] = relationship()


class StudentResponse(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "student_responses"
    __table_args__ = (
        CheckConstraint(_in_list("representation", values(Representation)), name="representation_allowed"),
        Index("ix_learning_student_responses_session_task", "session_id", "task_id", "submitted_at"),
        Index("ix_learning_student_responses_student", "student_id", "submitted_at"),
        {"schema": SCHEMA_LEARNING},
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_LEARNING}.learning_sessions.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_LEARNING}.tasks.id", ondelete="RESTRICT"), nullable=False
    )
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(STUDENTS_FK, ondelete="CASCADE"), nullable=False)
    question_id: Mapped[str] = mapped_column(String(32), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    representation: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    is_edit_of: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(f"{SCHEMA_LEARNING}.student_responses.id", ondelete="SET NULL")
    )
    # {"correct": true|false|null, "error_pattern": "...", "observed_dimensions": [...], "detail": {...}}
    evaluation: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    submitted_at: Mapped[datetime] = mapped_column(server_default=text("now()"), nullable=False)


class Interaction(UUIDPrimaryKeyMixin, Base):
    """Evento de trazabilidad (C.19). APPEND-ONLY: nunca se actualiza ni se borra desde la app."""

    __tablename__ = "interactions"
    __table_args__ = (
        CheckConstraint(_in_list("event_type", values(InteractionEventType)), name="event_type_allowed"),
        UniqueConstraint("session_id", "sequence"),
        Index("ix_learning_interactions_student_ts", "student_id", "timestamp"),
        Index("ix_learning_interactions_event_type", "event_type"),
        Index("ix_learning_interactions_session_task", "session_id", "task_id"),
        {"schema": SCHEMA_LEARNING},
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_LEARNING}.learning_sessions.id", ondelete="CASCADE"), nullable=False
    )
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(STUDENTS_FK, ondelete="CASCADE"), nullable=False)
    task_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey(f"{SCHEMA_LEARNING}.tasks.id", ondelete="RESTRICT"))
    timestamp: Mapped[datetime] = mapped_column(server_default=text("now()"), nullable=False)
    sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    student_action: Mapped[str | None] = mapped_column(String(64))
    student_response: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    response_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(f"{SCHEMA_LEARNING}.student_responses.id", ondelete="SET NULL")
    )
    representation: Mapped[str | None] = mapped_column(String(16))
    help_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    help_level: Mapped[int | None] = mapped_column(Integer)
    help_type: Mapped[str | None] = mapped_column(String(32))
    help_content: Mapped[str | None] = mapped_column(Text)
    help_accepted: Mapped[bool | None] = mapped_column(Boolean)
    help_rejected: Mapped[bool | None] = mapped_column(Boolean)
    scaffold_event_id: Mapped[uuid.UUID | None] = mapped_column()  # FK lógica (evita ciclo de FKs)
    ai_interpretation: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    teacher_intervention_id: Mapped[uuid.UUID | None] = mapped_column()
    next_student_action: Mapped[str | None] = mapped_column(String(64))  # se rellena en el siguiente evento
    # {"time_on_task_ms": 1234, "clicks": 12, "edits": 2, "device": "..."}
    client_meta: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))


class Scaffold(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Banco de andamiajes prediseñados y revisados. Nunca generados libremente."""

    __tablename__ = "scaffolds"
    __table_args__ = (
        CheckConstraint(_in_list("scaffold_type", values(ScaffoldType)), name="scaffold_type_allowed"),
        CheckConstraint("level BETWEEN 1 AND 5", name="level_range"),
        Index("ix_learning_scaffolds_type_level", "scaffold_type", "level", "is_active"),
        {"schema": SCHEMA_LEARNING},
    )

    code: Mapped[str] = mapped_column(String(48), unique=True, nullable=False)
    scaffold_type: Mapped[str] = mapped_column(String(32), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    applicable_task_types: Mapped[list[str]] = mapped_column(
        ARRAY(String(32)), nullable=False, server_default=text("'{}'")
    )
    applicable_skills: Mapped[list[str]] = mapped_column(ARRAY(String(48)), nullable=False, server_default=text("'{}'"))
    # {"text": "...", "variants": ["..."], "follow_up": "..."}
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    language: Mapped[str] = mapped_column(String(8), nullable=False, server_default=text("'es'"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    reviewed_by: Mapped[str | None] = mapped_column(String(120))
    reviewed_at: Mapped[datetime | None] = mapped_column()


class ScaffoldEvent(UUIDPrimaryKeyMixin, Base):
    """Decisión de andamiaje + fading + memoria de intervención (ver docs/05 §8–10)."""

    __tablename__ = "scaffold_events"
    __table_args__ = (
        CheckConstraint("source IN ('SYSTEM', 'AI_VALIDATED', 'STATIC')", name="source_allowed"),
        CheckConstraint(
            "result IN ('PENDING', 'IMPROVED', 'PERSISTED', 'REJECTED', 'ABANDONED', 'UNKNOWN')", name="result_allowed"
        ),
        Index("ix_learning_scaffold_events_student_created", "student_id", "created_at"),
        Index("ix_learning_scaffold_events_session_task", "session_id", "task_id"),
        Index("ix_learning_scaffold_events_scaffold", "scaffold_id"),
        {"schema": SCHEMA_LEARNING},
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_LEARNING}.learning_sessions.id", ondelete="CASCADE"), nullable=False
    )
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(STUDENTS_FK, ondelete="CASCADE"), nullable=False)
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_LEARNING}.tasks.id", ondelete="RESTRICT"), nullable=False
    )
    interaction_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(f"{SCHEMA_LEARNING}.interactions.id", ondelete="SET NULL")
    )
    scaffold_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(f"{SCHEMA_LEARNING}.scaffolds.id", ondelete="SET NULL")
    )
    decision: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)  # ScaffoldDecision serializada
    previous_help_level: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    current_help_level: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    reason_for_change: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'SYSTEM'"))
    delivered_text: Mapped[str | None] = mapped_column(Text)
    accepted: Mapped[bool | None] = mapped_column(Boolean)
    rejected: Mapped[bool | None] = mapped_column(Boolean)
    reformulations: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    student_response: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    result: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'PENDING'"))
    subsequent_strategy: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column()

    scaffold: Mapped[Scaffold | None] = relationship()


class TeacherIntervention(UUIDPrimaryKeyMixin, Base):
    """Intervención del DOCENTE. Siempre separada de las del sistema (Fase 6 la expone)."""

    __tablename__ = "teacher_interventions"
    __table_args__ = (
        CheckConstraint(
            "intervention_type IN ('QUESTION', 'COMMENT', 'OBSERVATION', 'REDIRECTION', 'ENCOURAGEMENT')",
            name="type_allowed",
        ),
        CheckConstraint("visibility IN ('STUDENT', 'RESEARCH_ONLY')", name="visibility_allowed"),
        Index("ix_learning_teacher_interventions_student", "student_id", "created_at"),
        Index("ix_learning_teacher_interventions_session", "session_id"),
        {"schema": SCHEMA_LEARNING},
    )

    teacher_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(TEACHERS_FK, ondelete="RESTRICT"), nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(STUDENTS_FK, ondelete="CASCADE"), nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_LEARNING}.learning_sessions.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey(f"{SCHEMA_LEARNING}.tasks.id", ondelete="RESTRICT"))
    interaction_id: Mapped[uuid.UUID | None] = mapped_column()
    intervention_type: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'STUDENT'"))
    student_seen_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"), nullable=False)
