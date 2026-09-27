"""Pruebas de configuración: parseo de listas, validaciones y endurecimiento en producción."""

from __future__ import annotations

import pytest
from app.core.config import Settings
from pydantic import ValidationError


def _settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)  # type: ignore[call-arg]


def test_csv_lists_are_parsed() -> None:
    s = _settings(cors_origins="http://a.test, http://b.test", password_reset_roles="ADMIN, TEACHER")
    assert s.cors_origins == ["http://a.test", "http://b.test"]
    assert s.password_reset_roles == ["ADMIN", "TEACHER"]


def test_database_url_requires_psycopg_driver() -> None:
    with pytest.raises(ValidationError, match="psycopg"):
        _settings(database_url="postgresql://user:pass@localhost/db")


def test_unknown_reset_role_is_rejected() -> None:
    with pytest.raises(ValidationError, match="PASSWORD_RESET_ROLES"):
        _settings(password_reset_roles="ADMIN,SUPERUSER")


def test_production_rejects_insecure_defaults() -> None:
    with pytest.raises(ValidationError) as exc:
        _settings(app_env="production", debug=True)
    message = str(exc.value)
    assert "DEBUG" in message
    assert "JWT_SECRET_KEY" in message
    assert "CORS_ORIGINS" in message


def test_production_accepts_hardened_config() -> None:
    s = _settings(
        app_env="production",
        debug=False,
        jwt_secret_key="x" * 48,
        cors_origins="https://tutor.example.edu",
    )
    assert s.is_production
    assert s.migrations_database_url == s.database_url


def test_alembic_url_overrides_migrations_url() -> None:
    s = _settings(alembic_database_url="postgresql+psycopg://u:p@direct.host:5432/db")
    assert s.migrations_database_url.startswith("postgresql+psycopg://u:p@direct.host")
