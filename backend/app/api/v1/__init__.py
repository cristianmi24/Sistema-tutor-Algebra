"""Router agregado de la versión 1 de la API."""

from fastapi import APIRouter

from app.api.v1 import admin, auth, consents, health, legal, meta

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(meta.router, prefix="/meta", tags=["meta"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(legal.router, prefix="/legal", tags=["legal"])
api_router.include_router(consents.router, prefix="/consents", tags=["consents"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
