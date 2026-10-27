"""Cliente LLM multi-proveedor con salida JSON estricta, reintentos y cadena de respaldo.

Gemini usa la API REST de Google AI Studio (httpx); Anthropic usa el SDK oficial.
Cada agente instancia su propio cliente con su modelo predeterminado.
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from backend.core.config import Settings

log = logging.getLogger("llm")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
RETRYABLE = {429, 500, 502, 503, 504}


@dataclass
class LLMResult:
    data: dict[str, Any]
    tokens: int
    model: str


class LLMError(RuntimeError):
    pass


class LLMClient(Protocol):
    models: list[str]

    async def generate_json(self, system: str, user: str, schema: dict[str, Any],
                            max_tokens: int = 8192) -> LLMResult: ...


class GeminiClient:
    """Prueba cada modelo de la cadena; reintenta 429/5xx/timeouts con backoff."""

    def __init__(self, api_key: str, models: list[str], timeout_s: float, retries: int = 2) -> None:
        self.api_key, self.models = api_key, models
        self.timeout_s, self.retries = timeout_s, retries

    async def generate_json(self, system: str, user: str, schema: dict[str, Any],
                            max_tokens: int = 8192) -> LLMResult:
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"responseMimeType": "application/json", "responseJsonSchema": schema,
                                 "maxOutputTokens": max_tokens},
        }
        errors: list[str] = []
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            for model in self.models:
                for attempt in range(self.retries + 1):
                    try:
                        r = await client.post(GEMINI_URL.format(model=model), json=body,
                                              headers={"x-goog-api-key": self.api_key})
                    except httpx.TimeoutException:
                        errors.append(f"{model}: timeout")
                        break  # un modelo lento no se reintenta: pasa al siguiente
                    except httpx.HTTPError as exc:
                        errors.append(f"{model}: {type(exc).__name__}")
                        break
                    if r.status_code == 200:
                        return self._parse(r.json(), model)
                    msg = r.json().get("error", {}).get("status", str(r.status_code))
                    if r.status_code not in RETRYABLE:
                        raise LLMError(f"{model}: {r.status_code} {msg}")
                    errors.append(f"{model}: {r.status_code} {msg}")
                    if attempt < self.retries:
                        await asyncio.sleep(1.5 * (attempt + 1))
        raise LLMError("; ".join(errors[-4:]))

    @staticmethod
    def _parse(payload: dict[str, Any], model: str) -> LLMResult:
        usage = payload.get("usageMetadata", {})
        tokens = int(usage.get("totalTokenCount", 0))
        cand = (payload.get("candidates") or [{}])[0]
        if cand.get("finishReason") not in (None, "STOP", "MAX_TOKENS"):
            raise LLMError(f"{model}: respuesta bloqueada ({cand.get('finishReason')})")
        text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []) if not p.get("thought"))
        try:
            return LLMResult(json.loads(text), tokens, model)
        except json.JSONDecodeError as exc:
            raise LLMError(f"{model}: JSON inválido") from exc


class AnthropicClient:
    """Claude vía SDK oficial con Structured Outputs y fallback de servidor."""

    def __init__(self, api_key: str, model: str, effort: str) -> None:
        import anthropic

        self._anthropic = anthropic
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.models, self.effort = [model], effort

    async def generate_json(self, system: str, user: str, schema: dict[str, Any],
                            max_tokens: int = 16000) -> LLMResult:
        a = self._anthropic
        try:
            response = await self.client.beta.messages.create(
                model=self.models[0], max_tokens=max_tokens, system=system,
                messages=[{"role": "user", "content": user}],
                output_config={"effort": self.effort, "format": {"type": "json_schema", "schema": schema}},
                betas=["server-side-fallback-2026-07-01"], fallbacks="default")
        except a.APIStatusError as exc:
            raise LLMError(f"{self.models[0]}: {exc.status_code}") from exc
        except a.APIConnectionError as exc:
            raise LLMError(f"{self.models[0]}: conexión") from exc
        tokens = response.usage.input_tokens + response.usage.output_tokens
        if response.stop_reason == "refusal":
            raise LLMError(f"{response.model}: solicitud declinada")
        text = next((b.text for b in response.content if b.type == "text"), "")
        try:
            return LLMResult(json.loads(text), tokens, response.model)
        except json.JSONDecodeError as exc:
            raise LLMError(f"{response.model}: JSON inválido") from exc


def build_client(cfg: Settings, model: str, fallbacks: list[str]) -> LLMClient | None:
    """Cliente para un agente concreto, o None si no hay clave (modo determinista)."""
    if cfg.llm_provider == "anthropic":
        claude_model = model if model.startswith("claude") else "claude-opus-5-5"
        return AnthropicClient(cfg.llm_api_key, claude_model, cfg.llm_effort) if cfg.llm_api_key else None
    if cfg.gemini_api_key:
        return GeminiClient(cfg.gemini_api_key, [model, *[m for m in fallbacks if m != model]], cfg.llm_timeout_s)
    return None
