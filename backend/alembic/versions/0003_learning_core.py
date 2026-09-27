"""Esquema learning (núcleo Fase 3): tareas, ejemplos trabajados, sesiones, respuestas,
interacciones append-only, banco de andamiajes, eventos de andamiaje e intervenciones docentes.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-27 01:37:03.520405+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scaffolds",
        sa.Column("code", sa.String(length=48), nullable=False),
        sa.Column("scaffold_type", sa.String(length=32), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column(
            "applicable_task_types",
            postgresql.ARRAY(sa.String(length=32)),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "applicable_skills", postgresql.ARRAY(sa.String(length=48)), server_default=sa.text("'{}'"), nullable=False
        ),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("language", sa.String(length=8), server_default=sa.text("'es'"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("reviewed_by", sa.String(length=120), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "scaffold_type IN ('FOCUSING', 'GUIDING_QUESTION', 'HINT', 'SELF_EXPLANATION', 'REPRESENTATION_CHANGE', 'TASK_DIVISION', 'RECOVERY', 'METACOGNITIVE', 'STRATEGY_COMPARISON', 'ERROR_REFLECTION')",
            name=op.f("ck_scaffolds_scaffold_type_allowed"),
        ),
        sa.CheckConstraint("level BETWEEN 1 AND 5", name=op.f("ck_scaffolds_level_range")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scaffolds")),
        sa.UniqueConstraint("code", name=op.f("uq_scaffolds_code")),
        schema="learning",
    )
    op.create_index(
        "ix_learning_scaffolds_type_level",
        "scaffolds",
        ["scaffold_type", "level", "is_active"],
        unique=False,
        schema="learning",
    )
    op.create_table(
        "tasks",
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("task_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("skill", sa.String(length=48), nullable=False),
        sa.Column("difficulty", sa.Integer(), server_default=sa.text("2"), nullable=False),
        sa.Column("grade_min", sa.String(length=2), server_default=sa.text("'7'"), nullable=False),
        sa.Column("grade_max", sa.String(length=2), server_default=sa.text("'9'"), nullable=False),
        sa.Column("statement", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("solution", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("related_task_id", sa.UUID(), nullable=True),
        sa.Column("order_index", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "task_type IN ('NUMERIC_PATTERN', 'FIGURAL_PATTERN', 'TABLE', 'GRAPH', 'SYMBOLIC', 'JUSTIFICATION', 'TRANSFER')",
            name=op.f("ck_tasks_task_type_allowed"),
        ),
        sa.CheckConstraint("difficulty BETWEEN 1 AND 5", name=op.f("ck_tasks_difficulty_range")),
        sa.ForeignKeyConstraint(
            ["related_task_id"], ["learning.tasks.id"], name=op.f("fk_tasks_related_task_id_tasks"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tasks")),
        sa.UniqueConstraint("code", name=op.f("uq_tasks_code")),
        schema="learning",
    )
    op.create_index(
        "ix_learning_tasks_type_active", "tasks", ["task_type", "is_active"], unique=False, schema="learning"
    )
    op.create_table(
        "worked_examples",
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("example_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("order_index", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint(
            "example_type IN ('FULL', 'PARTIAL', 'HIDDEN_STEPS', 'SELF_EXPLANATION', 'STRATEGY_COMPARISON', 'INTENTIONAL_ERROR', 'TRANSFER')",
            name=op.f("ck_worked_examples_example_type_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["task_id"], ["learning.tasks.id"], name=op.f("fk_worked_examples_task_id_tasks"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_worked_examples")),
        schema="learning",
    )
    op.create_index("ix_learning_worked_examples_task", "worked_examples", ["task_id"], unique=False, schema="learning")
    op.create_table(
        "learning_sessions",
        sa.Column("student_id", sa.UUID(), nullable=False),
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=16), server_default=sa.text("'ACTIVE'"), nullable=False),
        sa.Column(
            "context", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column("last_sequence", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'COMPLETED', 'ABANDONED')", name=op.f("ck_learning_sessions_status_allowed")
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["identity.students.id"],
            name=op.f("fk_learning_sessions_student_id_students"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learning_sessions")),
        schema="learning",
    )
    op.create_index(
        "ix_learning_sessions_student_started",
        "learning_sessions",
        ["student_id", "started_at"],
        unique=False,
        schema="learning",
    )
    op.create_table(
        "session_tasks",
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("order_index", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("status", sa.String(length=16), server_default=sa.text("'PENDING'"), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('PENDING', 'OPEN', 'COMPLETED', 'ABANDONED')", name=op.f("ck_session_tasks_status_allowed")
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["learning.learning_sessions.id"],
            name=op.f("fk_session_tasks_session_id_learning_sessions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"], ["learning.tasks.id"], name=op.f("fk_session_tasks_task_id_tasks"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_session_tasks")),
        sa.UniqueConstraint("session_id", "task_id", name=op.f("uq_session_tasks_session_id_task_id")),
        schema="learning",
    )
    op.create_table(
        "student_responses",
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("student_id", sa.UUID(), nullable=False),
        sa.Column("question_id", sa.String(length=32), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("representation", sa.String(length=16), nullable=False),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_edit_of", sa.UUID(), nullable=True),
        sa.Column(
            "evaluation", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint(
            "representation IN ('VERBAL', 'NUMERIC', 'TABULAR', 'GRAPHIC', 'SYMBOLIC')",
            name=op.f("ck_student_responses_representation_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["is_edit_of"],
            ["learning.student_responses.id"],
            name=op.f("fk_student_responses_is_edit_of_student_responses"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["learning.learning_sessions.id"],
            name=op.f("fk_student_responses_session_id_learning_sessions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["identity.students.id"],
            name=op.f("fk_student_responses_student_id_students"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"], ["learning.tasks.id"], name=op.f("fk_student_responses_task_id_tasks"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_student_responses")),
        schema="learning",
    )
    op.create_index(
        "ix_learning_student_responses_session_task",
        "student_responses",
        ["session_id", "task_id", "submitted_at"],
        unique=False,
        schema="learning",
    )
    op.create_index(
        "ix_learning_student_responses_student",
        "student_responses",
        ["student_id", "submitted_at"],
        unique=False,
        schema="learning",
    )
    op.create_table(
        "teacher_interventions",
        sa.Column("teacher_id", sa.UUID(), nullable=False),
        sa.Column("student_id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=True),
        sa.Column("interaction_id", sa.UUID(), nullable=True),
        sa.Column("intervention_type", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("visibility", sa.String(length=16), server_default=sa.text("'STUDENT'"), nullable=False),
        sa.Column("student_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint(
            "intervention_type IN ('QUESTION', 'COMMENT', 'OBSERVATION', 'REDIRECTION', 'ENCOURAGEMENT')",
            name=op.f("ck_teacher_interventions_type_allowed"),
        ),
        sa.CheckConstraint(
            "visibility IN ('STUDENT', 'RESEARCH_ONLY')", name=op.f("ck_teacher_interventions_visibility_allowed")
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["learning.learning_sessions.id"],
            name=op.f("fk_teacher_interventions_session_id_learning_sessions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["identity.students.id"],
            name=op.f("fk_teacher_interventions_student_id_students"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"], ["learning.tasks.id"], name=op.f("fk_teacher_interventions_task_id_tasks"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["teacher_id"],
            ["identity.teachers.id"],
            name=op.f("fk_teacher_interventions_teacher_id_teachers"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_teacher_interventions")),
        schema="learning",
    )
    op.create_index(
        "ix_learning_teacher_interventions_session",
        "teacher_interventions",
        ["session_id"],
        unique=False,
        schema="learning",
    )
    op.create_index(
        "ix_learning_teacher_interventions_student",
        "teacher_interventions",
        ["student_id", "created_at"],
        unique=False,
        schema="learning",
    )
    op.create_table(
        "interactions",
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("student_id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("sequence", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("student_action", sa.String(length=64), nullable=True),
        sa.Column("student_response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("response_id", sa.UUID(), nullable=True),
        sa.Column("representation", sa.String(length=16), nullable=True),
        sa.Column("help_requested", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("help_level", sa.Integer(), nullable=True),
        sa.Column("help_type", sa.String(length=32), nullable=True),
        sa.Column("help_content", sa.Text(), nullable=True),
        sa.Column("help_accepted", sa.Boolean(), nullable=True),
        sa.Column("help_rejected", sa.Boolean(), nullable=True),
        sa.Column("scaffold_event_id", sa.UUID(), nullable=True),
        sa.Column("ai_interpretation", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("teacher_intervention_id", sa.UUID(), nullable=True),
        sa.Column("next_student_action", sa.String(length=64), nullable=True),
        sa.Column(
            "client_meta",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('SESSION_STARTED', 'TASK_OPENED', 'EXAMPLE_OPENED', 'STUDENT_RESPONSE', 'STUDENT_EDITED_RESPONSE', 'HELP_REQUESTED', 'HELP_OFFERED', 'HELP_ACCEPTED', 'HELP_REJECTED', 'HELP_REFORMULATED', 'STUDENT_REATTEMPT', 'REPRESENTATION_CHANGED', 'SELF_EXPLANATION', 'ERROR_DETECTED', 'TEACHER_INTERVENTION', 'TASK_COMPLETED', 'TASK_ABANDONED', 'SESSION_ENDED')",
            name=op.f("ck_interactions_event_type_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["response_id"],
            ["learning.student_responses.id"],
            name=op.f("fk_interactions_response_id_student_responses"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["learning.learning_sessions.id"],
            name=op.f("fk_interactions_session_id_learning_sessions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["identity.students.id"],
            name=op.f("fk_interactions_student_id_students"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"], ["learning.tasks.id"], name=op.f("fk_interactions_task_id_tasks"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_interactions")),
        sa.UniqueConstraint("session_id", "sequence", name=op.f("uq_interactions_session_id_sequence")),
        schema="learning",
    )
    op.create_index(
        "ix_learning_interactions_event_type", "interactions", ["event_type"], unique=False, schema="learning"
    )
    op.create_index(
        "ix_learning_interactions_session_task",
        "interactions",
        ["session_id", "task_id"],
        unique=False,
        schema="learning",
    )
    op.create_index(
        "ix_learning_interactions_student_ts",
        "interactions",
        ["student_id", "timestamp"],
        unique=False,
        schema="learning",
    )
    op.create_table(
        "scaffold_events",
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("student_id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("interaction_id", sa.UUID(), nullable=True),
        sa.Column("scaffold_id", sa.UUID(), nullable=True),
        sa.Column("decision", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("previous_help_level", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("current_help_level", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("reason_for_change", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=16), server_default=sa.text("'SYSTEM'"), nullable=False),
        sa.Column("delivered_text", sa.Text(), nullable=True),
        sa.Column("accepted", sa.Boolean(), nullable=True),
        sa.Column("rejected", sa.Boolean(), nullable=True),
        sa.Column("reformulations", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("student_response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("result", sa.String(length=16), server_default=sa.text("'PENDING'"), nullable=False),
        sa.Column("subsequent_strategy", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint(
            "result IN ('PENDING', 'IMPROVED', 'PERSISTED', 'REJECTED', 'ABANDONED', 'UNKNOWN')",
            name=op.f("ck_scaffold_events_result_allowed"),
        ),
        sa.CheckConstraint(
            "source IN ('SYSTEM', 'AI_VALIDATED', 'STATIC')", name=op.f("ck_scaffold_events_source_allowed")
        ),
        sa.ForeignKeyConstraint(
            ["interaction_id"],
            ["learning.interactions.id"],
            name=op.f("fk_scaffold_events_interaction_id_interactions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["scaffold_id"],
            ["learning.scaffolds.id"],
            name=op.f("fk_scaffold_events_scaffold_id_scaffolds"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["learning.learning_sessions.id"],
            name=op.f("fk_scaffold_events_session_id_learning_sessions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["identity.students.id"],
            name=op.f("fk_scaffold_events_student_id_students"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"], ["learning.tasks.id"], name=op.f("fk_scaffold_events_task_id_tasks"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scaffold_events")),
        schema="learning",
    )
    op.create_index(
        "ix_learning_scaffold_events_scaffold", "scaffold_events", ["scaffold_id"], unique=False, schema="learning"
    )
    op.create_index(
        "ix_learning_scaffold_events_session_task",
        "scaffold_events",
        ["session_id", "task_id"],
        unique=False,
        schema="learning",
    )
    op.create_index(
        "ix_learning_scaffold_events_student_created",
        "scaffold_events",
        ["student_id", "created_at"],
        unique=False,
        schema="learning",
    )


def downgrade() -> None:
    op.drop_index("ix_learning_scaffold_events_student_created", table_name="scaffold_events", schema="learning")
    op.drop_index("ix_learning_scaffold_events_session_task", table_name="scaffold_events", schema="learning")
    op.drop_index("ix_learning_scaffold_events_scaffold", table_name="scaffold_events", schema="learning")
    op.drop_table("scaffold_events", schema="learning")
    op.drop_index("ix_learning_interactions_student_ts", table_name="interactions", schema="learning")
    op.drop_index("ix_learning_interactions_session_task", table_name="interactions", schema="learning")
    op.drop_index("ix_learning_interactions_event_type", table_name="interactions", schema="learning")
    op.drop_table("interactions", schema="learning")
    op.drop_index("ix_learning_teacher_interventions_student", table_name="teacher_interventions", schema="learning")
    op.drop_index("ix_learning_teacher_interventions_session", table_name="teacher_interventions", schema="learning")
    op.drop_table("teacher_interventions", schema="learning")
    op.drop_index("ix_learning_student_responses_student", table_name="student_responses", schema="learning")
    op.drop_index("ix_learning_student_responses_session_task", table_name="student_responses", schema="learning")
    op.drop_table("student_responses", schema="learning")
    op.drop_table("session_tasks", schema="learning")
    op.drop_index("ix_learning_sessions_student_started", table_name="learning_sessions", schema="learning")
    op.drop_table("learning_sessions", schema="learning")
    op.drop_index("ix_learning_worked_examples_task", table_name="worked_examples", schema="learning")
    op.drop_table("worked_examples", schema="learning")
    op.drop_index("ix_learning_tasks_type_active", table_name="tasks", schema="learning")
    op.drop_table("tasks", schema="learning")
    op.drop_index("ix_learning_scaffolds_type_level", table_name="scaffolds", schema="learning")
    op.drop_table("scaffolds", schema="learning")
