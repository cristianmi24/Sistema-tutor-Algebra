"""Entorno de Alembic (async, psycopg 3) con soporte para múltiples esquemas."""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from app.core.config import get_settings
from app.core.database import ALL_SCHEMAS
from app.models import Base
from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.migrations_database_url)

target_metadata = Base.metadata


def include_object(obj: object, name: str | None, type_: str, *_args: object) -> bool:
    """Solo se autogeneran objetos de nuestros esquemas (ignora ``public`` y extensiones)."""
    if type_ == "table":
        return getattr(obj, "schema", None) in ALL_SCHEMAS
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        include_object=include_object,
        version_table_schema="ops",
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def ensure_schemas(connection: Connection) -> None:
    """Crea los esquemas antes de que Alembic cree ``ops.alembic_version``."""
    for schema in ALL_SCHEMAS:
        connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
    connection.commit()


def do_run_migrations(connection: Connection) -> None:
    ensure_schemas(connection)
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        include_object=include_object,
        version_table_schema="ops",
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
