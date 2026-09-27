"""Autenticación: registro, login, refresh, logout, recuperación de contraseña, perfil."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response, status

from app.core.auth import AnyUserDep, load_user
from app.core.cookies import clear_refresh_cookie, read_refresh_cookie, set_refresh_cookie
from app.core.deps import DbDep, SettingsDep
from app.core.errors import NotFoundError
from app.core.ratelimit import auth_limit, limiter
from app.modules.identity import service
from app.modules.identity.email import EmailSender
from app.modules.identity.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterResponse,
    RegisterStudentRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserSummary,
)

router = APIRouter()


def _email_sender(request: Request) -> EmailSender:
    sender: EmailSender = request.app.state.email_sender
    return sender


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registro de estudiante con consentimiento",
)
@limiter.limit(auth_limit)
async def register(
    request: Request, payload: RegisterStudentRequest, db: DbDep, settings: SettingsDep
) -> RegisterResponse:
    user, student = await service.register_student(db, settings, payload, request)
    return RegisterResponse(
        user_id=user.id,
        participant_code=student.participant_code,
        status=user.status,
        research_status=student.research_status,
    )


@router.post("/login", response_model=TokenResponse, summary="Inicio de sesión")
@limiter.limit(auth_limit)
async def login(
    request: Request, response: Response, payload: LoginRequest, db: DbDep, settings: SettingsDep
) -> TokenResponse:
    user, access, expires_in, raw_refresh = await service.login(
        db, settings, identifier=payload.identifier, password=payload.password, request=request
    )
    set_refresh_cookie(response, settings, raw_refresh)
    return TokenResponse(access_token=access, expires_in=expires_in, user=service.user_summary(user))


@router.post("/refresh", response_model=TokenResponse, summary="Renovar sesión (rotación)")
@limiter.limit(auth_limit)
async def refresh(request: Request, response: Response, db: DbDep, settings: SettingsDep) -> TokenResponse:
    raw = read_refresh_cookie(request, settings)
    try:
        user, access, expires_in, new_raw = await service.refresh_session(
            db, settings, raw_refresh=raw, request=request
        )
    except Exception:
        clear_refresh_cookie(response, settings)
        raise
    set_refresh_cookie(response, settings, new_raw)
    return TokenResponse(access_token=access, expires_in=expires_in, user=service.user_summary(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Cerrar sesión")
async def logout(request: Request, response: Response, user: AnyUserDep, db: DbDep, settings: SettingsDep) -> Response:
    await service.logout(db, user, raw_refresh=read_refresh_cookie(request, settings), request=request)
    clear_refresh_cookie(response, settings)
    return Response(status_code=status.HTTP_204_NO_CONTENT, headers=dict(response.headers))


@router.post(
    "/forgot-password",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Solicitar restablecimiento (respuesta idéntica exista o no la cuenta)",
)
@limiter.limit(auth_limit)
async def forgot_password(
    request: Request, payload: ForgotPasswordRequest, db: DbDep, settings: SettingsDep
) -> dict[str, str]:
    await service.request_password_reset(db, settings, _email_sender(request), email=payload.email, request=request)
    return {"message": "Si la cuenta existe, recibirás un correo con instrucciones."}


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT, summary="Restablecer contraseña")
@limiter.limit(auth_limit)
async def reset_password(request: Request, payload: ResetPasswordRequest, db: DbDep) -> Response:
    await service.reset_password(db, token=payload.token, new_password=payload.new_password, request=request)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT, summary="Cambiar contraseña")
async def change_password(request: Request, payload: ChangePasswordRequest, user: AnyUserDep, db: DbDep) -> Response:
    await service.change_password(
        db,
        user_id=user.id,
        current_password=payload.current_password,
        new_password=payload.new_password,
        request=request,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserSummary, summary="Perfil mínimo del usuario autenticado")
async def me(user: AnyUserDep, db: DbDep) -> UserSummary:
    loaded = await load_user(db, user.id)
    if loaded is None:
        raise NotFoundError("Usuario no encontrado.")
    return service.user_summary(loaded)
