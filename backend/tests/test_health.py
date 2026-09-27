"""Pruebas de la API base: salud, metadatos, errores y cabeceras de seguridad."""

from __future__ import annotations

import httpx
import pytest
from app.modules.common.enums import STUDENT_FACING_STATE_LABELS, StudentState


async def test_health_returns_service_info(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["environment"] == "test"
    assert body["version"]


async def test_security_headers_and_request_id(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/health", headers={"X-Request-ID": "abc-123"})
    assert response.headers["X-Request-ID"] == "abc-123"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Cache-Control"] == "no-store"
    assert "Strict-Transport-Security" not in response.headers  # solo en producción


async def test_generated_request_id_when_header_is_invalid(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/health", headers={"X-Request-ID": "x" * 200})
    assert response.headers["X-Request-ID"] != "x" * 200
    assert len(response.headers["X-Request-ID"]) == 32


async def test_cors_allows_configured_origin_only(client: httpx.AsyncClient) -> None:
    ok = await client.options(
        "/api/v1/health",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    denied = await client.options(
        "/api/v1/health",
        headers={"Origin": "https://evil.test", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in denied.headers


async def test_not_found_uses_error_envelope(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["error"]["request_id"]


async def test_meta_exposes_vocabularies_without_negative_labels(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/meta")
    assert response.status_code == 200
    body = response.json()
    assert body["roles"] == ["STUDENT", "TEACHER", "RESEARCHER", "ADMIN"]
    assert set(body["student_states"]) == {s.value for s in StudentState}
    assert body["intervention_levels"] == ["0", "1", "2", "3", "4", "5"]
    assert len(body["interaction_event_types"]) == 18
    assert body["llm_enabled"] is False
    # Las etiquetas visibles para el estudiante nunca contienen las etiquetas operativas negativas.
    for label in STUDENT_FACING_STATE_LABELS.values():
        assert label.upper() not in {"DIFICULTAD", "ESTANCAMIENTO", "IMPULSIVIDAD", "INCERTIDUMBRE"}
    assert body["student_state_labels"]["STAGNATION"] == "Buscando otro camino"


async def test_readiness_reports_database(
    client: httpx.AsyncClient, database_available: bool
) -> None:
    response = await client.get("/api/v1/health/ready")
    if database_available:
        assert response.status_code == 200
        assert response.json() == {"status": "ready", "database": "ok"}
    else:
        pytest.skip("PostgreSQL no disponible: se verifica solo la respuesta 503")
