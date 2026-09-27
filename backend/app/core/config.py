"""Configuración tipada de la aplicación.

Todos los valores provienen de variables de entorno (o de un archivo ``.env`` en desarrollo).
Los secretos nunca se escriben en código ni se exponen al frontend.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

Environment = Literal["development", "test", "staging", "production"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Aplicación ---------------------------------------------------------
    app_name: str = "STI-GA API"
    app_env: Environment = "development"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"
    # NoDecode: los valores separados por coma se parsean en ``_split_csv`` (no como JSON).
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )

    # --- Base de datos -------------------------------------------------------
    database_url: str = "postgresql+psycopg://sti_app:sti_app_dev_password@localhost:5432/sti_dev"
    alembic_database_url: str | None = None
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_echo: bool = False
    database_uses_transaction_pooler: bool = False

    # --- Seguridad -----------------------------------------------------------
    # Marcador de posición: el validador de producción rechaza este valor.
    jwt_secret_key: str = "CHANGE_ME_generate_a_random_secret_of_at_least_32_characters"  # noqa: S105
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    jwt_issuer: str = "sti-ga"
    jwt_audience: str = "sti-ga-web"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 14
    password_reset_token_expire_minutes: int = 30
    password_reset_roles: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["ADMIN", "TEACHER", "RESEARCHER", "STUDENT"]
    )
    rate_limit_auth: str = "10/minute"

    # --- Documentos legales --------------------------------------------------
    privacy_policy_version: str = "2026.1"
    terms_version: str = "2026.1"

    # --- IA opcional ---------------------------------------------------------
    llm_enabled: bool = False
    llm_provider: Literal["null", "anthropic", "openai_compatible"] = "null"
    llm_model: str | None = None
    llm_api_key: str | None = None
    llm_timeout_ms: int = 8000
    llm_max_calls_per_session: int = 20

    # --- Validadores ---------------------------------------------------------
    @field_validator("cors_origins", "password_reset_roles", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("database_url", "alembic_database_url")
    @classmethod
    def _require_psycopg_driver(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.startswith("postgresql+psycopg://"):
            msg = (
                "DATABASE_URL debe usar el driver psycopg 3: "
                "'postgresql+psycopg://usuario:clave@host:puerto/base'"
            )
            raise ValueError(msg)
        return value

    @field_validator("password_reset_roles")
    @classmethod
    def _validate_roles(cls, roles: list[str]) -> list[str]:
        allowed = {"STUDENT", "TEACHER", "RESEARCHER", "ADMIN"}
        unknown = sorted(set(roles) - allowed)
        if unknown:
            msg = f"Roles desconocidos en PASSWORD_RESET_ROLES: {unknown}"
            raise ValueError(msg)
        return roles

    @model_validator(mode="after")
    def _enforce_production_hardening(self) -> Settings:
        if self.app_env == "production":
            problems: list[str] = []
            if self.debug:
                problems.append("DEBUG debe ser false en producción")
            if len(self.jwt_secret_key) < 32 or self.jwt_secret_key.startswith("CHANGE_ME"):
                problems.append("JWT_SECRET_KEY debe ser un secreto aleatorio de ≥ 32 caracteres")
            if any(origin.startswith("http://") for origin in self.cors_origins):
                problems.append("CORS_ORIGINS no debe incluir orígenes http:// en producción")
            if self.llm_enabled and not self.llm_api_key:
                problems.append("LLM_ENABLED=true requiere LLM_API_KEY")
            if problems:
                raise ValueError("Configuración insegura para producción: " + "; ".join(problems))
        return self

    # --- Derivados -----------------------------------------------------------
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def migrations_database_url(self) -> str:
        """URL usada por Alembic (conexión directa si se configuró)."""
        return self.alembic_database_url or self.database_url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
