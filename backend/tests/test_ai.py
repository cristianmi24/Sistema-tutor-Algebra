"""Fase 7: IA opcional subordinada. Caso C.43 10: una salida inválida del LLM se bloquea."""

from __future__ import annotations

from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from app.core.config import Settings
from app.main import create_app
from app.modules.ai.providers import AnthropicProvider, FakeProvider, LLMRequest, set_provider_override
from app.modules.ai.validators import validate_hint, validate_interpretation
from app.modules.learning.models import Task
from app.modules.tutor.models import AIInteraction
from app.seed.catalog import seed_catalog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import TEST_PASSWORD, SeededWorld, _Lifespan

ORIGINAL = "Fíjate en cómo cambia la cantidad de la figura 2 a la figura 3. ¿Cuánto se agrega?"


# ------------------------------------------------------------------ validadores (unitarias)


def test_hint_validator_blocks_solution_values_and_new_numbers() -> None:
    kwargs = {"original": ORIGINAL, "scaffold_type": "FOCUSING", "rule": "3*n+2", "protected_positions": [4, 12]}
    ok, result = validate_hint({"text": "Compara la figura 2 con la figura 3: ¿qué aparece nuevo?"}, **kwargs)
    assert ok and result.approved
    for bad in (
        "La fórmula es 3n + 2, ¿ves?",
        "Piensa en 3·n+2. ¿Qué observas?",
        "Con 12 mesas son 38 personas, ¿cierto?",
        "Mira https://x.com ¿qué ves?",
    ):
        text, result = validate_hint({"text": bad}, **kwargs)
        assert text is None and not result.approved, bad
    _, result = validate_hint({"text": "Muy bien, lo hiciste correcto."}, **kwargs)
    assert not result.pedagogical["approved"]
    _, result = validate_hint({}, **kwargs)
    assert not result.approved


def test_interpretation_validator_enforces_closed_vocabulary() -> None:
    value, result = validate_interpretation(
        {"dimensions": ["RECURSIVE_LANGUAGE", "GENERAL_CLAIM"], "confidence": 0.8, "note": ""}
    )
    assert result.approved and value is not None and "no es una categoría teórica" in value["label"]
    value, result = validate_interpretation({"dimensions": ["COMPRENDE_BIEN"], "confidence": 0.9, "note": ""})
    assert value is None and "vocabulario cerrado" in result.reasons[0]
    _, result = validate_interpretation({"dimensions": [], "confidence": 3, "note": ""})
    assert not result.approved


# ------------------------------------------------------------------ proveedor Anthropic con cliente falso


class _FakeMessages:
    def __init__(self, response: Any) -> None:
        self.response = response
        self.kwargs: dict[str, Any] = {}

    async def create(self, **kwargs: Any) -> Any:
        self.kwargs = kwargs
        return self.response


def _anthropic_provider(response: Any) -> tuple[AnthropicProvider, _FakeMessages]:
    settings = Settings(_env_file=None, llm_enabled=True, llm_provider="anthropic", llm_api_key="test-key")  # type: ignore[call-arg]
    provider = AnthropicProvider(settings)
    messages = _FakeMessages(response)
    provider._client = SimpleNamespace(beta=SimpleNamespace(messages=messages))  # type: ignore[assignment]
    return provider, messages


async def test_anthropic_provider_requests_structured_output_and_handles_refusal() -> None:
    ok_response = SimpleNamespace(
        stop_reason="end_turn",
        content=[SimpleNamespace(type="text", text='{"text": "¿Qué cambia?"}')],
        model="claude-opus-5",
    )
    provider, messages = _anthropic_provider(ok_response)
    result = await provider.complete(
        LLMRequest(purpose="ADAPT_LANGUAGE", system="s", user="u", json_schema={"type": "object"})
    )
    assert result.ok and result.data == {"text": "¿Qué cambia?"}
    assert messages.kwargs["model"] == "claude-opus-5"
    assert messages.kwargs["output_config"]["format"]["type"] == "json_schema"
    assert messages.kwargs["fallbacks"] == "default" and messages.kwargs["betas"] == ["server-side-fallback-2026-07-01"]

    refused, _ = _anthropic_provider(SimpleNamespace(stop_reason="refusal", content=[], model="claude-opus-5"))
    assert (await refused.complete(LLMRequest(purpose="x", system="s", user="u", json_schema={}))).error == "refusal"


# ------------------------------------------------------------------ integración


@pytest.fixture
async def ai_client(
    settings: Settings, world: SeededWorld, db: AsyncSession
) -> AsyncIterator[tuple[httpx.AsyncClient, dict[str, str]]]:
    await seed_catalog(db)
    await db.commit()
    tasks = {t.code: str(t.id) for t in (await db.execute(select(Task))).scalars()}
    app = create_app(
        settings.model_copy(update={"llm_enabled": True, "llm_provider": "fake", "llm_max_calls_per_session": 5})
    )
    async with (
        _Lifespan(app),
        httpx.ASGITransport(app=app) as transport,  # type: ignore[arg-type]
        httpx.AsyncClient(transport=transport, base_url="http://testserver") as client,
    ):
        yield client, tasks
    set_provider_override(None)


