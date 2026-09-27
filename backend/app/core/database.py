"""Acceso a base de datos: engine async, fábrica de sesiones y base declarativa.

Esquemas PostgreSQL (ver docs/04-modelo-de-datos.md):

* ``identity`` — datos personales y credenciales.
* ``learning`` — sesiones, tareas, interacciones, estados, andamiajes (pseudonimizado).
* ``research`` — episodios, memos, entrevistas.
* ``ops``      — auditoría y configuración.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, MetaData, func, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import Settings

SCHEMA_IDENTITY = "identity"
SCHEMA_LEARNING = "learning"
SCHEMA_RESEARCH = "research"
SCHEMA_OPS = "ops"
ALL_SCHEMAS: tuple[str, ...] = (SCHEMA_IDENTITY, SCHEMA_LEARNING, SCHEMA_RESEARCH, SCHEMA_OPS)

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    # Todas las fechas se almacenan como TIMESTAMPTZ (UTC).
    type_annotation_map = {uuid.UUID: PG_UUID(as_uuid=True), datetime: DateTime(timezone=True)}


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), nullable=False)


def build_engine(settings: Settings) -> AsyncEngine:
    connect_args: dict[str, Any] = {}
    if settings.database_uses_transaction_pooler:
        # PgBouncer/Supavisor en modo transacción no soportan prepared statements con nombre.
        connect_args["prepare_threshold"] = None
    return create_async_engine(
        settings.database_url,
        echo=settings.database_echo,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


async def check_database(engine: AsyncEngine) -> bool:
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        return result.scalar_one() == 1


async def get_db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
