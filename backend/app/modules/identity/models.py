"""Modelos SQLAlchemy del esquema ``identity``.

Ver ``docs/04-modelo-de-datos.md`` §2. Los enumerados se almacenan como ``VARCHAR`` + ``CHECK``.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import SCHEMA_IDENTITY, Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.modules.common.enums import (
    ConsentParty,
    ConsentStatus,
    Grade,
    LegalDocumentKind,
    Role,
    UserStatus,
    values,
)


def _in_list(column: str, options: list[str]) -> str:
    quoted = ", ".join(f"'{option}'" for option in options)
    return f"{column} IN ({quoted})"


class Institution(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "institutions"
    __table_args__ = ({"schema": SCHEMA_IDENTITY},)

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    country: Mapped[str | None] = mapped_column(String(2))
    city: Mapped[str | None] = mapped_column(String(120))
    # Política de consentimiento requerida para menores,
    # p.ej. {"required_parties": ["STUDENT", "GUARDIAN"]}
    consent_policy: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    retention_days: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    users: Mapped[list[User]] = relationship(back_populates="institution")


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(_in_list("role", values(Role)), name="role_allowed"),
        CheckConstraint(_in_list("status", values(UserStatus)), name="status_allowed"),
        Index("ix_identity_users_institution_role", "institution_id", "role"),
        # Unicidad de correo insensible a mayúsculas/minúsculas.
        Index("uq_identity_users_email_lower", func.lower(text("email")), unique=True),
        {"schema": SCHEMA_IDENTITY},
    )

    institution_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(f"{SCHEMA_IDENTITY}.institutions.id", ondelete="RESTRICT")
    )
    email: Mapped[str | None] = mapped_column(String(254))
    username: Mapped[str | None] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, server_default=text(f"'{UserStatus.ACTIVE.value}'"))
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    locked_until: Mapped[datetime | None] = mapped_column()
    last_login_at: Mapped[datetime | None] = mapped_column()
    password_changed_at: Mapped[datetime | None] = mapped_column()

    institution: Mapped[Institution | None] = relationship(back_populates="users")
    student_profile: Mapped[Student | None] = relationship(back_populates="user", uselist=False)
    teacher_profile: Mapped[Teacher | None] = relationship(back_populates="user", uselist=False)
    researcher_profile: Mapped[Researcher | None] = relationship(back_populates="user", uselist=False)
    consents: Mapped[list[Consent]] = relationship(back_populates="user")


class Student(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Perfil de estudiante. ``id`` es el identificador opaco usado por learning/research."""

    __tablename__ = "students"
    __table_args__ = (
        CheckConstraint(_in_list("grade", values(Grade)), name="grade_allowed"),
        CheckConstraint("research_status IN ('PENDING', 'ELIGIBLE', 'EXCLUDED')", name="research_status_allowed"),
        UniqueConstraint("institution_id", "participant_code"),
        Index("ix_identity_students_institution_grade_group", "institution_id", "grade", "group_code"),
        {"schema": SCHEMA_IDENTITY},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_IDENTITY}.users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    institution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_IDENTITY}.institutions.id", ondelete="RESTRICT"), nullable=False
    )
    participant_code: Mapped[str] = mapped_column(String(16), nullable=False)  # STU-001
    grade: Mapped[str] = mapped_column(String(2), nullable=False)
    group_code: Mapped[str | None] = mapped_column(String(16))
    birth_year: Mapped[int | None] = mapped_column(Integer)
    # Participación efectiva en la investigación según la política de consentimiento de la
    # institución: PENDING (falta alguna parte), ELIGIBLE, EXCLUDED (alguna parte declinó/revocó).
    research_status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'PENDING'"))

    user: Mapped[User] = relationship(back_populates="student_profile")


class Teacher(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "teachers"
    __table_args__ = (
        UniqueConstraint("institution_id", "display_code"),
        {"schema": SCHEMA_IDENTITY},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_IDENTITY}.users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    institution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_IDENTITY}.institutions.id", ondelete="RESTRICT"), nullable=False
    )
    display_code: Mapped[str] = mapped_column(String(16), nullable=False)  # TEA-001

    user: Mapped[User] = relationship(back_populates="teacher_profile")
    group_assignments: Mapped[list[TeacherGroupAssignment]] = relationship(back_populates="teacher")


