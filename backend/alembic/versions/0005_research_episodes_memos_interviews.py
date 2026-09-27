"""Esquema research (Fase 5): episodios reconstruibles, memos analíticos (Charmaz),
entrevistas y sus respuestas. Sin datos personales: solo identificadores opacos.

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-27 02:10:50.244747+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "episodes",
        sa.Column("student_id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("started_interaction_id", sa.UUID(), nullable=True),
        sa.Column("ended_interaction_id", sa.UUID(), nullable=True),
        sa.Column("trigger", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=8), server_default=sa.text("'OPEN'"), nullable=False),
        sa.Column(
            "summary", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column("close_reason", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint("status IN ('OPEN', 'CLOSED')", name=op.f("ck_episodes_status_allowed")),
        sa.CheckConstraint(
            "trigger IN ('DIFFICULTY', 'HELP_REQUEST', 'STAGNATION', 'UNCERTAINTY', 'IMPULSIVITY', 'TEACHER', 'MANUAL')",
            name=op.f("ck_episodes_trigger_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["ended_interaction_id"],
            ["learning.interactions.id"],
            name=op.f("fk_episodes_ended_interaction_id_interactions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["learning.learning_sessions.id"],
            name=op.f("fk_episodes_session_id_learning_sessions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["started_interaction_id"],
            ["learning.interactions.id"],
            name=op.f("fk_episodes_started_interaction_id_interactions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"], ["identity.students.id"], name=op.f("fk_episodes_student_id_students"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["task_id"], ["learning.tasks.id"], name=op.f("fk_episodes_task_id_tasks"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_episodes")),
        schema="research",
    )
    op.create_index(
        "ix_research_episodes_session_task", "episodes", ["session_id", "task_id"], unique=False, schema="research"
    )
    op.create_index(
        "ix_research_episodes_student_created",
        "episodes",
        ["student_id", "created_at"],
        unique=False,
        schema="research",
    )
    op.create_table(
        "episode_interactions",
        sa.Column("episode_id", sa.UUID(), nullable=False),
        sa.Column("interaction_id", sa.UUID(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["episode_id"],
            ["research.episodes.id"],
            name=op.f("fk_episode_interactions_episode_id_episodes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["interaction_id"],
            ["learning.interactions.id"],
            name=op.f("fk_episode_interactions_interaction_id_interactions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("episode_id", "interaction_id", name=op.f("pk_episode_interactions")),
        schema="research",
    )
    op.create_table(
        "interviews",
        sa.Column("researcher_id", sa.UUID(), nullable=False),
        sa.Column("interviewee_kind", sa.String(length=8), nullable=False),
        sa.Column("student_id", sa.UUID(), nullable=True),
        sa.Column("teacher_id", sa.UUID(), nullable=True),
        sa.Column("session_id", sa.UUID(), nullable=True),
        sa.Column("task_id", sa.UUID(), nullable=True),
        sa.Column("episode_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("conducted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "interviewee_kind IN ('STUDENT', 'TEACHER')", name=op.f("ck_interviews_interviewee_allowed")
        ),
        sa.ForeignKeyConstraint(
            ["episode_id"],
            ["research.episodes.id"],
            name=op.f("fk_interviews_episode_id_episodes"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["researcher_id"],
            ["identity.researchers.id"],
            name=op.f("fk_interviews_researcher_id_researchers"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["learning.learning_sessions.id"],
            name=op.f("fk_interviews_session_id_learning_sessions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["identity.students.id"],
            name=op.f("fk_interviews_student_id_students"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"], ["learning.tasks.id"], name=op.f("fk_interviews_task_id_tasks"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["teacher_id"],
            ["identity.teachers.id"],
            name=op.f("fk_interviews_teacher_id_teachers"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_interviews")),
        schema="research",
    )
    op.create_index(
        "ix_research_interviews_researcher",
        "interviews",
        ["researcher_id", "conducted_at"],
        unique=False,
        schema="research",
    )
    op.create_table(
        "research_memos",
        sa.Column("researcher_id", sa.UUID(), nullable=False),
        sa.Column("episode_id", sa.UUID(), nullable=True),
        sa.Column("student_id", sa.UUID(), nullable=True),
        sa.Column("session_id", sa.UUID(), nullable=True),
        sa.Column("task_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("observation", sa.Text(), nullable=True),
        sa.Column("interpretation", sa.Text(), nullable=True),
        sa.Column("emerging_question", sa.Text(), nullable=True),
        sa.Column("contradiction", sa.Text(), nullable=True),
        sa.Column("negative_case", sa.Text(), nullable=True),
        sa.Column("possible_category", sa.Text(), nullable=True),
        sa.Column("theoretical_sampling_need", sa.Text(), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String(length=48)), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["episode_id"],
            ["research.episodes.id"],
            name=op.f("fk_research_memos_episode_id_episodes"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["researcher_id"],
            ["identity.researchers.id"],
            name=op.f("fk_research_memos_researcher_id_researchers"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["learning.learning_sessions.id"],
            name=op.f("fk_research_memos_session_id_learning_sessions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["identity.students.id"],
            name=op.f("fk_research_memos_student_id_students"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"], ["learning.tasks.id"], name=op.f("fk_research_memos_task_id_tasks"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_research_memos")),
        schema="research",
    )
    op.create_index("ix_research_memos_episode", "research_memos", ["episode_id"], unique=False, schema="research")
    op.create_index(
        "ix_research_memos_researcher",
        "research_memos",
        ["researcher_id", "created_at"],
        unique=False,
        schema="research",
    )
    op.create_table(
        "interview_responses",
        sa.Column("interview_id", sa.UUID(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("related_episode_id", sa.UUID(), nullable=True),
        sa.Column("observations", sa.Text(), nullable=True),
        sa.Column("memo_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["interview_id"],
            ["research.interviews.id"],
            name=op.f("fk_interview_responses_interview_id_interviews"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["memo_id"],
            ["research.research_memos.id"],
            name=op.f("fk_interview_responses_memo_id_research_memos"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["related_episode_id"],
            ["research.episodes.id"],
            name=op.f("fk_interview_responses_related_episode_id_episodes"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_interview_responses")),
        schema="research",
    )
    op.create_index(
        "ix_research_interview_responses_interview",
        "interview_responses",
        ["interview_id", "order_index"],
        unique=False,
        schema="research",
    )


def downgrade() -> None:
    op.drop_index("ix_research_interview_responses_interview", table_name="interview_responses", schema="research")
    op.drop_table("interview_responses", schema="research")
    op.drop_index("ix_research_memos_researcher", table_name="research_memos", schema="research")
    op.drop_index("ix_research_memos_episode", table_name="research_memos", schema="research")
    op.drop_table("research_memos", schema="research")
    op.drop_index("ix_research_interviews_researcher", table_name="interviews", schema="research")
    op.drop_table("interviews", schema="research")
    op.drop_table("episode_interactions", schema="research")
    op.drop_index("ix_research_episodes_student_created", table_name="episodes", schema="research")
    op.drop_index("ix_research_episodes_session_task", table_name="episodes", schema="research")
    op.drop_table("episodes", schema="research")
