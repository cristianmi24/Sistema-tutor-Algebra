"""Dependencias de autenticación y autorización (RBAC + alcance) para FastAPI.

Toda ruta protegida declara sus roles con ``require_roles``. El frontend nunca es fuente de
verdad: aquí se vuelve a verificar cada petición.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import DbDep, SettingsDep
from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.security import TokenError, decode_access_token
from app.modules.common.enums import Role, UserStatus
from app.modules.identity.models import User

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class CurrentUser:
    id: uuid.UUID
    role: Role
    status: str
    institution_id: uuid.UUID | None
    session_family_id: uuid.UUID
    student_id: uuid.UUID | None = None
    teacher_id: uuid.UUID | None = None
    researcher_id: uuid.UUID | None = None
    participant_code: str | None = None
    display_code: str | None = None

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN


async def load_user(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.student_profile),
            selectinload(User.teacher_profile),
            selectinload(User.researcher_profile),
        )
        .where(User.id == user_id)
    )
    return result.scalar_one_or_none()


def build_current_user(user: User, session_family_id: uuid.UUID) -> CurrentUser:
    student = user.student_profile
    teacher = user.teacher_profile
    researcher = user.researcher_profile
    display_code = (
        student.participant_code
        if student
        else teacher.display_code
        if teacher
        else researcher.display_code
        if researcher
        else "ADM"
    )
    return CurrentUser(
        id=user.id,
        role=Role(user.role),
        status=user.status,
        institution_id=user.institution_id,
        session_family_id=session_family_id,
        student_id=student.id if student else None,
        teacher_id=teacher.id if teacher else None,
        researcher_id=researcher.id if researcher else None,
        participant_code=student.participant_code if student else None,
        display_code=display_code,
    )


async def get_current_user(
    request: Request,
    settings: SettingsDep,
    db: DbDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> CurrentUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("Se requiere autenticación.")
    try:
        payload = decode_access_token(settings, credentials.credentials)
    except TokenError as exc:
        message = "La sesión expiró." if str(exc) == "expired" else "Token inválido."
        raise UnauthorizedError(message, details={"reason": str(exc)}) from exc

    try:
        user_id = uuid.UUID(str(payload["sub"]))
        family_id = uuid.UUID(str(payload["sid"]))
    except (KeyError, ValueError) as exc:
        raise UnauthorizedError("Token inválido.") from exc

    user = await load_user(db, user_id)
    if user is None or user.status in (UserStatus.DISABLED, UserStatus.LOCKED):
        raise UnauthorizedError("La cuenta no está disponible.")
    if user.role != payload.get("role"):
        # El rol cambió después de emitir el token: obligar a reautenticar.
        raise UnauthorizedError("La sesión debe renovarse.")
    current = build_current_user(user, family_id)
    request.state.current_user = current
    return current


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def require_roles(*roles: Role) -> object:
    """Dependencia que exige uno de los roles indicados (403 si no)."""
    allowed = frozenset(roles)

    async def _checker(user: CurrentUserDep) -> CurrentUser:
        if user.role not in allowed:
            raise ForbiddenError("No tienes permiso para este recurso.")
        return user

    return Depends(_checker)


# Alias legibles por rol.
StudentDep = Annotated[CurrentUser, require_roles(Role.STUDENT)]
TeacherDep = Annotated[CurrentUser, require_roles(Role.TEACHER)]
ResearcherDep = Annotated[CurrentUser, require_roles(Role.RESEARCHER)]
AdminDep = Annotated[CurrentUser, require_roles(Role.ADMIN)]
StaffDep = Annotated[CurrentUser, require_roles(Role.TEACHER, Role.RESEARCHER, Role.ADMIN)]
ResearchStaffDep = Annotated[CurrentUser, require_roles(Role.RESEARCHER, Role.ADMIN)]
AnyUserDep = Annotated[CurrentUser, require_roles(Role.STUDENT, Role.TEACHER, Role.RESEARCHER, Role.ADMIN)]