class Researcher(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "researchers"
    __table_args__ = ({"schema": SCHEMA_IDENTITY},)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_IDENTITY}.users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    institution_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(f"{SCHEMA_IDENTITY}.institutions.id", ondelete="RESTRICT")
    )
    display_code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)  # RES-001

    user: Mapped[User] = relationship(back_populates="researcher_profile")


class TeacherGroupAssignment(UUIDPrimaryKeyMixin, Base):
    """Alcance (scope) del docente: institución + grado + grupo."""

    __tablename__ = "teacher_group_assignments"
    __table_args__ = (
        CheckConstraint(_in_list("grade", values(Grade)), name="grade_allowed"),
        UniqueConstraint("teacher_id", "institution_id", "grade", "group_code"),
        {"schema": SCHEMA_IDENTITY},
    )

    teacher_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_IDENTITY}.teachers.id", ondelete="CASCADE"), nullable=False
    )
    institution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_IDENTITY}.institutions.id", ondelete="RESTRICT"), nullable=False
    )
    grade: Mapped[str] = mapped_column(String(2), nullable=False)
    group_code: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"), nullable=False)

    teacher: Mapped[Teacher] = relationship(back_populates="group_assignments")


class LegalDocument(UUIDPrimaryKeyMixin, Base):
    """Política de privacidad y términos, versionados y mostrados en el registro."""

    __tablename__ = "legal_documents"
    __table_args__ = (
        CheckConstraint(_in_list("kind", values(LegalDocumentKind)), name="kind_allowed"),
        UniqueConstraint("kind", "version", "locale"),
        {"schema": SCHEMA_IDENTITY},
    )

    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    locale: Mapped[str] = mapped_column(String(8), nullable=False, server_default=text("'es-CO'"))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column()
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"), nullable=False)


class Consent(UUIDPrimaryKeyMixin, Base):
    """Registro de consentimiento por parte (estudiante, acudiente, institución, investigador)."""

    __tablename__ = "consents"
    __table_args__ = (
        CheckConstraint(_in_list("consent_party", values(ConsentParty)), name="party_allowed"),
        CheckConstraint(_in_list("consent_status", values(ConsentStatus)), name="status_allowed"),
        Index("ix_identity_consents_user_party", "user_id", "consent_party"),
        {"schema": SCHEMA_IDENTITY},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_IDENTITY}.users.id", ondelete="CASCADE"), nullable=False
    )
    consent_party: Mapped[str] = mapped_column(String(16), nullable=False)
    privacy_policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    terms_version: Mapped[str] = mapped_column(String(32), nullable=False)
    consent_status: Mapped[str] = mapped_column(String(16), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column()
    revoked_at: Mapped[datetime | None] = mapped_column()
    # {"method": "web_form", "ip_truncated": "190.24.0.0", "user_agent": "...",
    #  "guardian_reference": "..."}
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"), nullable=False)

    user: Mapped[User] = relationship(back_populates="consents")


class RefreshToken(UUIDPrimaryKeyMixin, Base):
    """Refresh token opaco: solo se guarda su hash. Rotación por familia (ver docs/03)."""

    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("ix_identity_refresh_tokens_user", "user_id"),
        Index("ix_identity_refresh_tokens_family", "family_id"),
        {"schema": SCHEMA_IDENTITY},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_IDENTITY}.users.id", ondelete="CASCADE"), nullable=False
    )
    family_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(server_default=text("now()"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column()
    revoked_reason: Mapped[str | None] = mapped_column(String(64))
    rotated_to: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(f"{SCHEMA_IDENTITY}.refresh_tokens.id", ondelete="SET NULL")
    )
    user_agent: Mapped[str | None] = mapped_column(String(255))
    ip_truncated: Mapped[str | None] = mapped_column(String(45))


class PasswordResetToken(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "password_reset_tokens"
    __table_args__ = (
        Index("ix_identity_password_reset_tokens_user", "user_id"),
        {"schema": SCHEMA_IDENTITY},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_IDENTITY}.users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    used_at: Mapped[datetime | None] = mapped_column()
    requested_ip_truncated: Mapped[str | None] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"), nullable=False)
