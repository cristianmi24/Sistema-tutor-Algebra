"""Exportación pseudonimizada (CSV, JSON, JSONL, Excel, PDF) respetando el alcance del rol.

Nunca incluye nombres, correos, usuarios ni identificadores de cuenta: solo ``participant_code`` y
UUID opacos de estudiante/sesión/tarea. Cada exportación queda auditada (EXPORT_GENERATED).
"""

from __future__ import annotations

import csv
import io
import json
import uuid
from datetime import datetime
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.core.errors import AppError
from app.modules.identity.models import Institution, Student
from app.modules.learning.models import Interaction, LearningSession, ScaffoldEvent, Task
from app.modules.learning.scope import accessible_student_ids
from app.modules.research.models import Episode, Interview, InterviewResponse, ResearchMemo
from app.modules.tutor.models import StudentStateHistory

Dataset = Literal[
    "participants", "sessions", "interactions", "episodes", "scaffold_events", "state_history", "memos", "interviews"
]
Format = Literal["csv", "json", "jsonl", "xlsx", "pdf"]

MAX_ROWS = 50_000
MEDIA_TYPES: dict[str, str] = {
    "csv": "text/csv; charset=utf-8",
    "json": "application/json",
    "jsonl": "application/x-ndjson",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
}


def _json_value(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _flat(value: Any) -> Any:
    value = _json_value(value)
    if isinstance(value, dict | list):
        return json.dumps(value, ensure_ascii=False, default=str)
    return value


async def _student_filter(
    db: AsyncSession, actor: CurrentUser, student_ids: list[uuid.UUID] | None
) -> list[uuid.UUID] | None:
    scope = await accessible_student_ids(db, actor)
    if student_ids is None:
        return scope
    if scope is None:
        return student_ids
    allowed = set(scope)
    return [s for s in student_ids if s in allowed]


async def _codes(db: AsyncSession) -> dict[uuid.UUID, str]:
    return {sid: code for sid, code in (await db.execute(select(Student.id, Student.participant_code))).all()}


async def _task_codes(db: AsyncSession) -> dict[uuid.UUID, str]:
    return {tid: code for tid, code in (await db.execute(select(Task.id, Task.code))).all()}


async def collect_rows(
    db: AsyncSession,
    actor: CurrentUser,
    dataset: Dataset,
    *,
    session_id: uuid.UUID | None = None,
    student_ids: list[uuid.UUID] | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> list[dict[str, Any]]:
    scope = await _student_filter(db, actor, student_ids)
    codes = await _codes(db)
    tasks = await _task_codes(db)

    def scoped(stmt: Any, column: Any) -> Any:
        return stmt.where(column.in_(scope)) if scope is not None else stmt

    rows: list[dict[str, Any]] = []
    if dataset == "participants":
        stmt = scoped(
            select(Student, Institution.code).join(Institution, Institution.id == Student.institution_id), Student.id
        )
        for student, inst in (await db.execute(stmt.order_by(Student.participant_code).limit(MAX_ROWS))).all():
            rows.append(
                {
                    "student_id": student.id,
                    "participant_code": student.participant_code,
                    "institution_code": inst,
                    "grade": student.grade,
                    "group_code": student.group_code,
                    "birth_year": student.birth_year,
                    "research_status": student.research_status,
                }
            )
    elif dataset == "sessions":
        stmt = scoped(select(LearningSession), LearningSession.student_id)
        if session_id:
            stmt = stmt.where(LearningSession.id == session_id)
        if since:
            stmt = stmt.where(LearningSession.started_at >= since)
        if until:
            stmt = stmt.where(LearningSession.started_at <= until)
        s: LearningSession
        for s in (await db.execute(stmt.order_by(LearningSession.started_at).limit(MAX_ROWS))).scalars():
            duration: float | None = (s.ended_at - s.started_at).total_seconds() if s.ended_at else None
            rows.append(
                {
                    "session_id": s.id,
                    "student_id": s.student_id,
                    "participant_code": codes.get(s.student_id),
                    "started_at": s.started_at,
                    "ended_at": s.ended_at,
                    "duration_seconds": duration,
                    "status": s.status,
                    "events": s.last_sequence,
                }
            )
    elif dataset == "interactions":
        stmt = scoped(select(Interaction), Interaction.student_id)
        if session_id:
            stmt = stmt.where(Interaction.session_id == session_id)
        if since:
            stmt = stmt.where(Interaction.timestamp >= since)
        if until:
            stmt = stmt.where(Interaction.timestamp <= until)
        i: Interaction
        for i in (
            await db.execute(stmt.order_by(Interaction.session_id, Interaction.sequence).limit(MAX_ROWS))
        ).scalars():
            # Esquema de evento C.19.
            rows.append(
                {
                    "session_id": i.session_id,
                    "student_id": i.student_id,
                    "participant_code": codes.get(i.student_id),
                    "task_id": i.task_id,
                    "task_code": tasks.get(i.task_id) if i.task_id else None,
                    "sequence": i.sequence,
                    "timestamp": i.timestamp,
                    "event_type": i.event_type,
                    "student_action": i.student_action,
                    "student_response": i.student_response,
                    "representation": i.representation,
                    "help_requested": i.help_requested,
                    "help_level": i.help_level,
                    "help_type": i.help_type,
                    "help_content": i.help_content,
                    "help_accepted": i.help_accepted,
                    "help_rejected": i.help_rejected,
                    "ai_interpretation": i.ai_interpretation,
                    "teacher_intervention": i.teacher_intervention_id,
                    "next_student_action": i.next_student_action,
                    "client_meta": i.client_meta,
                }
            )
    elif dataset == "episodes":
        stmt = scoped(select(Episode), Episode.student_id)
        if session_id:
            stmt = stmt.where(Episode.session_id == session_id)
        e: Episode
        for e in (await db.execute(stmt.order_by(Episode.created_at).limit(MAX_ROWS))).scalars():
            rows.append(
                {
                    "episode_id": e.id,
                    "participant_code": codes.get(e.student_id),
                    "session_id": e.session_id,
                    "task_code": tasks.get(e.task_id),
                    "trigger": e.trigger,
                    "status": e.status,
                    "close_reason": e.close_reason,
                    "created_at": e.created_at,
                    "closed_at": e.closed_at,
                    "summary_system_generated": e.summary,
                }
            )
    elif dataset == "scaffold_events":
        stmt = scoped(select(ScaffoldEvent), ScaffoldEvent.student_id)
        if session_id:
            stmt = stmt.where(ScaffoldEvent.session_id == session_id)
        se: ScaffoldEvent
        for se in (await db.execute(stmt.order_by(ScaffoldEvent.created_at).limit(MAX_ROWS))).scalars():
            rows.append(
                {
                    "scaffold_event_id": se.id,
                    "participant_code": codes.get(se.student_id),
                    "session_id": se.session_id,
                    "task_code": tasks.get(se.task_id),
                    "source": se.source,
                    "previous_help_level": se.previous_help_level,
                    "current_help_level": se.current_help_level,
                    "reason_for_change": se.reason_for_change,
                    "delivered_text": se.delivered_text,
                    "accepted": se.accepted,
                    "rejected": se.rejected,
                    "reformulations": se.reformulations,
                    "result": se.result,
                    "subsequent_strategy": se.subsequent_strategy,
                    "decision": se.decision,
                    "created_at": se.created_at,
                }
            )
    elif dataset == "state_history":
        stmt = scoped(select(StudentStateHistory), StudentStateHistory.student_id)
        if session_id:
            stmt = stmt.where(StudentStateHistory.session_id == session_id)
        h: StudentStateHistory
        for h in (await db.execute(stmt.order_by(StudentStateHistory.created_at).limit(MAX_ROWS))).scalars():
            rows.append(
                {
                    "participant_code": codes.get(h.student_id),
                    "session_id": h.session_id,
                    "task_code": tasks.get(h.task_id) if h.task_id else None,
                    "interaction_id": h.interaction_id,
                    "previous_state": h.previous_state,
                    "inferred_state": h.inferred_state,
                    "rule_fired": h.rule_fired,
                    "current_state": h.current_state,
                    "help_level": h.help_level,
                    "fading_action": h.fading_action,
                    "posterior": h.posterior,
                    "evidence": h.evidence_snapshot,
                    "created_at": h.created_at,
                    "label": "interpretación operativa del sistema",
                }
            )
    elif dataset == "memos":
        stmt = select(ResearchMemo)
        if actor.researcher_id is not None:
            stmt = stmt.where(ResearchMemo.researcher_id == actor.researcher_id)
        m: ResearchMemo
        for m in (await db.execute(stmt.order_by(ResearchMemo.created_at).limit(MAX_ROWS))).scalars():
            rows.append(
                {
                    "memo_id": m.id,
                    "title": m.title,
                    "episode_id": m.episode_id,
                    "participant_code": codes.get(m.student_id) if m.student_id else None,
                    "session_id": m.session_id,
                    "observation": m.observation,
                    "interpretation": m.interpretation,
                    "emerging_question": m.emerging_question,
                    "contradiction": m.contradiction,
                    "negative_case": m.negative_case,
                    "possible_category_researcher": m.possible_category,
                    "theoretical_sampling_need": m.theoretical_sampling_need,
                    "tags": m.tags,
                    "created_at": m.created_at,
                }
            )
    elif dataset == "interviews":
        stmt = select(Interview, InterviewResponse).join(
            InterviewResponse, InterviewResponse.interview_id == Interview.id
        )
        if actor.researcher_id is not None:
            stmt = stmt.where(Interview.researcher_id == actor.researcher_id)
        for iv, r in (
            await db.execute(stmt.order_by(Interview.conducted_at, InterviewResponse.order_index).limit(MAX_ROWS))
        ).all():
            rows.append(
                {
                    "interview_id": iv.id,
                    "title": iv.title,
                    "interviewee_kind": iv.interviewee_kind,
                    "participant_code": codes.get(iv.student_id) if iv.student_id else None,
                    "episode_id": iv.episode_id,
                    "conducted_at": iv.conducted_at,
                    "order": r.order_index,
                    "question": r.question,
                    "answer": r.answer,
                    "related_episode_id": r.related_episode_id,
                    "observations": r.observations,
                }
            )
    else:  # pragma: no cover - validado por Literal
        raise AppError("Conjunto de datos no soportado.")
    return rows


def render(rows: list[dict[str, Any]], fmt: Format, *, title: str) -> bytes:
    if fmt == "json":
        return json.dumps(
            [{k: _json_value(v) for k, v in r.items()} for r in rows], ensure_ascii=False, default=str, indent=2
        ).encode()
    if fmt == "jsonl":
        return "\n".join(
            json.dumps({k: _json_value(v) for k, v in r.items()}, ensure_ascii=False, default=str) for r in rows
        ).encode()
    headers = list(rows[0].keys()) if rows else ["sin_datos"]
    if fmt == "csv":
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow({k: _flat(v) for k, v in r.items()})
        return ("﻿" + buffer.getvalue()).encode("utf-8")  # BOM para Excel
    if fmt == "xlsx":
        from openpyxl import Workbook
        from openpyxl.styles import Font

        wb = Workbook()
        ws = wb.active
        assert ws is not None
        ws.title = title[:31]
        ws.append(headers)
        for cell in ws[1]:
            cell.font = Font(bold=True)
        for r in rows:
            ws.append([_excel_safe(_flat(r.get(h))) for h in headers])
        out = io.BytesIO()
        wb.save(out)
        return out.getvalue()
    if fmt == "pdf":
        return _render_pdf(rows, headers, title)
    raise AppError("Formato no soportado.")


def _excel_safe(value: Any) -> Any:
    # Evita inyección de fórmulas en hojas de cálculo.
    if isinstance(value, str) and value[:1] in {"=", "+", "-", "@"}:
        return "'" + value
    return value


def _latin1(text: str) -> str:
    return text.encode("latin-1", "replace").decode("latin-1")


def _render_pdf(rows: list[dict[str, Any]], headers: list[str], title: str) -> bytes:
    from fpdf import FPDF

    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, _latin1(f"STI-GA · Exportación: {title}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(
        0,
        5,
        _latin1(
            f"Registros: {len(rows)} · Datos pseudonimizados · Generado: {datetime.now().isoformat(timespec='minutes')}"
        ),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(2)
    for index, row in enumerate(rows, start=1):
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(0, 5, _latin1(f"#{index}"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 7)
        for key in headers:
            value = _flat(row.get(key))
            if value in (None, "", "{}", "[]"):
                continue
            text = str(value)
            if len(text) > 600:
                text = text[:600] + "…"
            pdf.multi_cell(0, 3.6, _latin1(f"{key}: {text}"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
    if not rows:
        pdf.cell(0, 6, "Sin datos para los filtros indicados.")
    return bytes(pdf.output())
