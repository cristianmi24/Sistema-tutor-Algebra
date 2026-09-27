"""Esquemas Pydantic del módulo de identidad (entradas con ``extra="forbid"``)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.core.security import validate_password_policy
from app.modules.common.enums import ConsentParty, ConsentStatus, Grade, LegalDocumentKind, Role


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ConsentIn(StrictModel):
    party: ConsentParty
    privacy_policy_version: str = Field(min_length=1, max_length=32)
    terms_version: str = Field(min_length=1, max_length=32)
    status: Literal["ACCEPTED", "DECLINED"] = "ACCEPTED"
    guardian_reference: str | None = Field(default=None, max_length=120)


class RegisterStudentRequest(StrictModel):
    """Registro de estudiante: datos mínimos + consentimiento del propio estudiante."""

    identifier: str = Field(min_length=3, max_length=254, description="Correo o nombre de usuario")
    password: str = Field(min_length=1, max_length=256)
    institution_code: str = Field(min_length=1, max_length=32)
    grade: Grade
    group_code: str | None = Field(default=None, max_length=16)
    birth_year: int | None = Field(default=None, ge=1990, le=2030)
    consents: list[ConsentIn] = Field(min_length=1, max_length=4)

    @field_validator("password")
    @classmethod
    def _policy(cls, value: str) -> str:
        error = validate_password_policy(value)
        if error:
            raise ValueError(error)
        return value

    @field_validator("identifier")
    @classmethod
    def _identifier(cls, value: str) -> str:
        value = value.strip()
        if "@" in value:
            return value.lower()
        if not value.replace("_", "").replace(".", "").replace("-", "").isalnum():
            raise ValueError("El usuario solo puede tener letras, números, '.', '-' o '_'.")
        return value.lower()

    @model_validator(mode="after")
    def _student_consent_present(self) -> RegisterStudentRequest:
        if not any(c.party == ConsentParty.STUDENT and c.status == "ACCEPTED" for c in self.consents):
            raise ValueError("Se requiere la aceptación del estudiante para crear la cuenta.")
        return self


class RegisterResponse(BaseModel):
    user_id: uuid.UUID
    participant_code: str
    status: str
    research_status: str


class LoginRequest(StrictModel):
    identifier: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class UserSummary(BaseModel):
    id: uuid.UUID
    role: Role
    status: str
    display_code: str
    institution_id: uuid.UUID | None
    email: str | None = None
    username: str | None = None
    grade: str | None = None
    group_code: str | None = None
    research_status: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105
    expires_in: int
    user: UserSummary


class ForgotPasswordRequest(StrictModel):
    email: EmailStr


class ResetPasswordRequest(StrictModel):
    token: str = Field(min_length=16, max_length=256)
    new_password: str = Field(min_length=1, max_length=256)

    @field_validator("new_password")
    @classmethod
    def _policy(cls, value: str) -> str:
        error = validate_password_policy(value)
        if error:
            raise ValueError(error)
        return value


class ChangePasswordRequest(StrictModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=1, max_length=256)

    @field_validator("new_password")
    @classmethod
    def _policy(cls, value: str) -> str:
        error = validate_password_policy(value)
        if error:
            raise ValueError(error)
        return value


class LegalDocumentOut(BaseModel):
    kind: LegalDocumentKind
    version: str
    locale: str
    title: str
    body_markdown: str
    published_at: datetime | None


class ConsentOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    consent_party: ConsentParty
    consent_status: ConsentStatus
    privacy_policy_version: str
    terms_version: str
    accepted_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


class ConsentRecordRequest(StrictModel):
    """Registro de consentimiento adicional (acudiente, institución) sobre un usuario."""

    user_id: uuid.UUID | None = None
    participant_code: str | None = Field(default=None, max_length=16)
    consent: ConsentIn

    @model_validator(mode="after")
    def _target(self) -> ConsentRecordRequest:
        if self.user_id is None and self.participant_code is None:
            raise ValueError("Indica user_id o participant_code.")
        return self


class InstitutionIn(StrictModel):
    code: str = Field(min_length=2, max_length=32, pattern=r"^[A-Z0-9_-]+$")
    name: str = Field(min_length=2, max_length=200)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    city: str | None = Field(default=None, max_length=120)
    consent_policy: dict[str, list[str]] = Field(default_factory=lambda: {"required_parties": ["STUDENT", "GUARDIAN"]})
    retention_days: int | None = Field(default=None, ge=30, le=3650)


class InstitutionOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    country: str | None
    city: str | None
    consent_policy: dict[str, object]
    retention_days: int | None
    is_active: bool


class InstitutionPublic(BaseModel):
    code: str
    name: str
    required_consent_parties: list[str]


class GroupAssignmentIn(StrictModel):
    grade: Grade
    group_code: str = Field(min_length=1, max_length=16)


class StaffUserCreate(StrictModel):
    """Creación de docentes, investigadores y administradores por un ADMIN."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=256)
    role: Literal["TEACHER", "RESEARCHER", "ADMIN"]
    institution_code: str | None = Field(default=None, max_length=32)
    group_assignments: list[GroupAssignmentIn] = Field(default_factory=list, max_length=20)

    @field_validator("password")
    @classmethod
    def _policy(cls, value: str) -> str:
        error = validate_password_policy(value)
        if error:
            raise ValueError(error)
        return value


class UserStatusUpdate(StrictModel):
    status: Literal["ACTIVE", "DISABLED"]


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int


class AuditLogOut(BaseModel):
    id: uuid.UUID
    occurred_at: datetime
    actor_user_id: uuid.UUID | None
    actor_role: str | None
    action: str
    resource_type: str | None
    resource_id: str | None
    outcome: str
    request_id: str | None
    details: dict[str, object]
