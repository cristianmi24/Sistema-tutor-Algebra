"""Fase 4 (integración): el tutor observa, interpreta, decide, adapta y recuerda a través de la API."""

from __future__ import annotations

import httpx
import pytest
from app.seed.catalog import seed_catalog
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import LoginFn, SeededWorld


@pytest.fixture
async def catalog(db: AsyncSession, world: SeededWorld) -> dict[str, str]:
    from app.modules.learning.models import Task
    from sqlalchemy import select

    await seed_catalog(db)
    await db.commit()
    return {t.code: str(t.id) for t in (await db.execute(select(Task))).scalars()}


async def answer(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    sid: str,
    task_id: str,
    question: str,
    value: object,
    ms: int = 200000,
) -> dict:
    response = await client.post(
        f"/api/v1/sessions/{sid}/responses",
        json={
            "task_id": task_id,
            "question_id": question,
            "representation": "NUMERIC",
            "content": {"value": value},
            "client_meta": {"time_on_task_ms": ms, "clicks": 6},
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_adaptive_cycle_observes_then_offers_minimal_help_and_records_everything(
    client: httpx.AsyncClient, world: SeededWorld, login: LoginFn, catalog: dict[str, str]
) -> None:
    student = await login(world.student_username)
    session = (await client.post("/api/v1/sessions", json={"task_codes": ["B-FIG-01"]}, headers=student)).json()
    sid, task_id = session["id"], catalog["B-FIG-01"]

    # Respuesta correcta: nivel 0, etiqueta neutral.
    ok = await answer(client, student, sid, task_id, "q2", 14)
    assert ok["help"] is None and ok["state_label"] in {"En marcha", "Explorando", "Con autonomía"}

    # Un error aislado: se observa (caso 2).
    first_error = await answer(client, student, sid, task_id, "q3", 40)
    assert first_error["help"] is None

    # Segundo error distinto: la regla de microayuda exige confirmación → todavía observa.
    second_error = await answer(client, student, sid, task_id, "q3", 30)
    assert second_error["help"] is None

    # Tercer error: confirmado → microayuda de nivel 1 (caso 3), sin revelar la solución.
    third = await answer(client, student, sid, task_id, "q3", 41)
    assert third["help"] is not None and third["help"]["offered"] is True
    assert third["help"]["level"] == 1
    assert "38" not in (third["help"]["text"] or "") and "3n" not in (third["help"]["text"] or "")
    assert third["state_label"] == "Pensando"  # etiqueta neutral de DIFFICULTY

    # El estudiante acepta y luego mejora: la ayuda queda IMPROVED y el apoyo se retira (caso 6).
    event_id = third["help"]["scaffold_event_id"]
    accepted = await client.post(
        f"/api/v1/sessions/{sid}/scaffold-events/{event_id}/feedback", json={"action": "ACCEPTED"}, headers=student
    )
    assert accepted.status_code == 200
    improved = await answer(client, student, sid, task_id, "q3", 38)
    assert improved["help"] is None
    assert improved["state_label"] in {"Avanzando", "En marcha", "Con autonomía"}

    researcher = await login(world.researcher_email)
    events = (await client.get(f"/api/v1/sessions/{sid}/scaffold-events", headers=researcher)).json()
    assert events[0]["result"] == "IMPROVED"
    decision = events[0]["decision"]
    for key in (
        "need_detected",
        "evidence",
        "candidate_supports",
        "selected_support",
        "explicitness_level",
        "confidence",
        "reason",
        "validation_status",
        "rule_code",
        "posterior",
        "fading_action",
    ):
        assert key in decision
    assert decision["rule_code"] == "R-DIFFICULTY-MICRO"
    assert any(e.startswith("error_pattern=") for e in decision["evidence"])
    # Fading registrado como evento observable (sin ayuda nueva).
    fading = [e for e in events if e["scaffold_id"] is None]
    assert fading and fading[0]["previous_help_level"] == 1 and fading[0]["current_help_level"] == 0
    assert fading[0]["decision"]["fading_action"] == "REDUCE"

    state = (await client.get(f"/api/v1/student-state/{world.student_id}", headers=researcher)).json()
    assert state["participant_code"] == world.student_participant_code
    assert state["current_state"] in {"RECOVERY", "NORMAL", "AUTONOMY"}
    assert state["current_help_level"] == 0
    assert "probabilities" in state["posterior"]

    history = (await client.get(f"/api/v1/student-state/{world.student_id}/history", headers=researcher)).json()
    assert len(history) == 5
    assert [h["current_state"] for h in history][3] == "DIFFICULTY"
    assert all("evidence_snapshot" in h and "posterior" in h for h in history)

    evidence = (await client.get("/api/v1/evidence", params={"session_id": sid}, headers=researcher)).json()
    assert len(evidence) == 5 and evidence[-1]["evidence"]["prior_help_result"] == "IMPROVED"

    # El estudiante no accede al perfil dinámico ni a las decisiones (etiquetas operativas).
    assert (await client.get(f"/api/v1/student-state/{world.student_id}", headers=student)).status_code == 403


async def test_stagnation_changes_representation_and_teacher_pause_is_respected(
    client: httpx.AsyncClient, world: SeededWorld, login: LoginFn, catalog: dict[str, str], db: AsyncSession
) -> None:
    student = await login(world.student_username)
    session = (await client.post("/api/v1/sessions", json={"task_codes": ["B-FIG-01"]}, headers=student)).json()
    sid, task_id = session["id"], catalog["B-FIG-01"]

    offered_levels: list[int] = []
    for _ in range(6):
        result = await answer(client, student, sid, task_id, "q3", 41, ms=250000)  # mismo error OFF_BY_STEP
        if result["help"] and result["help"]["offered"]:
            offered_levels.append(result["help"]["level"])
    assert offered_levels, "el tutor debió intervenir ante el estancamiento"
    assert max(offered_levels) >= 4, offered_levels  # llegó al cambio de representación (caso 5)
    assert offered_levels == sorted(offered_levels)  # la ayuda solo aumenta con evidencia nueva

    researcher = await login(world.researcher_email)
    state = (await client.get(f"/api/v1/student-state/{world.student_id}", headers=researcher)).json()
    assert state["current_state"] in {"STAGNATION", "DIFFICULTY"}
    events = (await client.get(f"/api/v1/sessions/{sid}/scaffold-events", headers=researcher)).json()
    codes = [e["scaffold_code"] for e in events if e["scaffold_code"]]
    assert len(codes) == len(set(codes))  # nunca se repite la misma ayuda en la tarea
    assert any(e["scaffold_type"] == "REPRESENTATION_CHANGE" for e in events)

    # Intervención docente (evento registrado por separado) ⇒ el sistema pausa (caso 9).
    from app.modules.common.enums import InteractionEventType
    from app.modules.learning.service import load_session, record_event

    loaded = await load_session(db, session["id"])
    await record_event(
        db,
        loaded,
        InteractionEventType.TEACHER_INTERVENTION,
        task_id=loaded.tasks[0].task_id,
        student_action="TEACHER_QUESTION",
    )
    await db.commit()
    paused = await answer(client, student, sid, task_id, "q3", 41, ms=250000)
    assert paused["help"] is None
    history = (await client.get(f"/api/v1/student-state/{world.student_id}/history", headers=researcher)).json()
    assert history[-1]["rule_fired"] == "R-TEACHER-PAUSE" and history[-1]["help_level"] == 0


async def test_simulation_endpoint_and_rule_administration(
    client: httpx.AsyncClient, world: SeededWorld, login: LoginFn, catalog: dict[str, str]
) -> None:
    researcher = await login(world.researcher_email)
    simulated = await client.post(
        "/api/v1/scaffolding/decision",
        json={
            "evidence": {
                "accuracy_band": "LOW",
                "error_pattern": "PERSISTENT",
                "attempt_count": 5,
                "responses_in_window": 4,
                "repetition_count": 2,
                "recent_errors_trend": "STABLE",
                "interventions_in_task": 2,
                "prior_help_result": "PERSISTED",
            },
            "previous_state": "DIFFICULTY",
            "memory": [
                {"code": "FOC-CHANGE-01", "scaffold_type": "FOCUSING", "level": 1, "result": "PERSISTED"},
                {"code": "GUIDE-RELATE-01", "scaffold_type": "GUIDING_QUESTION", "level": 2, "result": "PERSISTED"},
            ],
        },
        headers=researcher,
    )
    assert simulated.status_code == 200, simulated.text
    body = simulated.json()
    assert body["rule_result"]["rule_code"] == "R-STAGNATION-REPR"
    assert body["decision"]["selected_support"] == "REPR-TABLE-01"
    assert body["posterior"]["most_likely"] == "STAGNATION"

    rules = await client.get("/api/v1/tutor-rules", headers=researcher)
    assert rules.status_code == 200 and len(rules.json()) == 12
    denied = await client.post(
        "/api/v1/tutor-rules", json={"code": "R-X", "name": "x", "conditions": {}, "actions": {}}, headers=researcher
    )
    assert denied.status_code == 403

    admin = await login(world.admin_email)
    created = await client.post(
        "/api/v1/tutor-rules",
        json={
            "code": "R-TEST-ZERO",
            "name": "prueba",
            "priority": 1,
            "conditions": {"all": [{"evidence": "attempt_count", "gte": 99}]},
            "actions": {"state": "NORMAL", "level": 0},
        },
        headers=admin,
    )
    assert created.status_code == 201
    bayes = await client.get("/api/v1/bayesian-config", headers=researcher)
    assert bayes.json()[0]["name"] == "default" and "accuracy_band" in bayes.json()[0]["likelihoods"]
    audit = await client.get("/api/v1/admin/audit", params={"action": "RULE_UPDATED"}, headers=admin)
    assert audit.json()["total"] == 1
