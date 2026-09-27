"""Modelos SQLAlchemy del motor adaptativo (esquema ``learning``, Fase 4) y de IA (Fase 7)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import SCHEMA_IDENTITY, SCHEMA_LEARNING, Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.modules.common.enums import StudentState, values

STUDENTS_FK = f"{SCHEMA_IDENTITY}.students.id"
_STATES = ", ".join(f"'{s}'" for s in values(StudentState))


class InteractionEvidence(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "interaction_evidence"
    __table_args__ = (
        Index("ix_learning_interaction_evidence_student", "student_id", "created_at"),
        {"schema": SCHEMA_LEARNING},
    )

    interaction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_LEARNING}.interactions.id", ondelete="CASCADE"), nullable=False
    )
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(STUDENTS_FK, ondelete="CASCADE"), nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_LEARNING}.learning_sessions.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_LEARNING}.tasks.id", ondelete="RESTRICT"), nullable=False
    )
    window_size: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"), nullable=False)


class StudentStateRow(UUIDPrimaryKeyMixin, Base):
    """Perfil dinámico vigente: StudentCognitiveInteractionState (uno por estudiante)."""

    __tablename__ = "student_state"
    __table_args__ = (
        CheckConstraint(f"current_state IN ({_STATES})", name="current_state_allowed"),
        {"schema": SCHEMA_LEARNING},
    )

    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(STUDENTS_FK, ondelete="CASCADE"), unique=True, nullable=False
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(f"{SCHEMA_LEARNING}.learning_sessions.id", ondelete="SET NULL")
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey(f"{SCHEMA_LEARNING}.tasks.id", ondelete="SET NULL"))
    current_skill: Mapped[str | None] = mapped_column(String(48))
    current_difficulty: Mapped[int | None] = mapped_column(Integer)
    recent_accuracy: Mapped[float | None] = mapped_column(Numeric(5, 3))
    average_response_time_ms: Mapped[int | None] = mapped_column(Integer)
    click_pattern: Mapped[str | None] = mapped_column(String(16))
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    repetition_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    error_pattern: Mapped[str | None] = mapped_column(String(32))
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 3))
    current_state: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'NORMAL'"))
    previous_state: Mapped[str | None] = mapped_column(String(16))
    candidate_state: Mapped[str | None] = mapped_column(String(16))
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    current_help_level: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    last_intervention_id: Mapped[uuid.UUID | None] = mapped_column()
    intervention_result: Mapped[str | None] = mapped_column(String(16))
    posterior: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"), onupdate=text("now()"), nullable=False)


class StudentStateHistory(UUIDPrimaryKeyMixin, Base):
    """Historial append-only: estado anterior → evidencia → inferencia → regla → estado actual."""

    __tablename__ = "student_state_history"
    __table_args__ = (
        Index("ix_learning_student_state_history_student", "student_id", "created_at"),
        Index("ix_learning_student_state_history_session", "session_id"),
        {"schema": SCHEMA_LEARNING},
    )

    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(STUDENTS_FK, ondelete="CASCADE"), nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_LEARNING}.learning_sessions.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey(f"{SCHEMA_LEARNING}.tasks.id", ondelete="SET NULL"))
    interaction_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(f"{SCHEMA_LEARNING}.interactions.id", ondelete="SET NULL")
    )
    previous_state: Mapped[str] = mapped_column(String(16), nullable=False)
    evidence_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    posterior: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    inferred_state: Mapped[str] = mapped_column(String(16), nullable=False)
    rule_fired: Mapped[str | None] = mapped_column(String(48))
    current_state: Mapped[str] = mapped_column(String(16), nullable=False)
    help_level: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    fading_action: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'KEEP'"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"), nullable=False)


class TutorRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tutor_rules"
    __table_args__ = ({"schema": SCHEMA_LEARNING},)

    code: Mapped[str] = mapped_column(String(48), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    min_consecutive: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    conditions: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    actions: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))


class BayesianConfig(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "bayesian_config"
    __table_args__ = ({"schema": SCHEMA_LEARNING},)

    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    priors: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    likelihoods: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    thresholds: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))


class AIInteraction(UUIDPrimaryKeyMixin, Base):
    """Trazabilidad de cada llamada al LLM opcional (Fase 7)."""

    __tablename__ = "ai_interactions"
    __table_args__ = (
        CheckConstraint(
            "purpose IN ('INTERPRET_OPEN_ANSWER', 'ADAPT_LANGUAGE', 'FORMULATE_QUESTION', 'ANALYZE_EXPLANATION', "
            "'DETECT_CONTRADICTION')",
            name="purpose_allowed",
        ),
        Index("ix_learning_ai_interactions_session", "session_id", "created_at"),
        {"schema": SCHEMA_LEARNING},
    )

    session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(f"{SCHEMA_LEARNING}.learning_sessions.id", ondelete="SET NULL")
    )
    student_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey(STUDENTS_FK, ondelete="SET NULL"))
    interaction_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(f"{SCHEMA_LEARNING}.interactions.id", ondelete="SET NULL")
    )
    scaffold_event_id: Mapped[uuid.UUID | None] = mapped_column()
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str | None] = mapped_column(String(64))
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    prompt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    raw_output: Mapped[str | None] = mapped_column(Text)
    validation: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"), nullable=False)
