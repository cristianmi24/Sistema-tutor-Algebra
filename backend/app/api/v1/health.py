"""Endpoints de salud: liveness (app) y readiness (base de datos)."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.database import check_database
from app.core.deps import EngineDep, SettingsDep
from app.core.errors import ServiceUnavailableError
from app.core.logging import get_logger

router = APIRouter()
log = get_logger(__name__)


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str
    environment: str


class ReadinessResponse(BaseModel):
    status: Literal["ready"]
    database: Literal["ok"]


@router.get("", response_model=HealthResponse, summary="Estado de la aplicación")
async def health(settings: SettingsDep) -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
    )


@router.get("/ready", response_model=ReadinessResponse, summary="Disponibilidad de la base de datos")
async def readiness(engine: EngineDep) -> ReadinessResponse:
    try:
        ok = await check_database(engine)
    except Exception as exc:
        log.warning("database_unreachable", error_type=type(exc).__name__)
        ok = False
    if not ok:
        raise ServiceUnavailableError("La base de datos no está disponible.")
    return ReadinessResponse(status="ready", database="ok")
