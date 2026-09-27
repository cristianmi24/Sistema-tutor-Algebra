"""Las migraciones deben aplicarse, revertirse y coincidir con los modelos (sin deriva)."""

from __future__ import annotations

import pytest
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from app.core.config import Settings
from app.core.database import ALL_SCHEMAS
from app.models import Base
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from tests.conftest import run_alembic


def test_upgrade_downgrade_and_no_drift(settings: Settings, database_available: bool) -> None:
    if not database_available:
        pytest.skip("PostgreSQL no disponible")
    url = settings.database_url
    run_alembic(url, "downgrade", "base")
    run_alembic(url, "upgrade", "head")

    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            assert set(ALL_SCHEMAS) <= set(inspect(conn).get_schema_names())
            tables = set(inspect(conn).get_table_names(schema="identity"))
            assert {"users", "students", "consents", "refresh_tokens"} <= tables

            ctx = MigrationContext.configure(
                conn,
                opts={
                    "compare_type": True,
                    "include_schemas": True,
                    "version_table_schema": "ops",
                    "include_object": lambda obj, name, type_, *_: (
                        type_ != "table" or getattr(obj, "schema", None) in ALL_SCHEMAS
                    ),
                },
            )
            diff = compare_metadata(ctx, Base.metadata)
            assert diff == [], f"Deriva entre modelos y migración: {diff}"

            with pytest.raises(IntegrityError, match="ck_users_role_allowed"):
                conn.execute(text("INSERT INTO identity.users (password_hash, role) VALUES ('x', 'SUPERUSER')"))
            conn.rollback()

            conn.execute(
                text(
                    "INSERT INTO identity.users (password_hash, role, email) VALUES ('x', 'ADMIN', 'Admin@Example.edu')"
                )
            )
            with pytest.raises(IntegrityError, match="uq_identity_users_email_lower"):
                conn.execute(
                    text(
                        "INSERT INTO identity.users (password_hash, role, email) "
                        "VALUES ('x', 'ADMIN', 'admin@example.edu')"
                    )
                )
            conn.rollback()
    finally:
        engine.dispose()
