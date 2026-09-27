"""Proveedores de LLM tras una interfaz mínima. ``NullProvider`` por defecto (sin IA)."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.core.config import Settings
from app.core.logging import get_logger

log = get_logger("app.ai")


@dataclass(slots=True)
class LLMRequest:
    purpose: str
    system: str
    user: str
    json_schema: dict[str, Any]
    max_tokens: int = 1024


@dataclass(slots=True)
class LLMResponse:
    ok: bool
    text: str | None
    data: dict[str, Any] | None
    provider: str
    model: str | None
    latency_ms: int
    error: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


class LLMProvider(Protocol):
    name: str
    model: str | None

    async def complete(self, request: LLMRequest) -> LLMResponse: ...


class NullProvider:
    """Sin IA: siempre devuelve 'no disponible' y el sistema usa el banco."""

    name = "null"
    model: str | None = None

    async def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            ok=False, text=None, data=None, provider=self.name, model=None, latency_ms=0, error="disabled"
        )


class FakeProvider:
    """Proveedor determinista para pruebas: ``responder(request) -> dict | str``."""

    name = "fake"

    def __init__(
        self, responder: Callable[[LLMRequest], dict[str, Any] | str] | None = None, model: str = "fake-model"
    ) -> None:
        self.model: str | None = model
        self.responder = responder or (lambda _req: {})
        self.calls: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.calls.append(request)
        started = time.perf_counter()
        output = self.responder(request)
        text = output if isinstance(output, str) else json.dumps(output, ensure_ascii=False)
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = None
        return LLMResponse(
            ok=data is not None,
            text=text,
            data=data if isinstance(data, dict) else None,
            provider=self.name,
            model=self.model,
            latency_ms=int((time.perf_counter() - started) * 1000),
            error=None if data is not None else "invalid_json",
        )


class AnthropicProvider:
    """Claude vía SDK oficial ``anthropic`` (asíncrono).

    * Salida estructurada con ``output_config.format`` (esquema JSON) → JSON válido garantizado.
    * ``effort: low``: tareas cortas y acotadas.
    * Respaldo del servidor ante rechazos (``fallbacks: "default"``) y comprobación de ``stop_reason``.
    * Tiempo límite corto y reintentos limitados: nunca bloquea la experiencia del estudiante.
    """

    name = "anthropic"

    def __init__(self, settings: Settings) -> None:
        import anthropic

        self.model: str | None = settings.llm_model
        self._anthropic = anthropic
        self._client = anthropic.AsyncAnthropic(
            api_key=settings.llm_api_key, timeout=settings.llm_timeout_ms / 1000, max_retries=1
        )

    async def complete(self, request: LLMRequest) -> LLMResponse:
        anthropic = self._anthropic
        started = time.perf_counter()

        def result(
            ok: bool, text: str | None = None, data: dict[str, Any] | None = None, error: str | None = None, **meta: Any
        ) -> LLMResponse:
            return LLMResponse(
                ok=ok,
                text=text,
                data=data,
                provider=self.name,
                model=self.model,
                latency_ms=int((time.perf_counter() - started) * 1000),
                error=error,
                meta=meta,
            )

        try:
            response = await self._client.beta.messages.create(
                model=self.model or "claude-opus-5",
                max_tokens=request.max_tokens,
                system=request.system,
                messages=[{"role": "user", "content": request.user}],
                output_config={"effort": "low", "format": {"type": "json_schema", "schema": request.json_schema}},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except anthropic.RateLimitError:
            return result(False, error="rate_limited")
        except anthropic.APIStatusError as exc:
            log.warning("llm_api_error", status=exc.status_code)
            return result(False, error=f"api_error_{exc.status_code}")
        except anthropic.APIConnectionError:
            return result(False, error="connection_error")

        request_id = getattr(response, "_request_id", None)
        if response.stop_reason == "refusal":
            return result(False, error="refusal", request_id=request_id)
        if response.stop_reason == "max_tokens":
            return result(False, error="max_tokens", request_id=request_id)
        text = next((b.text for b in response.content if b.type == "text"), None)
        if text is None:
            return result(False, error="no_text", request_id=request_id)
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return result(False, text=text, error="invalid_json", request_id=request_id)
        return result(
            isinstance(data, dict),
            text=text,
            data=data if isinstance(data, dict) else None,
            request_id=request_id,
            served_model=getattr(response, "model", None),
        )


_override: LLMProvider | None = None


def set_provider_override(provider: LLMProvider | None) -> None:
    """Permite inyectar un proveedor (pruebas)."""
    global _override
    _override = provider


def build_provider(settings: Settings) -> LLMProvider:
    if _override is not None:
        return _override
    if not settings.llm_enabled or settings.llm_provider == "null":
        return NullProvider()
    if settings.llm_provider == "anthropic":
        return AnthropicProvider(settings)
    return FakeProvider()
