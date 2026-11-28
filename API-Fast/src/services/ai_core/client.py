"""Async HTTP client for shared ai-core-service Phase 1 LLM APIs."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any, Literal

import httpx

from ...config.settings import settings

logger = logging.getLogger(__name__)

_client: "AsyncAiCoreClient | None" = None


class AsyncAiCoreClient:
    def __init__(self, base_url: str, api_key: str, *, timeout: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=10.0),
            headers={"X-API-Key": api_key},
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def generate(
        self,
        messages: list[dict[str, str]],
        *,
        system: str | None = None,
        mode: Literal["answer", "light"] = "answer",
        temperature: float = 0.2,
        max_output_tokens: int = 1024,
        model: str | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "messages": messages,
            "mode": mode,
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
        }
        if system:
            body["system"] = system
        if model:
            body["model"] = model
        kwargs: dict[str, Any] = {"json": body}
        if timeout is not None:
            kwargs["timeout"] = timeout
        resp = await self._client.post(f"{self.base_url}/v1/llm/generate", **kwargs)
        resp.raise_for_status()
        return resp.json()

    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        system: str | None = None,
        mode: Literal["answer", "light"] = "answer",
        temperature: float = 0.2,
        max_output_tokens: int = 1024,
        model: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield parsed SSE events: {event, data} where data is a JSON object."""
        body: dict[str, Any] = {
            "messages": messages,
            "mode": mode,
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
        }
        if system:
            body["system"] = system
        if model:
            body["model"] = model

        async with self._client.stream(
            "POST",
            f"{self.base_url}/v1/llm/stream",
            json=body,
            timeout=httpx.Timeout(60.0, read=60.0),
        ) as resp:
            resp.raise_for_status()
            event_name = "message"
            async for line in resp.aiter_lines():
                if line.startswith("event:"):
                    event_name = line[6:].strip() or "message"
                    continue
                if not line.startswith("data:"):
                    continue
                raw = line[5:].strip()
                if not raw:
                    continue
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                yield {"event": event_name, "data": data}
                event_name = "message"


def get_ai_core_client() -> AsyncAiCoreClient:
    """Lazy process-wide client (settings must have URL + key)."""
    global _client
    url = (settings.AI_CORE_URL or "").strip()
    key = (settings.AI_CORE_API_KEY or "").strip()
    if not url or not key:
        raise RuntimeError("AI core client requested but AI_CORE_URL / AI_CORE_API_KEY are empty")
    if _client is None:
        _client = AsyncAiCoreClient(url, key)
    return _client


def reset_ai_core_client() -> None:
    """Test helper — drop the cached client after settings change."""
    global _client
    _client = None
