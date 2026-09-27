"""Estado de participación en investigación del estudiante (consentimiento efectivo).

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-27 01:17:24.868243+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "students",
        sa.Column(
            "research_status",
            sa.String(length=16),
            server_default=sa.text("'PENDING'"),
            nullable=False,
        ),
        schema="identity",
    )
    op.create_check_constraint(
        op.f("ck_students_research_status_allowed"),
        "students",
        "research_status IN ('PENDING', 'ELIGIBLE', 'EXCLUDED')",
        schema="identity",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_students_research_status_allowed"), "students", schema="identity", type_="check")
    op.drop_column("students", "research_status", schema="identity")
