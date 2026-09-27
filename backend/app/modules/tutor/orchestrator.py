"""RECORDAR: política adaptativa que conecta el motor puro con la persistencia.

Flujo por evento significativo (respuesta o solicitud de ayuda)::

    eventos + memoria → Evidence → Posterior → RuleResult → restricciones → Selection
        → InteractionEvidence, StudentState (upsert), StudentStateHistory, ScaffoldEvent (+HELP_OFFERED)
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings, get_settings
from app.modules.common.enums import StudentState
from app.modules.learning.models import Interaction, Scaffold, ScaffoldEvent, StudentResponse
from app.modules.learning.schemas import HelpOffer
from app.modules.learning.service import TutorContext, TutorOutcome, deliver_scaffold
from app.modules.tutor.bayes import BayesConfig, Posterior, infer
from app.modules.tutor.decision import ScaffoldDecision
from app.modules.tutor.defaults import DEFAULT_BAYES_CONFIG, DEFAULT_RULES
from app.modules.tutor.evidence import EventRecord, Evidence, ScaffoldRecord, extract_evidence
from app.modules.tutor.models import (
    BayesianConfig,
    InteractionEvidence,
    StudentStateHistory,
    StudentStateRow,
    TutorRule,
)
from app.modules.tutor.rules import Rule, RuleContext, RuleResult, evaluate_rules
from app.modules.tutor.scaffolding import ScaffoldCandidate, Selection, fading_action, select_scaffold


def content_key(content: dict[str, Any] | None) -> str | None:
    if not content:
        return None
    payload = {k: v for k, v in content.items() if k != "question_id"}
    return hashlib.sha1(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:16]  # noqa: S324


async def load_event_records(db: AsyncSession, session_id: uuid.UUID, task_id: uuid.UUID) -> list[EventRecord]:
    rows = (
        await db.execute(
            select(Interaction, StudentResponse)
            .outerjoin(StudentResponse, StudentResponse.id == Interaction.response_id)
            .where(Interaction.session_id == session_id, Interaction.task_id == task_id)
            .order_by(Interaction.sequence)
        )
    ).all()
    records: list[EventRecord] = []
    for interaction, response in rows:
        evaluation = response.evaluation if response is not None else {}
        records.append(
            EventRecord(
                sequence=interaction.sequence,
                event_type=interaction.event_type,
                timestamp=interaction.timestamp,
                task_id=str(interaction.task_id) if interaction.task_id else None,
                question_id=response.question_id if response is not None else None,
                correct=evaluation.get("correct") if response is not None else None,
                error_pattern=evaluation.get("error_pattern") if response is not None else None,
                representation=interaction.representation,
                content_key=content_key(response.content) if response is not None else None,
                client_meta=interaction.client_meta or {},
            )
        )
    return records


async def load_scaffold_memory(db: AsyncSession, session_id: uuid.UUID, task_id: uuid.UUID) -> list[ScaffoldRecord]:
    rows = (
        await db.execute(
            select(ScaffoldEvent, Interaction.sequence)
            .outerjoin(Interaction, Interaction.id == ScaffoldEvent.interaction_id)
            .options(selectinload(ScaffoldEvent.scaffold))
            .where(ScaffoldEvent.session_id == session_id, ScaffoldEvent.task_id == task_id)
            .order_by(ScaffoldEvent.created_at)
        )
    ).all()
    return [
        ScaffoldRecord(
            code=event.scaffold.code if event.scaffold else None,
            scaffold_type=event.scaffold.scaffold_type if event.scaffold else None,
            level=event.current_help_level,
            result=event.result,
            rejected=bool(event.rejected),
            accepted=event.accepted,
            created_sequence=sequence,
        )
        for event, sequence in rows
    ]


async def load_rules(db: AsyncSession) -> list[Rule]:
    rows = (await db.execute(select(TutorRule).where(TutorRule.is_active.is_(True)))).scalars().all()
    if not rows:
        return [Rule.from_dict(r) for r in DEFAULT_RULES]
    return [
        Rule(
            code=r.code,
            name=r.name,
            priority=r.priority,
            when=r.conditions,
            then=r.actions,
            min_consecutive=r.min_consecutive,
            description=r.description or "",
        )
        for r in rows
    ]


async def load_bayes_config(db: AsyncSession) -> BayesConfig:
    row = await db.scalar(
        select(BayesianConfig).where(BayesianConfig.is_active.is_(True)).order_by(BayesianConfig.version.desc())
    )
    if row is None:
        return BayesConfig.from_dict(DEFAULT_BAYES_CONFIG)
    return BayesConfig.from_dict(
        {
            "name": row.name,
            "version": row.version,
            "priors": row.priors,
            "likelihoods": row.likelihoods,
            "smoothing": row.thresholds.get("smoothing", 0.05),
        }
    )


async def load_bank(db: AsyncSession) -> list[ScaffoldCandidate]:
    rows = (await db.execute(select(Scaffold).where(Scaffold.is_active.is_(True)))).scalars().all()
    return [
        ScaffoldCandidate(
            code=s.code,
            scaffold_type=s.scaffold_type,
            level=s.level,
            applicable_task_types=list(s.applicable_task_types),
            applicable_skills=list(s.applicable_skills),
            content=s.content,
        )
        for s in rows
    ]


async def get_or_create_state(db: AsyncSession, student_id: uuid.UUID) -> StudentStateRow:
    row = await db.scalar(select(StudentStateRow).where(StudentStateRow.student_id == student_id))
    if row is None:
        row = StudentStateRow(student_id=student_id, current_state=StudentState.NORMAL.value)
        db.add(row)
        await db.flush()
    return row


def run_engine(
    *,
    evidence: Evidence,
    posterior: Posterior,
    rules: list[Rule],
    previous_state: str,
    candidate_state: str | None,
    candidate_count: int,
) -> RuleResult:
    ctx = RuleContext(
        evidence=evidence,
        posterior=posterior,
        previous_state=previous_state,
        candidate_state=candidate_state,
        candidate_count=candidate_count,
    )
    return evaluate_rules(rules, ctx)


def build_decision(
    *,
    evidence: Evidence,
    posterior: Posterior,
    result: RuleResult,
    selection: Selection,
    previous_state: str,
    previous_level: int,
    level: int,
    constraints: list[str],
    suggest_teacher: bool,
) -> ScaffoldDecision:
    fading = fading_action(previous_level, level, result.fading) if level > 0 or result.fading != "KEEP" else "KEEP"
    if level == 0 and previous_level > 0 and result.fading == "REDUCE":
        fading = "REDUCE"
    top_state_prob = posterior.get(result.state) if result.state in posterior.probabilities else posterior.need_support
    reason_parts = [result.explanation, selection.reason]
    if constraints:
        reason_parts.append("Restricciones: " + "; ".join(constraints) + ".")
    return ScaffoldDecision(
        need_detected=result.state if level > 0 or result.rule_code else "NONE",
        evidence=[
            *evidence.as_strings(),
            f"P({posterior.most_likely})={posterior.get(posterior.most_likely):.2f}",
            f"need_support={posterior.need_support:.2f}",
        ],
        candidate_supports=selection.candidates,
        selected_support=selection.selected.code if selection.selected else None,
        explicitness_level=level,
        confidence=round(max(0.0, min(1.0, top_state_prob)), 3),
        reason=" ".join(p for p in reason_parts if p),
        validation_status="NOT_REQUIRED",
        rule_code=result.rule_code,
        rule_name=result.rule_name,
        matched_rules=result.matched_codes,
        previous_state=previous_state,
        inferred_state=result.state,
        posterior=posterior.as_dict(),
        previous_help_level=previous_level,
        fading_action=fading,
        constraints=constraints,
        suggest_teacher=suggest_teacher,
    )


class AdaptivePolicy:
    """Política de Fase 4: OBSERVAR → INTERPRETAR → DECIDIR → ADAPTAR → RECORDAR."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def decide(self, db: AsyncSession, ctx: TutorContext) -> TutorOutcome:
        settings = self.settings
        events = await load_event_records(db, ctx.session.id, ctx.task.id)
        memory = await load_scaffold_memory(db, ctx.session.id, ctx.task.id)
        state_row = await get_or_create_state(db, ctx.student.id)
        expected_time = int(ctx.task.statement.get("expected_time_ms") or 90000)

        evidence = extract_evidence(
            events,
            task_id=str(ctx.task.id),
            scaffolds=memory,
            window_size=settings.tutor_window_size,
            expected_time_ms=expected_time,
            teacher_pause_events=settings.tutor_teacher_pause_events,
            difficulty=ctx.task.difficulty,
            help_requested_now=ctx.help_requested,
        )
        bayes = await load_bayes_config(db)
        posterior = infer(bayes, evidence.discretized())
        rules = await load_rules(db)
        previous_state = state_row.current_state
        result = run_engine(
            evidence=evidence,
            posterior=posterior,
            rules=rules,
            previous_state=previous_state,
            candidate_state=state_row.candidate_state,
            candidate_count=state_row.candidate_count,
        )

        # Restricciones explícitas (nunca sustituyen a las reglas: las acotan).
        constraints: list[str] = []
        suggest_teacher = False
        level = result.level
        if evidence.teacher_intervened_recently and not ctx.help_requested and level > 0:
            constraints.append("pausa tras intervención docente")
            level = 0
        if (
            level > 0
            and evidence.interventions_in_task >= settings.tutor_max_interventions_per_task
            and not ctx.help_requested
        ):
            constraints.append(
                f"tope de {settings.tutor_max_interventions_per_task} intervenciones automáticas por tarea alcanzado"
            )
            suggest_teacher = True
            level = 0
        if evidence.interventions_in_task >= settings.tutor_max_interventions_per_task:
            suggest_teacher = True

        bank = await load_bank(db)
        selection = select_scaffold(
            bank,
            task_type=ctx.task.task_type,
            skill=ctx.task.skill,
            level=level,
            intervention=result.intervention,
            memory=memory,
        )
        if level > 0 and selection.selected is None:
            suggest_teacher = True
            level = 0

        previous_level = state_row.current_help_level
        decision = build_decision(
            evidence=evidence,
            posterior=posterior,
            result=result,
            selection=selection,
            previous_state=previous_state,
            previous_level=previous_level,
            level=level,
            constraints=constraints,
            suggest_teacher=suggest_teacher,
        )

        # --- RECORDAR -------------------------------------------------------------
        db.add(
            InteractionEvidence(
                interaction_id=ctx.trigger_interaction.id,
                student_id=ctx.student.id,
                session_id=ctx.session.id,
                task_id=ctx.task.id,
                window_size=evidence.window_size,
                evidence=evidence.as_dict(),
            )
        )
        new_state = result.state if result.confirmed else previous_state
        db.add(
            StudentStateHistory(
                student_id=ctx.student.id,
                session_id=ctx.session.id,
                task_id=ctx.task.id,
                interaction_id=ctx.trigger_interaction.id,
                previous_state=previous_state,
                evidence_snapshot=evidence.as_dict(),
                posterior=posterior.as_dict(),
                inferred_state=result.state,
                rule_fired=result.rule_code,
                current_state=new_state,
                help_level=level,
                fading_action=decision.fading_action,
            )
        )
        state_row.previous_state = previous_state
        state_row.current_state = new_state
        state_row.candidate_state = result.candidate_state
        state_row.candidate_count = result.candidate_count
        state_row.session_id = ctx.session.id
        state_row.task_id = ctx.task.id
        state_row.current_skill = ctx.task.skill
        state_row.current_difficulty = ctx.task.difficulty
        state_row.recent_accuracy = evidence.recent_accuracy
        state_row.average_response_time_ms = evidence.response_time_ms
        state_row.click_pattern = evidence.click_pattern
        state_row.attempt_count = evidence.attempt_count
        state_row.repetition_count = evidence.repetition_count
        state_row.error_pattern = evidence.last_error_pattern
        state_row.confidence = decision.confidence
        state_row.posterior = posterior.as_dict()
        state_row.intervention_result = evidence.prior_help_result

        offer: HelpOffer | None = None
        scaffold_event: ScaffoldEvent | None = None
        if level > 0 and selection.selected is not None:
            scaffold = await db.scalar(select(Scaffold).where(Scaffold.code == selection.selected.code))
            scaffold_event, offer = await deliver_scaffold(
                db,
                ctx,
                scaffold,
                level=level,
                previous_level=previous_level,
                decision=decision.as_dict(),
                reason=decision.reason,
                source="SYSTEM",
            )
            state_row.current_help_level = level
            state_row.last_intervention_id = scaffold_event.id
        elif decision.fading_action == "REDUCE" and previous_level > 0:
            # Fading registrado como evento observable (sin HELP_OFFERED): menos ayuda ≠ aprendizaje.
            new_level = max(0, previous_level - 1)
            fading_event = ScaffoldEvent(
                session_id=ctx.session.id,
                student_id=ctx.student.id,
                task_id=ctx.task.id,
                interaction_id=ctx.trigger_interaction.id,
                scaffold_id=None,
                decision=decision.as_dict(),
                previous_help_level=previous_level,
                current_help_level=new_level,
                reason_for_change=decision.reason,
                source="SYSTEM",
                result="UNKNOWN",
            )
            db.add(fading_event)
            state_row.current_help_level = new_level
        elif ctx.help_requested:
            offer = HelpOffer(
                scaffold_event_id=None,
                offered=False,
                level=0,
                scaffold_type=None,
                text=None,
                message=(
                    "Por ahora el tutor no tiene otra pista para esta tarea. Tu docente puede acompañarte."
                    if suggest_teacher
                    else "Intenta un poco más por tu cuenta; si sigues trabado, vuelve a pedir ayuda."
                ),
            )
        await db.flush()
        return TutorOutcome(scaffold_event=scaffold_event, offer=offer, state=StudentState(new_state))
