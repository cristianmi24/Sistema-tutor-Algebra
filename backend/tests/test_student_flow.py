"""Fase 3: sesiones, eventos append-only, respuestas sin corrección inmediata, ayuda y alcance por rol."""

from __future__ import annotations

import uuid

import httpx
import pytest
from app.modules.learning.models import Interaction, Task
from app.seed.catalog import seed_catalog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import LoginFn, SeededWorld


@pytest.fixture
async def catalog(db: AsyncSession, world: SeededWorld) -> dict[str, str]:
    await seed_catalog(db)
    await db.commit()
    rows = (await db.execute(select(Task))).scalars()
    return {t.code: str(t.id) for t in rows}


async def start_session(client: httpx.AsyncClient, headers: dict[str, str], codes: list[str] | None = None) -> dict:
    response = await client.post("/api/v1/sessions", json={"task_codes": codes} if codes else {}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


async def test_student_sees_tasks_without_solution(
    client: httpx.AsyncClient, world: SeededWorld, login: LoginFn, catalog: dict[str, str]
) -> None:
    headers = await login(world.student_username)
    tasks = await client.get("/api/v1/tasks", headers=headers)
    assert tasks.status_code == 200
    assert len(tasks.json()) == 7
    assert {t["task_type"] for t in tasks.json()} == {
        "NUMERIC_PATTERN",
        "FIGURAL_PATTERN",
        "TABLE",
        "GRAPH",
        "SYMBOLIC",
        "JUSTIFICATION",
        "TRANSFER",
    }
    for task in tasks.json():
        assert "solution" not in task
        assert "3*n+2" not in str(task["statement"].get("questions"))
    examples = await client.get(f"/api/v1/tasks/{catalog['B-FIG-01']}/worked-examples", headers=headers)
    assert {e["example_type"] for e in examples.json()} == {
        "FULL",
        "PARTIAL",
        "HIDDEN_STEPS",
        "SELF_EXPLANATION",
        "STRATEGY_COMPARISON",
        "INTENTIONAL_ERROR",
    }


async def test_session_lifecycle_and_append_only_trace(
    client: httpx.AsyncClient, world: SeededWorld, login: LoginFn, catalog: dict[str, str], db: AsyncSession
) -> None:
    headers = await login(world.student_username)
    session = await start_session(client, headers)
    assert session["status"] == "ACTIVE"
    assert session["participant_code"] == world.student_participant_code
    assert [t["task"]["code"] for t in session["tasks"]][:2] == ["A-NUM-01", "B-FIG-01"]

    duplicate = await client.post("/api/v1/sessions", json={}, headers=headers)
    assert duplicate.status_code == 409

    sid = session["id"]
    task_id = catalog["A-NUM-01"]
    opened = await client.post(
        f"/api/v1/sessions/{sid}/events", json={"event_type": "TASK_OPENED", "task_id": task_id}, headers=headers
    )
    assert opened.status_code == 201
    forbidden_event = await client.post(
        f"/api/v1/sessions/{sid}/events", json={"event_type": "HELP_OFFERED", "task_id": task_id}, headers=headers
    )
    assert forbidden_event.status_code == 422  # eventos del servidor no se aceptan del cliente

    first = await client.post(
        f"/api/v1/sessions/{sid}/responses",
        json={
            "task_id": task_id,
            "question_id": "q1",
            "representation": "NUMERIC",
            "content": {"value": 17},
            "client_meta": {"time_on_task_ms": 42000, "clicks": 5},
        },
        headers=headers,
    )
    assert first.status_code == 201, first.text
    body = first.json()
    assert body["response"]["attempt_number"] == 1
    # Sin corrección inmediata: el estudiante no recibe 'correct' ni el patrón de error.
    assert body["response"]["evaluation"] is None
    assert body["help"] is None
    assert body["state_label"] == "En marcha"

    wrong = await client.post(
        f"/api/v1/sessions/{sid}/responses",
        json={"task_id": task_id, "question_id": "q3", "representation": "NUMERIC", "content": {"value": 35}},
        headers=headers,
    )
    assert wrong.status_code == 201
    assert wrong.json()["response"]["evaluation"] is None

    explain = await client.post(
        f"/api/v1/sessions/{sid}/responses",
        json={
            "task_id": task_id,
            "question_id": "q2",
            "representation": "VERBAL",
            "content": {"text": "Cada vez se suma 3 al anterior"},
        },
        headers=headers,
    )
    assert explain.json()["response"]["evaluation"] == {"observed_dimensions": ["RECURSIVE_LANGUAGE"]}

    edit = await client.post(
        f"/api/v1/sessions/{sid}/responses",
        json={
            "task_id": task_id,
            "question_id": "q3",
            "representation": "NUMERIC",
            "content": {"value": 32},
            "is_edit_of": wrong.json()["response"]["id"],
        },
        headers=headers,
    )
    assert edit.status_code == 201

    self_expl = await client.post(
        f"/api/v1/sessions/{sid}/events",
        json={"event_type": "SELF_EXPLANATION", "task_id": task_id, "payload": {"text": "Multipliqué por 3 y sumé 2"}},
        headers=headers,
    )
    assert self_expl.status_code == 201
    completed = await client.post(
        f"/api/v1/sessions/{sid}/events", json={"event_type": "TASK_COMPLETED", "task_id": task_id}, headers=headers
    )
    assert completed.status_code == 201

    trace = await client.get(f"/api/v1/sessions/{sid}/interactions", headers=headers)
    events = [e["event_type"] for e in trace.json()]
    assert events == [
        "SESSION_STARTED",
        "TASK_OPENED",
        "STUDENT_RESPONSE",
        "STUDENT_RESPONSE",
        "ERROR_DETECTED",
        "STUDENT_RESPONSE",
        "STUDENT_EDITED_RESPONSE",
        "SELF_EXPLANATION",
        "TASK_COMPLETED",
    ]
    sequences = [e["sequence"] for e in trace.json()]
    assert sequences == list(range(1, len(events) + 1))
    assert trace.json()[1]["next_student_action"] == "STUDENT_RESPONSE"
    assert trace.json()[2]["client_meta"] == {"time_on_task_ms": 42000, "clicks": 5}

    # El personal sí ve la evaluación (docente con alcance sobre 8-A).
    teacher = await login(world.teacher_email)
    staff_view = await client.get(f"/api/v1/sessions/{sid}/responses", headers=teacher)
    assert staff_view.status_code == 200
    evaluations = {r["question_id"] + str(r["attempt_number"]): r["evaluation"] for r in staff_view.json()}
    assert evaluations["q11"]["correct"] is True
    assert evaluations["q31"]["error_pattern"] == "OFF_BY_STEP"
    assert evaluations["q32"]["correct"] is True

    ended = await client.patch(f"/api/v1/sessions/{sid}/end", json={"status": "COMPLETED"}, headers=headers)
    assert ended.status_code == 200 and ended.json()["status"] == "COMPLETED"
    assert ended.json()["tasks"][0]["status"] == "COMPLETED"
    after = await client.post(
        f"/api/v1/sessions/{sid}/events", json={"event_type": "TASK_OPENED", "task_id": task_id}, headers=headers
    )
    assert after.status_code == 409

    stored = (
        (
            await db.execute(
                select(Interaction).where(Interaction.session_id == uuid.UUID(sid)).order_by(Interaction.sequence)
            )
        )
        .scalars()
        .all()
    )
    assert stored[-1].event_type == "SESSION_ENDED"


async def test_help_request_accept_reject_and_reformulate(
    client: httpx.AsyncClient, world: SeededWorld, login: LoginFn, catalog: dict[str, str]
) -> None:
    headers = await login(world.student_username)
    session = await start_session(client, headers, ["B-FIG-01"])
    sid, task_id = session["id"], catalog["B-FIG-01"]

    offer = await client.post(
        f"/api/v1/sessions/{sid}/help", json={"task_id": task_id, "question_id": "q2"}, headers=headers
    )
    assert offer.status_code == 200, offer.text
    body = offer.json()
    # El motor adaptativo atiende la solicitud explícita con la menor orientación útil (nivel 1–2).
    assert body["offered"] is True and body["level"] in (1, 2)
    assert body["text"] and "3n" not in body["text"] and "3*n" not in body["text"] and "14" not in body["text"]
    event_id = body["scaffold_event_id"]

    reformulated = await client.post(
        f"/api/v1/sessions/{sid}/scaffold-events/{event_id}/feedback", json={"action": "REFORMULATE"}, headers=headers
    )
    assert reformulated.status_code == 200
    assert reformulated.json()["text"] != body["text"]

    rejected = await client.post(
        f"/api/v1/sessions/{sid}/scaffold-events/{event_id}/feedback", json={"action": "REJECTED"}, headers=headers
    )
    assert rejected.status_code == 200 and rejected.json()["result"] == "REJECTED"

    # Caso 8: la siguiente ayuda nunca es la misma que fue rechazada.
    second = await client.post(f"/api/v1/sessions/{sid}/help", json={"task_id": task_id}, headers=headers)
    assert second.json()["scaffold_event_id"] != event_id
    assert second.json()["text"] != body["text"]
    accepted = await client.post(
        f"/api/v1/sessions/{sid}/scaffold-events/{second.json()['scaffold_event_id']}/feedback",
        json={"action": "ACCEPTED"},
        headers=headers,
    )
    assert accepted.json()["accepted"] is True

    # Memoria de intervención: la siguiente respuesta resuelve la ayuda pendiente.
    answer = await client.post(
        f"/api/v1/sessions/{sid}/responses",
        json={"task_id": task_id, "question_id": "q2", "representation": "NUMERIC", "content": {"value": 14}},
        headers=headers,
    )
    assert answer.status_code == 201
    trace = await client.get(f"/api/v1/sessions/{sid}/interactions", headers=headers)
    events = [e["event_type"] for e in trace.json()]
    assert events == [
        "SESSION_STARTED",
        "HELP_REQUESTED",
        "HELP_OFFERED",
        "HELP_REFORMULATED",
        "HELP_REJECTED",
        "HELP_REQUESTED",
        "HELP_OFFERED",
        "HELP_ACCEPTED",
        "STUDENT_RESPONSE",
    ]
    student_forbidden = await client.get(f"/api/v1/sessions/{sid}/scaffold-events", headers=headers)
    assert student_forbidden.status_code == 403
    researcher = await login(world.researcher_email)
    decisions = await client.get(f"/api/v1/sessions/{sid}/scaffold-events", headers=researcher)
    assert decisions.status_code == 200
    results = {d["scaffold_code"]: d["result"] for d in decisions.json()}
    assert "REJECTED" in results.values() and "IMPROVED" in results.values()
    assert all(d["decision"]["reason"] for d in decisions.json())


async def test_scope_is_enforced_for_sessions(
    client: httpx.AsyncClient, world: SeededWorld, login: LoginFn, catalog: dict[str, str], db: AsyncSession
) -> None:
    from app.modules.identity.models import Institution
    from app.seed.demo import create_student, create_teacher

    institution = await db.get(Institution, uuid.UUID(world.institution_id))
    assert institution is not None
    await create_student(
        db, username="stu2", password=world.password, institution=institution, grade="7", group_code="B"
    )
    await create_student(
        db,
        username="stu3",
        password=world.password,
        institution=institution,
        grade="8",
        group_code="A",
        research_status="PENDING",
    )
    await create_teacher(
        db, email="other.teacher@test.edu", password=world.password, institution=institution, groups=[("9", "C")]
    )
    await db.commit()

    s1 = await start_session(client, await login(world.student_username))
    s2 = await start_session(client, await login("stu2"))
    s3 = await start_session(client, await login("stu3"))

    # Estudiante: solo sus sesiones (404 para no revelar existencia).
    other = await client.get(f"/api/v1/sessions/{s2['id']}", headers=await login(world.student_username))
    assert other.status_code == 404
    mine = await client.get("/api/v1/sessions", headers=await login(world.student_username))
    assert [s["id"] for s in mine.json()] == [s1["id"]]

    # Docente 8-A: ve stu1 y stu3 (mismo grupo), no stu2 (7-B).
    teacher = await login(world.teacher_email)
    visible = {s["participant_code"] for s in (await client.get("/api/v1/sessions", headers=teacher)).json()}
    assert visible == {"STU-001", "STU-003"}
    assert (await client.get(f"/api/v1/sessions/{s2['id']}", headers=teacher)).status_code == 404
    other_teacher = await login("other.teacher@test.edu")
    assert (await client.get("/api/v1/sessions", headers=other_teacher)).json() == []

    # Investigador: solo estudiantes ELIGIBLE (stu3 está PENDING de acudiente).
    researcher = await login(world.researcher_email)
    research_visible = {
        s["participant_code"] for s in (await client.get("/api/v1/sessions", headers=researcher)).json()
    }
    assert research_visible == {"STU-001", "STU-002"}
    assert (await client.get(f"/api/v1/sessions/{s3['id']}", headers=researcher)).status_code == 404

    # Solo estudiantes envían respuestas.
    denied = await client.post(
        f"/api/v1/sessions/{s1['id']}/responses",
        json={
            "task_id": catalog["A-NUM-01"],
            "question_id": "q1",
            "representation": "NUMERIC",
            "content": {"value": 17},
        },
        headers=teacher,
    )
    assert denied.status_code == 403
