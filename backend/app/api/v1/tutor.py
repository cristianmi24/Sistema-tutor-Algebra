"""Motor adaptativo: perfil dinámico, historial, evidencias, simulación y configuración pedagógica."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AdminDep, ResearchStaffDep, StaffDep
from app.core.deps import DbDep
from app.core.errors import ConflictError, NotFoundError
from app.modules.common.enums import AuditAction, AuditOutcome
from app.modules.identity.models import Student
from app.modules.learning.scope import require_student_access
from app.modules.ops.audit import record_audit
from app.modules.tutor.bayes import BayesConfig, infer
from app.modules.tutor.defaults import DEFAULT_BAYES_CONFIG
from app.modules.tutor.evidence import Evidence, ScaffoldRecord
from app.modules.tutor.models import (
    BayesianConfig,
    InteractionEvidence,
    StudentStateHistory,
    StudentStateRow,
    TutorRule,
)
from app.modules.tutor.orchestrator import build_decision, load_bank, load_bayes_config, load_rules, run_engine
from app.modules.tutor.scaffolding import select_scaffold
from app.modules.tutor.schemas import (
    BayesianConfigIn,
    BayesianConfigOut,
    EvidenceOut,
    SimulationRequest,
    SimulationResult,
    StudentStateHistoryOut,
    StudentStateOut,
    TutorRuleIn,
    TutorRuleOut,
)

router = APIRouter()


def _state_out(row: StudentStateRow, participant_code: str | None) -> StudentStateOut:
    return StudentStateOut(
        student_id=row.student_id,
        participant_code=participant_code,
        session_id=row.session_id,
        task_id=row.task_id,
        current_skill=row.current_skill,
        current_difficulty=row.current_difficulty,
        recent_accuracy=float(row.recent_accuracy) if row.recent_accuracy is not None else None,
        average_response_time_ms=row.average_response_time_ms,
        click_pattern=row.click_pattern,
        attempt_count=row.attempt_count,
        repetition_count=row.repetition_count,
        error_pattern=row.error_pattern,
        confidence=float(row.confidence) if row.confidence is not None else None,
        current_state=row.current_state,
        previous_state=row.previous_state,
        current_help_level=row.current_help_level,
        last_intervention_id=row.last_intervention_id,
        intervention_result=row.intervention_result,
        posterior=row.posterior,
        updated_at=row.updated_at,
    )


async def _student_with_access(db: AsyncSession, user: Any, student_id: uuid.UUID) -> Student:
    return await require_student_access(db, user, student_id)


@router.get("/student-state/{student_id}", response_model=StudentStateOut, summary="Perfil dinámico vigente")
async def student_state(student_id: uuid.UUID, user: StaffDep, db: DbDep) -> StudentStateOut:
    student = await _student_with_access(db, user, student_id)
    row = await db.scalar(select(StudentStateRow).where(StudentStateRow.student_id == student_id))
    if row is None:
        raise NotFoundError("El estudiante aún no tiene perfil dinámico (sin interacciones significativas).")
    return _state_out(row, student.participant_code)


@router.get(
    "/student-state/{student_id}/history", response_model=list[StudentStateHistoryOut], summary="Historial del perfil"
)
async def student_state_history(
    student_id: uuid.UUID,
    user: StaffDep,
    db: DbDep,
    session_id: uuid.UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[StudentStateHistoryOut]:
    await _student_with_access(db, user, student_id)
    stmt = select(StudentStateHistory).where(StudentStateHistory.student_id == student_id)
    if session_id:
        stmt = stmt.where(StudentStateHistory.session_id == session_id)
    rows = (await db.execute(stmt.order_by(StudentStateHistory.created_at).limit(limit))).scalars()
    return [
        StudentStateHistoryOut(
            id=r.id,
            session_id=r.session_id,
            task_id=r.task_id,
            interaction_id=r.interaction_id,
            previous_state=r.previous_state,
            evidence_snapshot=r.evidence_snapshot,
            posterior=r.posterior,
            inferred_state=r.inferred_state,
            rule_fired=r.rule_fired,
            current_state=r.current_state,
            help_level=r.help_level,
            fading_action=r.fading_action,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.get("/evidence", response_model=list[EvidenceOut], summary="Evidencias extraídas por evento")
async def evidence(
    user: StaffDep, db: DbDep, session_id: uuid.UUID, task_id: uuid.UUID | None = None
) -> list[EvidenceOut]:
    from app.modules.learning.service import load_session

    session = await load_session(db, session_id)
    await _student_with_access(db, user, session.student_id)
    stmt = select(InteractionEvidence).where(InteractionEvidence.session_id == session_id)
    if task_id:
        stmt = stmt.where(InteractionEvidence.task_id == task_id)
    rows = (await db.execute(stmt.order_by(InteractionEvidence.created_at))).scalars()
    return [
        EvidenceOut(
            id=r.id,
            interaction_id=r.interaction_id,
            session_id=r.session_id,
            task_id=r.task_id,
            window_size=r.window_size,
            evidence=r.evidence,
            created_at=r.created_at,
        )
        for r in rows
    ]


NEUTRAL_EVIDENCE: dict[str, Any] = {
    "window_size": 5,
    "events_in_window": 0,
    "responses_in_window": 0,
    "response_time_ms": None,
    "response_time_band": "UNKNOWN",
    "fast_streak": 0,
    "recent_accuracy": None,
    "accuracy_band": "UNKNOWN",
    "attempt_count": 0,
    "repetition_count": 0,
    "click_pattern": "UNKNOWN",
    "error_pattern": "NONE",
    "last_error_pattern": None,
    "answer_changes": 0,
    "help_requests": 0,
    "help_requested_now": False,
    "prior_help_result": "NONE",
    "interventions_in_task": 0,
    "representation_switches": 0,
    "recent_errors_trend": "UNKNOWN",
    "stable_correct_streak": 0,
    "teacher_intervened_recently": False,
    "last_event_type": None,
    "difficulty": 2,
}


@router.post(
    "/scaffolding/decision",
    response_model=SimulationResult,
    summary="Simular la decisión del tutor con evidencias dadas",
)
async def simulate(payload: SimulationRequest, _: ResearchStaffDep, db: DbDep) -> SimulationResult:
    data = {**NEUTRAL_EVIDENCE, **payload.evidence}
    evidence_obj = Evidence(**data)
    posterior = infer(await load_bayes_config(db), evidence_obj.discretized())
    result = run_engine(
        evidence=evidence_obj,
        posterior=posterior,
        rules=await load_rules(db),
        previous_state=payload.previous_state,
        candidate_state=None,
        candidate_count=0,
    )
    memory = [
        ScaffoldRecord(
            code=m.get("code"),
            scaffold_type=m.get("scaffold_type"),
            level=int(m.get("level", 1)),
            result=str(m.get("result", "PENDING")),
            rejected=bool(m.get("rejected", False)),
            accepted=m.get("accepted"),
        )
        for m in payload.memory
    ]
    selection = select_scaffold(
        await load_bank(db),
        task_type=payload.task_type,
        skill=payload.skill,
        level=result.level,
        intervention=result.intervention,
        memory=memory,
    )
    decision = build_decision(
        evidence=evidence_obj,
        posterior=posterior,
        result=result,
        selection=selection,
        previous_state=payload.previous_state,
        previous_level=0,
        level=result.level,
        constraints=[],
        suggest_teacher=False,
    )
    return SimulationResult(
        evidence=evidence_obj.as_dict(),
        posterior=posterior.as_dict(),
        rule_result={
            "state": result.state,
            "level": result.level,
            "intervention": result.intervention,
            "fading": result.fading,
            "rule_code": result.rule_code,
            "matched": result.matched_codes,
            "confirmed": result.confirmed,
            "explanation": result.explanation,
        },
        decision=decision.as_dict(),
    )


# ----------------------------------------------------------------- reglas y Bayes (ADMIN edita, investigación lee)


def _rule_out(r: TutorRule) -> TutorRuleOut:
    return TutorRuleOut(
        id=r.id,
        code=r.code,
        name=r.name,
        description=r.description,
        priority=r.priority,
        min_consecutive=r.min_consecutive,
        conditions=r.conditions,
        actions=r.actions,
        version=r.version,
        is_active=r.is_active,
    )


@router.get("/tutor-rules", response_model=list[TutorRuleOut])
async def list_rules(_: ResearchStaffDep, db: DbDep) -> list[TutorRuleOut]:
    rows = (await db.execute(select(TutorRule).order_by(TutorRule.priority.desc(), TutorRule.code))).scalars()
    return [_rule_out(r) for r in rows]


@router.post("/tutor-rules", response_model=TutorRuleOut, status_code=status.HTTP_201_CREATED)
async def create_rule(request: Request, payload: TutorRuleIn, admin: AdminDep, db: DbDep) -> TutorRuleOut:
    if await db.scalar(select(TutorRule.id).where(TutorRule.code == payload.code)):
        raise ConflictError("Ya existe una regla con ese código.")
    row = TutorRule(**payload.model_dump())
    db.add(row)
    await db.flush()
    await record_audit(
        db,
        action=AuditAction.RULE_UPDATED,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=admin.id,
        actor_role=admin.role.value,
        resource_type="tutor_rule",
        resource_id=row.id,
        details={"created": payload.code},
        request=request,
    )
    return _rule_out(row)


@router.put("/tutor-rules/{rule_id}", response_model=TutorRuleOut)
async def update_rule(
    request: Request, rule_id: uuid.UUID, payload: TutorRuleIn, admin: AdminDep, db: DbDep
) -> TutorRuleOut:
    row = await db.get(TutorRule, rule_id)
    if row is None:
        raise NotFoundError("Regla no encontrada.")
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    row.version += 1
    await record_audit(
        db,
        action=AuditAction.RULE_UPDATED,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=admin.id,
        actor_role=admin.role.value,
        resource_type="tutor_rule",
        resource_id=row.id,
        details={"updated": payload.code, "version": row.version},
        request=request,
    )
    return _rule_out(row)


def _bayes_out(b: BayesianConfig) -> BayesianConfigOut:
    return BayesianConfigOut(
        id=b.id,
        name=b.name,
        version=b.version,
        priors=b.priors,
        likelihoods=b.likelihoods,
        thresholds=b.thresholds,
        is_active=b.is_active,
    )


@router.get("/bayesian-config", response_model=list[BayesianConfigOut])
async def list_bayes(_: ResearchStaffDep, db: DbDep) -> list[BayesianConfigOut]:
    rows = (await db.execute(select(BayesianConfig).order_by(BayesianConfig.version.desc()))).scalars()
    return [_bayes_out(b) for b in rows]


@router.get(
    "/bayesian-config/default", response_model=dict[str, Any], summary="Configuración bayesiana de respaldo (código)"
)
async def default_bayes(_: ResearchStaffDep) -> dict[str, Any]:
    return DEFAULT_BAYES_CONFIG


@router.post(
    "/bayesian-config",
    response_model=BayesianConfigOut,
    status_code=status.HTTP_201_CREATED,
    summary="Nueva versión de la configuración",
)
async def create_bayes(request: Request, payload: BayesianConfigIn, admin: AdminDep, db: DbDep) -> BayesianConfigOut:
    BayesConfig.from_dict(
        {"name": payload.name, "priors": payload.priors, "likelihoods": payload.likelihoods}
    )  # valida forma
    latest = await db.scalar(
        select(BayesianConfig).where(BayesianConfig.name == payload.name).order_by(BayesianConfig.version.desc())
    )
    if latest is not None:
        latest.is_active = False
        latest.name = f"{latest.name}@v{latest.version}"
    row = BayesianConfig(
        name=payload.name,
        version=(latest.version + 1) if latest else 1,
        priors=payload.priors,
        likelihoods=payload.likelihoods,
        thresholds=payload.thresholds,
        is_active=payload.is_active,
    )
    db.add(row)
    await db.flush()
    await record_audit(
        db,
        action=AuditAction.RULE_UPDATED,
        outcome=AuditOutcome.SUCCESS,
        actor_user_id=admin.id,
        actor_role=admin.role.value,
        resource_type="bayesian_config",
        resource_id=row.id,
        details={"name": payload.name, "version": row.version},
        request=request,
    )
    return _bayes_out(row)
