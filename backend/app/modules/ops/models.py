"""Modelos SQLAlchemy del esquema ``ops``."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import SCHEMA_OPS, Base, UUIDPrimaryKeyMixin
from app.modules.common.enums import AuditOutcome, values


class AuditLog(UUIDPrimaryKeyMixin, Base):
    """Registro de auditoría. Solo INSERT/SELECT desde la aplicación (append-only).

    ``actor_user_id`` no tiene clave foránea a propósito: el registro debe sobrevivir
    a la eliminación/anonimización del usuario.
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        CheckConstraint(
            "outcome IN (" + ", ".join(f"'{v}'" for v in values(AuditOutcome)) + ")",
            name="outcome_allowed",
        ),
        Index("ix_ops_audit_logs_occurred_at", "occurred_at"),
        Index("ix_ops_audit_logs_actor_occurred", "actor_user_id", "occurred_at"),
        Index("ix_ops_audit_logs_action", "action"),
        {"schema": SCHEMA_OPS},
    )

    occurred_at: Mapped[datetime] = mapped_column(server_default=text("now()"), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column()
    actor_role: Mapped[str | None] = mapped_column(String(16))
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(64))
    resource_id: Mapped[str | None] = mapped_column(String(64))
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(64))
    ip_truncated: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )


class SystemSetting(Base):
    __tablename__ = "system_settings"
    __table_args__ = ({"schema": SCHEMA_OPS},)

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    updated_by: Mapped[uuid.UUID | None] = mapped_column()
    updated_at: Mapped[datetime] = mapped_column(
        server_default=text("now()"), onupdate=text("now()"), nullable=False
    )
