"""Motor adaptativo (Fase 4) e IA (Fase 7): evidencias, perfil dinámico e historial, reglas
pedagógicas, configuración bayesiana y trazabilidad de interacciones con IA.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-27 01:56:55.782749+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "bayesian_config",
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("priors", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("likelihoods", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "thresholds", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bayesian_config")),
        sa.UniqueConstraint("name", name=op.f("uq_bayesian_config_name")),
        schema="learning",
    )
    op.create_table(
        "tutor_rules",
        sa.Column("code", sa.String(length=48), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("priority", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("min_consecutive", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("conditions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("actions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tutor_rules")),
        sa.UniqueConstraint("code", name=op.f("uq_tutor_rules_code")),
        schema="learning",
    )
    op.create_table(
        "student_state",
        sa.Column("student_id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=True),
        sa.Column("task_id", sa.UUID(), nullable=True),
        sa.Column("current_skill", sa.String(length=48), nullable=True),
        sa.Column("current_difficulty", sa.Integer(), nullable=True),
        sa.Column("recent_accuracy", sa.Numeric(precision=5, scale=3), nullable=True),
        sa.Column("average_response_time_ms", sa.Integer(), nullable=True),
        sa.Column("click_pattern", sa.String(length=16), nullable=True),
        sa.Column("attempt_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("repetition_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("error_pattern", sa.String(length=32), nullable=True),
        sa.Column("confidence", sa.Numeric(precision=5, scale=3), nullable=True),
        sa.Column("current_state", sa.String(length=16), server_default=sa.text("'NORMAL'"), nullable=False),
        sa.Column("previous_state", sa.String(length=16), nullable=True),
        sa.Column("candidate_state", sa.String(length=16), nullable=True),
        sa.Column("candidate_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("current_help_level", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_intervention_id", sa.UUID(), nullable=True),
        sa.Column("intervention_result", sa.String(length=16), nullable=True),
        sa.Column(
            "posterior", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint(
            "current_state IN ('NORMAL', 'EXPLORATION', 'DIFFICULTY', 'UNCERTAINTY', 'IMPULSIVITY', 'STAGNATION', 'RECOVERY', 'AUTONOMY')",
            name=op.f("ck_student_state_current_state_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["learning.learning_sessions.id"],
            name=op.f("fk_student_state_session_id_learning_sessions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["identity.students.id"],
            name=op.f("fk_student_state_student_id_students"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"], ["learning.tasks.id"], name=op.f("fk_student_state_task_id_tasks"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_student_state")),
        sa.UniqueConstraint("student_id", name=op.f("uq_student_state_student_id")),
        schema="learning",
    )
    op.create_table(
        "ai_interactions",
        sa.Column("session_id", sa.UUID(), nullable=True),
        sa.Column("student_id", sa.UUID(), nullable=True),
        sa.Column("interaction_id", sa.UUID(), nullable=True),
        sa.Column("scaffold_event_id", sa.UUID(), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=True),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("prompt_hash", sa.String(length=64), nullable=False),
        sa.Column("prompt", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("raw_output", sa.Text(), nullable=True),
        sa.Column(
            "validation", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column("approved", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint(
            "purpose IN ('INTERPRET_OPEN_ANSWER', 'ADAPT_LANGUAGE', 'FORMULATE_QUESTION', 'ANALYZE_EXPLANATION', 'DETECT_CONTRADICTION')",
            name=op.f("ck_ai_interactions_purpose_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["interaction_id"],
            ["learning.interactions.id"],
            name=op.f("fk_ai_interactions_interaction_id_interactions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["learning.learning_sessions.id"],
            name=op.f("fk_ai_interactions_session_id_learning_sessions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["identity.students.id"],
            name=op.f("fk_ai_interactions_student_id_students"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_interactions")),
        schema="learning",
    )
    op.create_index(
        "ix_learning_ai_interactions_session",
        "ai_interactions",
        ["session_id", "created_at"],
        unique=False,
        schema="learning",
    )
    op.create_table(
        "interaction_evidence",
        sa.Column("interaction_id", sa.UUID(), nullable=False),
        sa.Column("student_id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("window_size", sa.Integer(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["interaction_id"],
            ["learning.interactions.id"],
            name=op.f("fk_interaction_evidence_interaction_id_interactions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["learning.learning_sessions.id"],
            name=op.f("fk_interaction_evidence_session_id_learning_sessions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["identity.students.id"],
            name=op.f("fk_interaction_evidence_student_id_students"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"], ["learning.tasks.id"], name=op.f("fk_interaction_evidence_task_id_tasks"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_interaction_evidence")),
        schema="learning",
    )
    op.create_index(
        "ix_learning_interaction_evidence_student",
        "interaction_evidence",
        ["student_id", "created_at"],
        unique=False,
        schema="learning",
    )
    op.create_table(
        "student_state_history",
        sa.Column("student_id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=True),
        sa.Column("interaction_id", sa.UUID(), nullable=True),
        sa.Column("previous_state", sa.String(length=16), nullable=False),
        sa.Column("evidence_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("posterior", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("inferred_state", sa.String(length=16), nullable=False),
        sa.Column("rule_fired", sa.String(length=48), nullable=True),
        sa.Column("current_state", sa.String(length=16), nullable=False),
        sa.Column("help_level", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("fading_action", sa.String(length=16), server_default=sa.text("'KEEP'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["interaction_id"],
            ["learning.interactions.id"],
            name=op.f("fk_student_state_history_interaction_id_interactions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["learning.learning_sessions.id"],
            name=op.f("fk_student_state_history_session_id_learning_sessions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["identity.students.id"],
            name=op.f("fk_student_state_history_student_id_students"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"], ["learning.tasks.id"], name=op.f("fk_student_state_history_task_id_tasks"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_student_state_history")),
        schema="learning",
    )
    op.create_index(
        "ix_learning_student_state_history_session",
        "student_state_history",
        ["session_id"],
        unique=False,
        schema="learning",
    )
    op.create_index(
        "ix_learning_student_state_history_student",
        "student_state_history",
        ["student_id", "created_at"],
        unique=False,
        schema="learning",
    )


def downgrade() -> None:
    op.drop_index("ix_learning_student_state_history_student", table_name="student_state_history", schema="learning")
    op.drop_index("ix_learning_student_state_history_session", table_name="student_state_history", schema="learning")
    op.drop_table("student_state_history", schema="learning")
    op.drop_index("ix_learning_interaction_evidence_student", table_name="interaction_evidence", schema="learning")
    op.drop_table("interaction_evidence", schema="learning")
    op.drop_index("ix_learning_ai_interactions_session", table_name="ai_interactions", schema="learning")
    op.drop_table("ai_interactions", schema="learning")
    op.drop_table("student_state", schema="learning")
    op.drop_table("tutor_rules", schema="learning")
    op.drop_table("bayesian_config", schema="learning")
