"""Fase 6 (caso 9): intervención docente registrada por separado, visible al estudiante, pausa del tutor."""

from __future__ import annotations

import httpx
import pytest
from app.modules.learning.models import Task
from app.seed.catalog import seed_catalog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import LoginFn, SeededWorld


@pytest.fixture
async def catalog(db: AsyncSession, world: SeededWorld) -> dict[str, str]:
    await seed_catalog(db)
    await db.commit()
    return {t.code: str(t.id) for t in (await db.execute(select(Task))).scalars()}


async def test_teacher_intervention_is_separate_visible_and_pauses_tutor(
    client: httpx.AsyncClient, world: SeededWorld, login: LoginFn, catalog: dict[str, str]
) -> None:
    student = await login(world.student_username)
    task_id = catalog["B-FIG-01"]
    session = (await client.post("/api/v1/sessions", json={"task_codes": ["B-FIG-01"]}, headers=student)).json()
    sid = session["id"]
    for value in (41, 30):
        await client.post(
            f"/api/v1/sessions/{sid}/responses",
            json={
                "task_id": task_id,
                "question_id": "q3",
                "representation": "NUMERIC",
                "content": {"value": value},
                "client_meta": {"time_on_task_ms": 200000},
            },
            headers=student,
        )

    teacher = await login(world.teacher_email)
    groups = (await client.get("/api/v1/teacher/groups", headers=teacher)).json()
    assert groups[0]["grade"] == "8" and groups[0]["group_code"] == "A"
    overview = groups[0]["students"][0]
    assert overview["participant_code"] == world.student_participant_code
    assert overview["active_session_id"] == sid and overview["current_task_code"] == "B-FIG-01"
    assert overview["operational_state"] is not None and overview["state_label"] is not None
    assert "username" not in overview and "email" not in overview

    created = await client.post(
        "/api/v1/teacher/interventions",
        json={
            "session_id": sid,
            "task_id": task_id,
            "intervention_type": "QUESTION",
            "content": "¿Qué pasa con las sillas de los extremos?",
        },
        headers=teacher,
    )
    assert created.status_code == 201, created.text
    intervention = created.json()
    assert intervention["source"] == "TEACHER" and intervention["interaction_id"]
    note = await client.post(
        "/api/v1/teacher/interventions",
        json={
            "session_id": sid,
            "intervention_type": "OBSERVATION",
            "content": "Cuenta mesa por mesa.",
            "visibility": "RESEARCH_ONLY",
        },
        headers=teacher,
    )
    assert note.status_code == 201 and note.json()["interaction_id"] is None

    # El estudiante ve solo el mensaje dirigido a él, marcado como del docente.
    messages = (await client.get(f"/api/v1/sessions/{sid}/teacher-messages", headers=student)).json()
    assert [m["content"] for m in messages] == ["¿Qué pasa con las sillas de los extremos?"]
    assert (
        await client.post(f"/api/v1/sessions/{sid}/teacher-messages/{messages[0]['id']}/seen", headers=student)
    ).status_code == 204
    assert (await client.get(f"/api/v1/sessions/{sid}/teacher-messages", headers=student)).json()[0]["seen"] is True

    # Trazabilidad separada: evento TEACHER_INTERVENTION propio, no HELP_OFFERED.
    trace = (await client.get(f"/api/v1/sessions/{sid}/interactions", headers=teacher)).json()
    teacher_events = [e for e in trace if e["event_type"] == "TEACHER_INTERVENTION"]
    assert len(teacher_events) == 1 and teacher_events[0]["teacher_intervention_id"] == intervention["id"]
    assert teacher_events[0]["help_content"] is None and teacher_events[0]["scaffold_event_id"] is None

    # El tutor pausa: una respuesta incorrecta inmediata no produce ayuda del sistema.
    paused = await client.post(
        f"/api/v1/sessions/{sid}/responses",
        json={
            "task_id": task_id,
            "question_id": "q3",
            "representation": "NUMERIC",
            "content": {"value": 44},
            "client_meta": {"time_on_task_ms": 200000},
        },
        headers=student,
    )
    assert paused.json()["help"] is None

    # La línea de tiempo marca al docente como actor distinto del sistema.
    timeline = (await client.get(f"/api/v1/research/sessions/{sid}/timeline", headers=teacher)).json()
    step = next(s for s in timeline if s["event_type"] == "TEACHER_INTERVENTION")
    assert step["actor"] == "TEACHER" and step["teacher_intervention"]["type"] == "QUESTION"
    episodes = (await client.get("/api/v1/research/episodes", params={"session_id": sid}, headers=teacher)).json()
    assert episodes[0]["trigger"] == "TEACHER"

    listed = (await client.get("/api/v1/teacher/interventions", params={"session_id": sid}, headers=teacher)).json()
    assert {i["visibility"] for i in listed} == {"STUDENT", "RESEARCH_ONLY"}


async def test_teacher_scope_and_roles(
    client: httpx.AsyncClient, world: SeededWorld, login: LoginFn, catalog: dict[str, str], db: AsyncSession
) -> None:
    import uuid

    from app.modules.identity.models import Institution
    from app.seed.demo import create_student, create_teacher

    institution = await db.get(Institution, uuid.UUID(world.institution_id))
    assert institution is not None
    await create_student(
        db, username="other", password=world.password, institution=institution, grade="9", group_code="C"
    )
    await create_teacher(db, email="t9@test.edu", password=world.password, institution=institution, groups=[("9", "C")])
    await db.commit()
    other_session = (await client.post("/api/v1/sessions", json={}, headers=await login("other"))).json()

    teacher = await login(world.teacher_email)
    denied = await client.post(
        "/api/v1/teacher/interventions",
        json={"session_id": other_session["id"], "intervention_type": "COMMENT", "content": "Hola"},
        headers=teacher,
    )
    assert denied.status_code == 404  # fuera de su grupo: no se revela la existencia
    researcher = await login(world.researcher_email)
    assert (
        await client.post(
            "/api/v1/teacher/interventions",
            json={"session_id": other_session["id"], "intervention_type": "COMMENT", "content": "x"},
            headers=researcher,
        )
    ).status_code == 403
    assert (await client.get("/api/v1/teacher/groups", headers=researcher)).status_code == 403
    own = await client.post(
        "/api/v1/teacher/interventions",
        json={"session_id": other_session["id"], "intervention_type": "ENCOURAGEMENT", "content": "¡Vas bien!"},
        headers=await login("t9@test.edu"),
    )
    assert own.status_code == 201
    student = await login(world.student_username)
    assert (
        await client.get(f"/api/v1/sessions/{other_session['id']}/teacher-messages", headers=student)
    ).status_code == 404
