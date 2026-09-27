"""Fundación: esquemas PostgreSQL, identidad (PII) y operación (auditoría).

Crea los cuatro esquemas del sistema (identity, learning, research, ops) y las tablas del
esquema ``identity`` (instituciones, usuarios, perfiles por rol, alcance docente, documentos
legales, consentimientos, refresh tokens, tokens de recuperación) y del esquema ``ops``
(auditoría append-only y configuración). Ver docs/04-modelo-de-datos.md.

Revision ID: 0001
Revises:
Create Date: 2026-09-27 00:53:23.263763+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SCHEMAS = ("identity", "learning", "research", "ops")


def upgrade() -> None:
    for schema in SCHEMAS:
        op.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')

    op.create_table(
        "institutions",
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("country", sa.String(length=2), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column(
            "consent_policy",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("retention_days", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_institutions")),
        sa.UniqueConstraint("code", name=op.f("uq_institutions_code")),
        schema="identity",
    )
    op.create_table(
        "legal_documents",
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("locale", sa.String(length=8), server_default=sa.text("'es-CO'"), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body_markdown", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint("kind IN ('PRIVACY_POLICY', 'TERMS')", name=op.f("ck_legal_documents_kind_allowed")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_legal_documents")),
        sa.UniqueConstraint("kind", "version", "locale", name=op.f("uq_legal_documents_kind_version_locale")),
        schema="identity",
    )
    op.create_table(
        "audit_logs",
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("actor_user_id", sa.UUID(), nullable=True),
        sa.Column("actor_role", sa.String(length=16), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=True),
        sa.Column("resource_id", sa.String(length=64), nullable=True),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("ip_truncated", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint(
            "outcome IN ('SUCCESS', 'FAILURE', 'DENIED')",
            name=op.f("ck_audit_logs_outcome_allowed"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
        schema="ops",
    )
    op.create_index("ix_ops_audit_logs_action", "audit_logs", ["action"], unique=False, schema="ops")
    op.create_index(
        "ix_ops_audit_logs_actor_occurred",
        "audit_logs",
        ["actor_user_id", "occurred_at"],
        unique=False,
        schema="ops",
    )
    op.create_index("ix_ops_audit_logs_occurred_at", "audit_logs", ["occurred_at"], unique=False, schema="ops")
    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_system_settings")),
        schema="ops",
    )
    op.create_table(
        "users",
        sa.Column("institution_id", sa.UUID(), nullable=True),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=24), server_default=sa.text("'ACTIVE'"), nullable=False),
        sa.Column("failed_login_attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('STUDENT', 'TEACHER', 'RESEARCHER', 'ADMIN')",
            name=op.f("ck_users_role_allowed"),
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'PENDING_CONSENT', 'LOCKED', 'DISABLED')",
            name=op.f("ck_users_status_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["identity.institutions.id"],
            name=op.f("fk_users_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("username", name=op.f("uq_users_username")),
        schema="identity",
    )
    op.create_index(
        "ix_identity_users_institution_role",
        "users",
        ["institution_id", "role"],
        unique=False,
        schema="identity",
    )
    op.create_index(
        "uq_identity_users_email_lower",
        "users",
        [sa.literal_column("lower(email)")],
        unique=True,
        schema="identity",
    )
    op.create_table(
        "consents",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("consent_party", sa.String(length=16), nullable=False),
        sa.Column("privacy_policy_version", sa.String(length=32), nullable=False),
        sa.Column("terms_version", sa.String(length=32), nullable=False),
        sa.Column("consent_status", sa.String(length=16), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint(
            "consent_party IN ('STUDENT', 'GUARDIAN', 'INSTITUTION', 'RESEARCHER')",
            name=op.f("ck_consents_party_allowed"),
        ),
        sa.CheckConstraint(
            "consent_status IN ('PENDING', 'ACCEPTED', 'DECLINED', 'REVOKED')",
            name=op.f("ck_consents_status_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["identity.users.id"],
            name=op.f("fk_consents_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_consents")),
        schema="identity",
    )
    op.create_index(
        "ix_identity_consents_user_party",
        "consents",
        ["user_id", "consent_party"],
        unique=False,
        schema="identity",
    )
    op.create_table(
        "password_reset_tokens",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_ip_truncated", sa.String(length=45), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["identity.users.id"],
            name=op.f("fk_password_reset_tokens_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_password_reset_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_password_reset_tokens_token_hash")),
        schema="identity",
    )
    op.create_index(
        "ix_identity_password_reset_tokens_user",
        "password_reset_tokens",
        ["user_id"],
        unique=False,
        schema="identity",
    )
    op.create_table(
        "refresh_tokens",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("family_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_reason", sa.String(length=64), nullable=True),
        sa.Column("rotated_to", sa.UUID(), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("ip_truncated", sa.String(length=45), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["rotated_to"],
            ["identity.refresh_tokens.id"],
            name=op.f("fk_refresh_tokens_rotated_to_refresh_tokens"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["identity.users.id"],
            name=op.f("fk_refresh_tokens_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_refresh_tokens_token_hash")),
        schema="identity",
    )
    op.create_index(
        "ix_identity_refresh_tokens_family",
        "refresh_tokens",
        ["family_id"],
        unique=False,
        schema="identity",
    )
    op.create_index(
        "ix_identity_refresh_tokens_user",
        "refresh_tokens",
        ["user_id"],
        unique=False,
        schema="identity",
    )
    op.create_table(
        "researchers",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("institution_id", sa.UUID(), nullable=True),
        sa.Column("display_code", sa.String(length=16), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["identity.institutions.id"],
            name=op.f("fk_researchers_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["identity.users.id"],
            name=op.f("fk_researchers_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_researchers")),
        sa.UniqueConstraint("display_code", name=op.f("uq_researchers_display_code")),
        sa.UniqueConstraint("user_id", name=op.f("uq_researchers_user_id")),
        schema="identity",
    )
    op.create_table(
        "students",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("participant_code", sa.String(length=16), nullable=False),
        sa.Column("grade", sa.String(length=2), nullable=False),
        sa.Column("group_code", sa.String(length=16), nullable=True),
        sa.Column("birth_year", sa.Integer(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("grade IN ('7', '8', '9')", name=op.f("ck_students_grade_allowed")),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["identity.institutions.id"],
            name=op.f("fk_students_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["identity.users.id"],
            name=op.f("fk_students_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_students")),
        sa.UniqueConstraint(
            "institution_id",
            "participant_code",
            name=op.f("uq_students_institution_id_participant_code"),
        ),
        sa.UniqueConstraint("user_id", name=op.f("uq_students_user_id")),
        schema="identity",
    )
    op.create_index(
        "ix_identity_students_institution_grade_group",
        "students",
        ["institution_id", "grade", "group_code"],
        unique=False,
        schema="identity",
    )
    op.create_table(
        "teachers",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("display_code", sa.String(length=16), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["identity.institutions.id"],
            name=op.f("fk_teachers_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["identity.users.id"],
            name=op.f("fk_teachers_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_teachers")),
        sa.UniqueConstraint("institution_id", "display_code", name=op.f("uq_teachers_institution_id_display_code")),
        sa.UniqueConstraint("user_id", name=op.f("uq_teachers_user_id")),
        schema="identity",
    )
    op.create_table(
        "teacher_group_assignments",
        sa.Column("teacher_id", sa.UUID(), nullable=False),
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("grade", sa.String(length=2), nullable=False),
        sa.Column("group_code", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint("grade IN ('7', '8', '9')", name=op.f("ck_teacher_group_assignments_grade_allowed")),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["identity.institutions.id"],
            name=op.f("fk_teacher_group_assignments_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["teacher_id"],
            ["identity.teachers.id"],
            name=op.f("fk_teacher_group_assignments_teacher_id_teachers"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_teacher_group_assignments")),
        sa.UniqueConstraint(
            "teacher_id",
            "institution_id",
            "grade",
            "group_code",
            name=op.f("uq_teacher_group_assignments_teacher_id_institution_id_grade_group_code"),
        ),
        schema="identity",
    )


def downgrade() -> None:
    op.drop_table("teacher_group_assignments", schema="identity")
    op.drop_table("teachers", schema="identity")
    op.drop_index("ix_identity_students_institution_grade_group", table_name="students", schema="identity")
    op.drop_table("students", schema="identity")
    op.drop_table("researchers", schema="identity")
    op.drop_index("ix_identity_refresh_tokens_user", table_name="refresh_tokens", schema="identity")
    op.drop_index("ix_identity_refresh_tokens_family", table_name="refresh_tokens", schema="identity")
    op.drop_table("refresh_tokens", schema="identity")
    op.drop_index(
        "ix_identity_password_reset_tokens_user",
        table_name="password_reset_tokens",
        schema="identity",
    )
    op.drop_table("password_reset_tokens", schema="identity")
    op.drop_index("ix_identity_consents_user_party", table_name="consents", schema="identity")
    op.drop_table("consents", schema="identity")
    op.drop_index("uq_identity_users_email_lower", table_name="users", schema="identity")
    op.drop_index("ix_identity_users_institution_role", table_name="users", schema="identity")
    op.drop_table("users", schema="identity")
    op.drop_table("system_settings", schema="ops")
    op.drop_index("ix_ops_audit_logs_occurred_at", table_name="audit_logs", schema="ops")
    op.drop_index("ix_ops_audit_logs_actor_occurred", table_name="audit_logs", schema="ops")
    op.drop_index("ix_ops_audit_logs_action", table_name="audit_logs", schema="ops")
    op.drop_table("audit_logs", schema="ops")
    op.drop_table("legal_documents", schema="identity")
    op.drop_table("institutions", schema="identity")
