"""AI core cutover for SentinelVision assistant (mocked gateway / SSE)."""

from __future__ import annotations

import json
import uuid
from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest

from src.config import settings as settings_mod
from src.services.ai_core.client import AsyncAiCoreClient, reset_ai_core_client
from src.services.ai_core.flags import ai_core_enabled
from src.services import sentinel_assistant_service as assistant


COMPANY_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

SAMPLE_SNAP: dict[str, Any] = {
    "workDate": "2026-03-28",
    "presentToday": 12,
    "openIncidents": 1,
    "activeZones": 3,
    "activeWatchlist": 2,
    "camerasByStatus": {"online": 4, "offline": 1},
    "recentIncidents": [],
}


@pytest.fixture(autouse=True)
def _reset_ai_core(monkeypatch: pytest.MonkeyPatch):
    reset_ai_core_client()
    monkeypatch.setattr(settings_mod.settings, "AI_CORE_URL", "")
    monkeypatch.setattr(settings_mod.settings, "AI_CORE_API_KEY", "")
    monkeypatch.setattr(settings_mod.settings, "GOOGLE_API_KEY", "")
    monkeypatch.setattr(settings_mod.settings, "GEMINI_MODEL", "gemini-2.5-flash")
    yield
    reset_ai_core_client()


def _parse_sse_frames(raw_frames: list[str]) -> list[tuple[str, dict[str, Any]]]:
    out: list[tuple[str, dict[str, Any]]] = []
    for frame in raw_frames:
        event = "message"
        data: dict[str, Any] = {}
        for line in frame.strip().splitlines():
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                data = json.loads(line[5:].strip())
        out.append((event, data))
    return out


def test_ai_core_disabled_by_default() -> None:
    assert ai_core_enabled() is False


def test_ai_core_requires_both(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings_mod.settings, "AI_CORE_URL", "http://127.0.0.1:8088")
    monkeypatch.setattr(settings_mod.settings, "AI_CORE_API_KEY", "")
    assert ai_core_enabled() is False

    monkeypatch.setattr(settings_mod.settings, "AI_CORE_API_KEY", "dev-key")
    assert ai_core_enabled() is True


@pytest.mark.asyncio
async def test_flag_off_db_snapshot_unchanged() -> None:
    frames = [
        f
        async for f in assistant.stream_assistant_chat(
            None,
            COMPANY_ID,
            "สรุปวันนี้",
            snapshot=SAMPLE_SNAP,
        )
    ]
    events = _parse_sse_frames(frames)
    assert events[0][0] == "status"
    assert any(e == "token" for e, _ in events)
    done = [d for e, d in events if e == "done"][-1]
    assert done["provider"] == "db-snapshot"
    assert "presentToday" in done["snapshot"]


@pytest.mark.asyncio
async def test_stream_via_ai_core_maps_sse(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings_mod.settings, "AI_CORE_URL", "http://127.0.0.1:8088")
    monkeypatch.setattr(settings_mod.settings, "AI_CORE_API_KEY", "dev-key")

    async def fake_stream(*_args: Any, **_kwargs: Any):
        yield {"event": "token", "data": {"text": "สวัสดี "}}
        yield {"event": "token", "data": {"text": "จาก ai-core"}}
        yield {"event": "done", "data": {"model": "gemini-3.6-flash", "provider": "gemini"}}

    fake = MagicMock()
    fake.stream = fake_stream
    monkeypatch.setattr(
        "src.services.ai_core.client.get_ai_core_client",
        lambda: fake,
    )

    frames = [
        f
        async for f in assistant.stream_assistant_chat(
            None,
            COMPANY_ID,
            "hello",
            history=[{"role": "user", "content": "hi"}],
            snapshot=SAMPLE_SNAP,
        )
    ]
    events = _parse_sse_frames(frames)
    tokens = [d["text"] for e, d in events if e == "token"]
    assert "".join(tokens) == "สวัสดี จาก ai-core"
    done = [d for e, d in events if e == "done"][-1]
    assert done["provider"] == "ai-core"
    assert done.get("model") == "gemini-3.6-flash"


@pytest.mark.asyncio
async def test_ai_core_failure_falls_back_to_db_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings_mod.settings, "AI_CORE_URL", "http://127.0.0.1:8088")
    monkeypatch.setattr(settings_mod.settings, "AI_CORE_API_KEY", "dev-key")

    async def boom(*_args: Any, **_kwargs: Any):
        raise httpx.ConnectError("refused")
        yield  # pragma: no cover — make this an async generator

    fake = MagicMock()
    fake.stream = boom
    monkeypatch.setattr(
        "src.services.ai_core.client.get_ai_core_client",
        lambda: fake,
    )

    frames = [
        f
        async for f in assistant.stream_assistant_chat(
            None,
            COMPANY_ID,
            "สถานะกล้อง",
            snapshot=SAMPLE_SNAP,
        )
    ]
    events = _parse_sse_frames(frames)
    tokens = "".join(d["text"] for e, d in events if e == "token")
    assert "PRESENT" in tokens or "presentToday" in tokens or "พนักงาน" in tokens
    done = [d for e, d in events if e == "done"][-1]
    assert done["provider"] == "db-fallback"
    assert done.get("via") == "ai-core-error"


@pytest.mark.asyncio
async def test_client_stream_parses_sse_lines() -> None:
    sse_body = (
        "event: token\ndata: {\"text\": \"Hi\"}\n\n"
        "event: done\ndata: {\"model\": \"m\", \"provider\": \"gemini\"}\n\n"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/llm/stream"
        assert request.headers.get("X-API-Key") == "dev-key"
        body = json.loads(request.content.decode())
        assert body["messages"][0]["content"] == "q"
        assert body["system"] == "sys"
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=sse_body.encode(),
        )

    client = AsyncAiCoreClient("http://example.invalid", "dev-key")
    await client.aclose()
    client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        headers={"X-API-Key": "dev-key"},
    )
    events = [e async for e in client.stream([{"role": "user", "content": "q"}], system="sys")]
    await client.aclose()
    assert events[0] == {"event": "token", "data": {"text": "Hi"}}
    assert events[1]["event"] == "done"
