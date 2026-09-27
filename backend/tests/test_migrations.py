"""La migración 0001 debe aplicarse, revertirse y coincidir con los modelos (sin deriva).

Prueba sincrónica: ``alembic/env.py`` ejecuta ``asyncio.run`` y no puede correr dentro de un
loop activo.
"""

from __future__ import annotations

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from app.core import config as config_module
from app.core.config import Settings
from app.core.database import ALL_SCHEMAS
from app.models import Base
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError


def _database_available(url: str) -> bool:
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
    finally:
        engine.dispose()


def test_upgrade_downgrade_and_no_drift(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    if not _database_available(settings.database_url):
        pytest.skip("PostgreSQL no disponible")

    monkeypatch.setenv("DATABASE_URL", settings.database_url)
    monkeypatch.delenv("ALEMBIC_DATABASE_URL", raising=False)
    config_module.get_settings.cache_clear()
    cfg = Config("alembic.ini")

    try:
        command.downgrade(cfg, "base")
        command.upgrade(cfg, "head")

        engine = create_engine(settings.database_url)
        try:
            with engine.connect() as conn:
                schemas = set(inspect(conn).get_schema_names())
                assert set(ALL_SCHEMAS) <= schemas

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

                # Vocabularios cerrados protegidos por CHECK.
                with pytest.raises(IntegrityError, match="ck_users_role_allowed"):
                    conn.execute(
                        text(
                            "INSERT INTO identity.users (password_hash, role) "
                            "VALUES ('x', 'SUPERUSER')"
                        )
                    )
                conn.rollback()

                # Unicidad de correo insensible a mayúsculas.
                conn.execute(
                    text(
                        "INSERT INTO identity.users (password_hash, role, email) "
                        "VALUES ('x', 'ADMIN', 'Admin@Example.edu')"
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
    finally:
        config_module.get_settings.cache_clear()
