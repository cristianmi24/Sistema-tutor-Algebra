"""Sin base de datos, /health/ready responde 503 con el sobre de error, sin filtrar detalles."""

from __future__ import annotations

import httpx
from app.core.config import Settings
from app.main import create_app


async def test_readiness_returns_503_when_database_is_down() -> None:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        app_env="test",
        database_url="postgresql+psycopg://nobody:nothing@127.0.0.1:1/none",
        jwt_secret_key="test-secret-key-with-at-least-32-characters!!",
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)  # type: ignore[arg-type]
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/v1/health/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert "nobody" not in response.text
    assert "127.0.0.1" not in response.text
