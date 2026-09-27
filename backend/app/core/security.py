"""Primitivas de seguridad: Argon2id, JWT de acceso, tokens opacos y hashing de tokens.

Nunca se almacenan contraseñas ni tokens de refresco/recuperación en texto plano.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import Settings

# Parámetros Argon2id (RFC 9106, perfil moderado). Rehash automático si cambian.
_hasher = PasswordHasher(time_cost=3, memory_cost=64 * 1024, parallelism=2, hash_len=32, salt_len=16)

# Contraseñas comprometidas comunes (lista mínima local; ampliable sin red).
COMMON_PASSWORDS: frozenset[str] = frozenset(
    {
        "password",
        "password1",
        "password123",
        "contrasena",
        "contraseña",
        "12345678",
        "123456789",
        "1234567890",
        "qwertyuiop",
        "iloveyou",
        "estudiante",
        "colegio123",
        "matematicas",
        "abcdefgh",
        "11111111",
        "00000000",
    }
)

PASSWORD_MIN_LENGTH = 10
PASSWORD_MAX_LENGTH = 128


def validate_password_policy(password: str) -> str | None:
    """Devuelve un mensaje de error o ``None`` si la contraseña cumple la política."""
    if len(password) < PASSWORD_MIN_LENGTH:
        return f"La contraseña debe tener al menos {PASSWORD_MIN_LENGTH} caracteres."
    if len(password) > PASSWORD_MAX_LENGTH:
        return f"La contraseña no puede superar {PASSWORD_MAX_LENGTH} caracteres."
    if password.lower() in COMMON_PASSWORDS:
        return "Esa contraseña es demasiado común. Elige otra."
    if password.isdigit():
        return "La contraseña no puede estar formada solo por números."
    return None


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> tuple[bool, bool]:
    """Devuelve ``(válida, necesita_rehash)``. Nunca lanza por hash inválido."""
    try:
        _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False, False
    return True, _hasher.check_needs_rehash(password_hash)


# Hash "dummy" para igualar el tiempo de respuesta cuando el usuario no existe (anti-enumeración).
DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(24))


def generate_opaque_token(nbytes: int = 48) -> str:
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def tokens_match(token_hash_a: str, token_hash_b: str) -> bool:
    return hmac.compare_digest(token_hash_a, token_hash_b)


def utcnow() -> datetime:
    return datetime.now(UTC)


def create_access_token(
    settings: Settings,
    *,
    user_id: uuid.UUID,
    role: str,
    session_family_id: uuid.UUID,
    expires_delta: timedelta | None = None,
) -> tuple[str, datetime]:
    now = utcnow()
    expires_at = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "sid": str(session_family_id),
        "jti": uuid.uuid4().hex,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "typ": "access",
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expires_at


class TokenError(Exception):
    """Token inválido, expirado o con claims incorrectos."""


def decode_access_token(settings: Settings, token: str) -> dict[str, Any]:
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={"require": ["exp", "iat", "sub", "iss", "aud", "jti"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("invalid") from exc
    if payload.get("typ") != "access":
        raise TokenError("invalid")
    return payload


def truncate_ip(ip: str | None) -> str | None:
    """Trunca la IP para minimizar datos: IPv4 → /16, IPv6 → /48."""
    if not ip:
        return None
    if ":" in ip:
        parts = ip.split(":")
        return ":".join(parts[:3]) + "::"
    octets = ip.split(".")
    if len(octets) == 4:
        return f"{octets[0]}.{octets[1]}.0.0"
    return None