async def _login(client: httpx.AsyncClient, identifier: str) -> dict[str, str]:
    token = (
        await client.post("/api/v1/auth/login", json={"identifier": identifier, "password": TEST_PASSWORD})
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _offer(client: httpx.AsyncClient, headers: dict[str, str], task_id: str) -> tuple[str, dict[str, Any]]:
    session = (await client.post("/api/v1/sessions", json={"task_codes": ["B-FIG-01"]}, headers=headers)).json()
    offer = (
        await client.post(f"/api/v1/sessions/{session['id']}/help", json={"task_id": task_id}, headers=headers)
    ).json()
    return session["id"], offer


async def test_case_10_invalid_llm_output_is_blocked_and_bank_is_used(
    ai_client: tuple[httpx.AsyncClient, dict[str, str]], world: SeededWorld, db: AsyncSession
) -> None:
    client, tasks = ai_client
    fake = FakeProvider(lambda req: {"text": "La fórmula es 3n + 2. Con 12 mesas son 38."})
    set_provider_override(fake)
    student = await _login(client, world.student_username)
    sid, offer = await _offer(client, student, tasks["B-FIG-01"])
    assert offer["can_reformulate"] is True
    reformulated = await client.post(
        f"/api/v1/sessions/{sid}/scaffold-events/{offer['scaffold_event_id']}/feedback",
        json={"action": "REFORMULATE"},
        headers=student,
    )
    assert reformulated.status_code == 200, reformulated.text
    text = reformulated.json()["text"]
    assert "3n" not in text and "38" not in text  # nunca se muestra la salida inválida
    row = (await db.execute(select(AIInteraction))).scalars().one()
    assert row.approved is False and row.purpose == "ADAPT_LANGUAGE"
    assert not row.validation["domain"]["approved"]
    assert any("expresión general" in r for r in row.validation["reasons"])
    assert "stu1" not in str(row.prompt) and "@" not in str(row.prompt)  # sin datos personales
    researcher = await _login(client, world.researcher_email)
    trace = (await client.get(f"/api/v1/sessions/{sid}/interactions", headers=researcher)).json()
    assert (
        trace[-1]["event_type"] == "HELP_REFORMULATED"
        and trace[-1]["ai_interpretation"]["reformulation_source"] == "BANK_VARIANT"
    )


async def test_valid_reformulation_is_delivered_and_traced(
    ai_client: tuple[httpx.AsyncClient, dict[str, str]], world: SeededWorld
) -> None:
    client, tasks = ai_client
    set_provider_override(
        FakeProvider(lambda req: {"text": "Compara dos figuras seguidas: ¿qué parte aparece nueva en la siguiente?"})
    )
    student = await _login(client, world.student_username)
    sid, offer = await _offer(client, student, tasks["B-FIG-01"])
    reformulated = (
        await client.post(
            f"/api/v1/sessions/{sid}/scaffold-events/{offer['scaffold_event_id']}/feedback",
            json={"action": "REFORMULATE"},
            headers=student,
        )
    ).json()
    assert reformulated["text"].startswith("Compara dos figuras seguidas")
    researcher = await _login(client, world.researcher_email)
    events = (await client.get(f"/api/v1/sessions/{sid}/scaffold-events", headers=researcher)).json()
    assert events[0]["source"] == "AI_VALIDATED" and events[0]["decision"]["validation_status"] == "APPROVED"
    ai_rows = (await client.get("/api/v1/ai/interactions", params={"session_id": sid}, headers=researcher)).json()
    assert ai_rows[0]["approved"] is True and ai_rows[0]["validation"]["safety"]["approved"] is True


async def test_interpretation_is_stored_for_staff_only_and_budget_is_enforced(
    ai_client: tuple[httpx.AsyncClient, dict[str, str]], world: SeededWorld, db: AsyncSession
) -> None:
    client, tasks = ai_client
    fake = FakeProvider(
        lambda req: {"dimensions": ["RECURSIVE_LANGUAGE"], "confidence": 0.7, "note": "habla de sumar cada vez"}
    )
    set_provider_override(fake)
    student = await _login(client, world.student_username)
    session = (await client.post("/api/v1/sessions", json={"task_codes": ["B-FIG-01"]}, headers=student)).json()
    sid, task_id = session["id"], tasks["B-FIG-01"]
    for _ in range(7):
        await client.post(
            f"/api/v1/sessions/{sid}/events",
            json={"event_type": "SELF_EXPLANATION", "task_id": task_id, "payload": {"text": "Cada vez se suma 3"}},
            headers=student,
        )
    assert len(fake.calls) == 5  # LLM_MAX_CALLS_PER_SESSION
    own = (await client.get(f"/api/v1/sessions/{sid}/interactions", headers=student)).json()
    assert all(e["ai_interpretation"] is None for e in own)
    researcher = await _login(client, world.researcher_email)
    staff = (await client.get(f"/api/v1/sessions/{sid}/interactions", headers=researcher)).json()
    interpreted = [e for e in staff if e["event_type"] == "SELF_EXPLANATION" and e["ai_interpretation"]]
    assert len(interpreted) == 5 and interpreted[0]["ai_interpretation"]["dimensions"] == ["RECURSIVE_LANGUAGE"]
    admin = await _login(client, world.admin_email)
    config = (await client.get("/api/v1/ai/config", headers=admin)).json()
    assert config["enabled"] is True and "no decide" in config["guarantees"][0]
    assert (await client.get("/api/v1/ai/config", headers=researcher)).status_code == 403


async def test_platform_works_without_llm(client: httpx.AsyncClient, world: SeededWorld, db: AsyncSession) -> None:
    await seed_catalog(db)
    await db.commit()
    task_id = str((await db.execute(select(Task.id).where(Task.code == "B-FIG-01"))).scalar_one())
    student = await _login(client, world.student_username)
    sid, offer = await _offer(client, student, task_id)
    reformulated = await client.post(
        f"/api/v1/sessions/{sid}/scaffold-events/{offer['scaffold_event_id']}/feedback",
        json={"action": "REFORMULATE"},
        headers=student,
    )
    assert reformulated.status_code == 200
    assert (await db.execute(select(AIInteraction))).scalars().all() == []
