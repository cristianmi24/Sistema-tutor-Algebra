"""Servicio de auditoría (append-only)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger, request_id_ctx
from app.core.security import truncate_ip
from app.modules.common.enums import AuditAction, AuditOutcome
from app.modules.ops.models import AuditLog

log = get_logger("app.audit")


def client_context(request: Request | None) -> dict[str, str | None]:
    if request is None:
        return {"ip_truncated": None, "user_agent": None}
    forwarded = request.headers.get("x-forwarded-for")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else None)
    user_agent = request.headers.get("user-agent")
    return {
        "ip_truncated": truncate_ip(ip),
        "user_agent": user_agent[:255] if user_agent else None,
    }


async def record_audit(
    db: AsyncSession,
    *,
    action: AuditAction,
    outcome: AuditOutcome,
    actor_user_id: uuid.UUID | None = None,
    actor_role: str | None = None,
    resource_type: str | None = None,
    resource_id: str | uuid.UUID | None = None,
    details: dict[str, Any] | None = None,
    request: Request | None = None,
) -> AuditLog:
    ctx = client_context(request)
    entry = AuditLog(
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        action=action.value,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        outcome=outcome.value,
        request_id=request_id_ctx.get(),
        ip_truncated=ctx["ip_truncated"],
        user_agent=ctx["user_agent"],
        details=details or {},
    )
    db.add(entry)
    log.info(
        "audit",
        action=action.value,
        outcome=outcome.value,
        actor=str(actor_user_id) if actor_user_id else None,
        resource_type=resource_type,
        resource_id=entry.resource_id,
    )
    return entry
