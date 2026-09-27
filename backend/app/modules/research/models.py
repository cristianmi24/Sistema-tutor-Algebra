"""Modelos SQLAlchemy del esquema ``research``."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, PrimaryKeyConstraint, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import (
    SCHEMA_IDENTITY,
    SCHEMA_LEARNING,
    SCHEMA_RESEARCH,
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)

STUDENTS_FK = f"{SCHEMA_IDENTITY}.students.id"
TEACHERS_FK = f"{SCHEMA_IDENTITY}.teachers.id"
RESEARCHERS_FK = f"{SCHEMA_IDENTITY}.researchers.id"
SESSIONS_FK = f"{SCHEMA_LEARNING}.learning_sessions.id"
TASKS_FK = f"{SCHEMA_LEARNING}.tasks.id"
INTERACTIONS_FK = f"{SCHEMA_LEARNING}.interactions.id"


class Episode(UUIDPrimaryKeyMixin, Base):
    """Trayectoria reconstruible: dificultad → ayuda → interpretación → nueva acción → resultado."""

    __tablename__ = "episodes"
    __table_args__ = (
        CheckConstraint(
            "trigger IN ('DIFFICULTY', 'HELP_REQUEST', 'STAGNATION', 'UNCERTAINTY', 'IMPULSIVITY', "
            "'TEACHER', 'MANUAL')",
            name="trigger_allowed",
        ),
        CheckConstraint("status IN ('OPEN', 'CLOSED')", name="status_allowed"),
        Index("ix_research_episodes_student_created", "student_id", "created_at"),
        Index("ix_research_episodes_session_task", "session_id", "task_id"),
        {"schema": SCHEMA_RESEARCH},
    )

    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(STUDENTS_FK, ondelete="CASCADE"), nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(SESSIONS_FK, ondelete="CASCADE"), nullable=False)
    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(TASKS_FK, ondelete="RESTRICT"), nullable=False)
    started_interaction_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey(INTERACTIONS_FK, ondelete="SET NULL"))
    ended_interaction_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey(INTERACTIONS_FK, ondelete="SET NULL"))
    trigger: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(8), nullable=False, server_default=text("'OPEN'"))
    # Resumen AUTOMÁTICO (conteos y niveles). No contiene categorías teóricas.
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    close_reason: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column()

    interactions: Mapped[list[EpisodeInteraction]] = relationship(
        back_populates="episode", order_by="EpisodeInteraction.order_index"
    )


class EpisodeInteraction(Base):
    __tablename__ = "episode_interactions"
    __table_args__ = (
        PrimaryKeyConstraint("episode_id", "interaction_id"),
        {"schema": SCHEMA_RESEARCH},
    )

    episode_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_RESEARCH}.episodes.id", ondelete="CASCADE"), nullable=False
    )
    interaction_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(INTERACTIONS_FK, ondelete="CASCADE"), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)

    episode: Mapped[Episode] = relationship(back_populates="interactions")


class ResearchMemo(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Memo analítico (Teoría Fundamentada Constructivista). Las categorías son del investigador."""

    __tablename__ = "research_memos"
    __table_args__ = (
        Index("ix_research_memos_researcher", "researcher_id", "created_at"),
        Index("ix_research_memos_episode", "episode_id"),
        {"schema": SCHEMA_RESEARCH},
    )

    researcher_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(RESEARCHERS_FK, ondelete="RESTRICT"), nullable=False)
    episode_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(f"{SCHEMA_RESEARCH}.episodes.id", ondelete="SET NULL")
    )
    student_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey(STUDENTS_FK, ondelete="SET NULL"))
    session_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey(SESSIONS_FK, ondelete="SET NULL"))
    task_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey(TASKS_FK, ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    observation: Mapped[str | None] = mapped_column(Text)
    interpretation: Mapped[str | None] = mapped_column(Text)
    emerging_question: Mapped[str | None] = mapped_column(Text)
    contradiction: Mapped[str | None] = mapped_column(Text)
    negative_case: Mapped[str | None] = mapped_column(Text)
    possible_category: Mapped[str | None] = mapped_column(Text)
    theoretical_sampling_need: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String(48)), nullable=False, server_default=text("'{}'"))


class Interview(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "interviews"
    __table_args__ = (
        CheckConstraint("interviewee_kind IN ('STUDENT', 'TEACHER')", name="interviewee_allowed"),
        Index("ix_research_interviews_researcher", "researcher_id", "conducted_at"),
        {"schema": SCHEMA_RESEARCH},
    )

    researcher_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(RESEARCHERS_FK, ondelete="RESTRICT"), nullable=False)
    interviewee_kind: Mapped[str] = mapped_column(String(8), nullable=False)
    student_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey(STUDENTS_FK, ondelete="SET NULL"))
    teacher_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey(TEACHERS_FK, ondelete="SET NULL"))
    session_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey(SESSIONS_FK, ondelete="SET NULL"))
    task_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey(TASKS_FK, ondelete="SET NULL"))
    episode_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(f"{SCHEMA_RESEARCH}.episodes.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    conducted_at: Mapped[datetime] = mapped_column(nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    responses: Mapped[list[InterviewResponse]] = relationship(
        back_populates="interview", order_by="InterviewResponse.order_index"
    )


class InterviewResponse(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "interview_responses"
    __table_args__ = (
        Index("ix_research_interview_responses_interview", "interview_id", "order_index"),
        {"schema": SCHEMA_RESEARCH},
    )

    interview_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_RESEARCH}.interviews.id", ondelete="CASCADE"), nullable=False
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text)
    related_episode_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(f"{SCHEMA_RESEARCH}.episodes.id", ondelete="SET NULL")
    )
    observations: Mapped[str | None] = mapped_column(Text)
    memo_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(f"{SCHEMA_RESEARCH}.research_memos.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"), nullable=False)

    interview: Mapped[Interview] = relationship(back_populates="responses")
