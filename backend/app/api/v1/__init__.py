"""Router agregado de la versión 1 de la API."""

from fastapi import APIRouter

from app.api.v1 import health, meta

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(meta.router, prefix="/meta", tags=["meta"])
