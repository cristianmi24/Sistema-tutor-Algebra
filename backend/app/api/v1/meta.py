"""Metadatos públicos no sensibles: vocabularios del sistema y versiones legales vigentes.

El frontend los usa para poblar selectores y para mostrar la versión de política/términos
en el registro. No expone secretos ni datos de usuarios.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.deps import SettingsDep
from app.modules.common import enums

router = APIRouter()


class MetaResponse(BaseModel):
    roles: list[str]
    student_states: list[str]
    student_state_labels: dict[str, str]
    intervention_levels: list[str]
    task_types: list[str]
    worked_example_types: list[str]
    representations: list[str]
    scaffold_types: list[str]
    interaction_event_types: list[str]
    grades: list[str]
    privacy_policy_version: str
    terms_version: str
    llm_enabled: bool


@router.get("", response_model=MetaResponse, summary="Vocabularios y versiones vigentes")
async def meta(settings: SettingsDep) -> MetaResponse:
    return MetaResponse(
        roles=enums.values(enums.Role),
        student_states=enums.values(enums.StudentState),
        student_state_labels={
            state.value: label for state, label in enums.STUDENT_FACING_STATE_LABELS.items()
        },
        intervention_levels=enums.values(enums.InterventionLevel),
        task_types=enums.values(enums.TaskType),
        worked_example_types=enums.values(enums.WorkedExampleType),
        representations=enums.values(enums.Representation),
        scaffold_types=enums.values(enums.ScaffoldType),
        interaction_event_types=enums.values(enums.InteractionEventType),
        grades=enums.values(enums.Grade),
        privacy_policy_version=settings.privacy_policy_version,
        terms_version=settings.terms_version,
        llm_enabled=settings.llm_enabled,
    )
