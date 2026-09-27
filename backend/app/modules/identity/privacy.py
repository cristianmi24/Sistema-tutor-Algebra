"""Privacidad: anonimización irreversible de identidad y retención configurable por institución.

La anonimización elimina los datos personales de ``identity`` (correo, usuario, año de nacimiento,
credenciales, tokens, evidencia de consentimiento) y deshabilita la cuenta, pero conserva los
registros pseudonimizados de aprendizaje/investigación bajo el mismo ``participant_code``, según el
protocolo. La eliminación completa de datos de investigación, si el protocolo la exige, es una
decisión humana documentada (no automática).
"""

from __future__ import annotations

import secrets
import uuid
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, utcnow
from app.modules.common.enums import AuditAction, AuditOutcome, Role, UserStatus
from app.modules.identity.models import Consent, Institution, PasswordResetToken, Student, User
from app.modules.identity.service import revoke_all_user_tokens
from app.modules.learning.models import Interaction
from app.modules.ops.audit import record_audit


async def anonymize_user(
    db: AsyncSession, user: User, *, reason: str, actor_id: uuid.UUID | None, actor_role: str | None
) -> None:
    if user.role == Role.ADMIN.value and actor_id == user.id:
        raise ValueError("Un administrador no puede anonimizar su propia cuenta.")
    user.email = None
    user.username = f"anon-{uuid.uuid4().hex[:12]}"
    user.password_hash = hash_password(secrets.token_urlsafe(32))
    user.status = UserStatus.DISABLED.value
    user.failed_login_attempts = 0
    user.locked_until = None
    await revoke_all_user_tokens(db, user.id, reason="anonymized")
    for token in (await db.execute(select(PasswordResetToken).where(PasswordResetToken.user_id == user.id))).scalars():
        token.used_at = token.used_at or utcnow()
    for consent in (await db.execute(select(Consent).where(Consent.user_id == user.id))).scalars():
        consent.evidence = {"anonymized": True}
    student = await db.scalar(select(Student).where(Student.user_id == user.id))
    if student is not None:
        student.birth_year = None
    await record_audit(
        db,
        action=AuditAction.USER_UPDATED,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=actor_id,
        actor_role=actor_role,
        resource_type="user",
        resource_id=user.id,
        details={"anonymized": True, "reason": reason},
    )
    await db.flush()


async def apply_retention(db: AsyncSession, *, dry_run: bool = False) -> list[uuid.UUID]:
    """Anonimiza estudiantes sin actividad durante más de ``retention_days`` de su institución."""
    now = utcnow()
    affected: list[uuid.UUID] = []
    institutions = (
        (await db.execute(select(Institution).where(Institution.retention_days.is_not(None)))).scalars().all()
    )
    for institution in institutions:
        assert institution.retention_days is not None
        cutoff = now - timedelta(days=institution.retention_days)
        rows = (
            await db.execute(
                select(User, Student)
                .join(Student, Student.user_id == User.id)
                .where(
                    Student.institution_id == institution.id, User.email.is_not(None) | ~User.username.like("anon-%")
                )
            )
        ).all()
        for user, student in rows:
            last_activity = await db.scalar(
                select(func.max(Interaction.timestamp)).where(Interaction.student_id == student.id)
            )
            reference = last_activity or user.last_login_at or user.created_at
            if reference < cutoff:
                affected.append(user.id)
                if not dry_run:
                    await anonymize_user(
                        db,
                        user,
                        reason=f"retención de {institution.retention_days} días",
                        actor_id=None,
                        actor_role="SYSTEM",
                    )
    return affected
