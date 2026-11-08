"""F2: IoT relay httpx dispatch — exponential retry + per-URL circuit breaker."""
from __future__ import annotations

import httpx
import pytest
from cryptography.fernet import Fernet

from src.services import outbox_crypto as crypto
from src.services import sentinel_relay_service as relay


@pytest.fixture(autouse=True)
def _reset_breakers():
    relay.reset_circuit_breakers()
    yield
    relay.reset_circuit_breakers()


@pytest.mark.asyncio
async def test_dispatch_success_posts_signed_json(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(crypto.settings, "OUTBOX_ENCRYPTION_KEY", key)
    sealed = crypto.seal_relay_secret("whsec-test")
    assert sealed and sealed.startswith("fernet:")

    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        ok = await relay.dispatch_relay_webhook(
            "https://relay.example/door",
            sealed,
            {"event": "door.access_granted", "zoneCode": "GATE-1"},
            client=client,
        )
    assert ok is True
    assert len(seen) == 1
    req = seen[0]
    assert req.method == "POST"
    assert req.url.path == "/door"
    assert req.headers["Content-Type"] == "application/json"
    assert "X-Sentinel-Timestamp" in req.headers
    assert req.headers["X-DPU-Signature-256"].startswith("v1=")
    assert relay.circuit_state_for("https://relay.example/door")["state"] == "closed"


@pytest.mark.asyncio
async def test_dispatch_retries_then_opens_circuit():
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        return httpx.Response(503, json={"error": "down"})

    url = "https://relay.example/fail"
    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        # Drive FAILURE_THRESHOLD failed dispatches (each does MAX_ATTEMPTS).
        for _ in range(relay.FAILURE_THRESHOLD):
            ok = await relay.dispatch_relay_webhook(
                url, None, {"event": "door.remote_unlock"}, client=client
            )
            assert ok is False

    assert attempts["n"] == relay.FAILURE_THRESHOLD * relay.MAX_ATTEMPTS
    state = relay.circuit_state_for(url)
    assert state["state"] == "open"
    assert state["failures"] >= relay.FAILURE_THRESHOLD

    # Circuit open → skip without further HTTP.
    before = attempts["n"]
    async with httpx.AsyncClient(transport=transport) as client:
        ok = await relay.dispatch_relay_webhook(
            url, None, {"event": "door.remote_unlock"}, client=client
        )
    assert ok is False
    assert attempts["n"] == before


@pytest.mark.asyncio
async def test_dispatch_half_open_recovers_after_cooldown(monkeypatch):
    monkeypatch.setattr(relay, "COOLDOWN_SECONDS", 0.0)
    monkeypatch.setattr(relay, "FAILURE_THRESHOLD", 1)
    monkeypatch.setattr(relay, "MAX_ATTEMPTS", 1)
    monkeypatch.setattr(relay, "BASE_BACKOFF_SECONDS", 0.0)

    phase = {"fail": True}

    def handler(request: httpx.Request) -> httpx.Response:
        if phase["fail"]:
            return httpx.Response(500)
        return httpx.Response(204)

    url = "https://relay.example/recover"
    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        assert (
            await relay.dispatch_relay_webhook(url, None, {"event": "x"}, client=client)
            is False
        )
        assert relay.circuit_state_for(url)["state"] == "open"

        phase["fail"] = False
        # cooldown 0 → half_open probe allowed
        assert (
            await relay.dispatch_relay_webhook(url, None, {"event": "x"}, client=client)
            is True
        )
    assert relay.circuit_state_for(url)["state"] == "closed"


@pytest.mark.asyncio
async def test_invalid_url_skipped():
    assert await relay.dispatch_relay_webhook("", None, {}) is False
    assert await relay.dispatch_relay_webhook("ftp://nope", None, {}) is False
