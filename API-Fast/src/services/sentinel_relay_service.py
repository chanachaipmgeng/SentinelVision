"""Async IoT door/turnstile relay with retry + per-URL circuit breaker (Phase F2).

Replaces the urllib-in-executor path formerly in ``sentinel_routes``.
``relaySecret`` values may be Fernet-sealed (``fernet:…``); they are decrypted
only at dispatch time.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from .outbox_crypto import decrypt_secret

logger = logging.getLogger("dpu.sentinel.relay")

# Circuit breaker defaults
FAILURE_THRESHOLD = 5
COOLDOWN_SECONDS = 30.0
# Retry defaults
MAX_ATTEMPTS = 3
BASE_BACKOFF_SECONDS = 0.25
REQUEST_TIMEOUT_SECONDS = 4.0


@dataclass
class _CircuitState:
    failures: int = 0
    opened_at: float = 0.0
    state: str = "closed"  # closed | open | half_open


_circuits: dict[str, _CircuitState] = {}
_circuits_lock = asyncio.Lock()

_client: Optional[httpx.AsyncClient] = None
_client_lock = asyncio.Lock()


def reset_circuit_breakers() -> None:
    """Test helper: clear in-process breaker state."""
    _circuits.clear()


def circuit_state_for(url: str) -> dict[str, Any]:
    """Test helper: snapshot breaker state for a URL."""
    c = _circuits.get(url) or _CircuitState()
    return {
        "state": c.state,
        "failures": c.failures,
        "opened_at": c.opened_at,
    }


async def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is not None and not _client.is_closed:
        return _client
    async with _client_lock:
        if _client is None or _client.is_closed:
            _client = httpx.AsyncClient(
                timeout=httpx.Timeout(REQUEST_TIMEOUT_SECONDS),
                follow_redirects=False,
            )
        return _client


def _unseal_secret(secret: Optional[str]) -> Optional[str]:
    if not secret:
        return None
    text = str(secret).strip()
    if not text:
        return None
    return decrypt_secret(text)


async def _allow_request(url: str) -> bool:
    """Return False when the circuit is open (still cooling down)."""
    async with _circuits_lock:
        c = _circuits.get(url)
        if c is None:
            return True
        if c.state == "closed":
            return True
        if c.state == "open":
            if time.monotonic() - c.opened_at >= COOLDOWN_SECONDS:
                c.state = "half_open"
                return True
            return False
        # half_open: allow one probe
        return True


async def _record_success(url: str) -> None:
    async with _circuits_lock:
        _circuits[url] = _CircuitState()


async def _record_failure(url: str) -> None:
    async with _circuits_lock:
        c = _circuits.get(url) or _CircuitState()
        c.failures += 1
        if c.state == "half_open" or c.failures >= FAILURE_THRESHOLD:
            c.state = "open"
            c.opened_at = time.monotonic()
            logger.warning(
                "IoT relay circuit OPEN for %s after %s failures",
                url,
                c.failures,
            )
        _circuits[url] = c


async def dispatch_relay_webhook(
    webhook_url: str,
    secret: Optional[str],
    payload: dict,
    *,
    client: Optional[httpx.AsyncClient] = None,
) -> bool:
    """POST signed JSON to an IoT relay URL with exponential retry + circuit breaker.

    Returns True on HTTP 2xx, False on skip/failure. Never raises to callers.
    """
    if not webhook_url or not webhook_url.startswith(("http://", "https://")):
        return False

    if not await _allow_request(webhook_url):
        logger.warning("IoT relay circuit open; skipping %s", webhook_url)
        return False

    # Lazy import keeps this module free of SQLAlchemy/pgvector import side-effects.
    from .notification_service import compute_webhook_signature

    plain_secret = _unseal_secret(secret)
    body_bytes = json.dumps(payload).encode("utf-8")
    ts_str = str(int(datetime.now(timezone.utc).timestamp()))
    headers = {
        "Content-Type": "application/json",
        "X-Sentinel-Timestamp": ts_str,
    }
    if plain_secret:
        headers["X-DPU-Signature-256"] = compute_webhook_signature(
            plain_secret, ts_str, body_bytes
        )

    http = client or await _get_client()
    last_exc: Optional[BaseException] = None

    for attempt in range(MAX_ATTEMPTS):
        try:
            resp = await http.post(webhook_url, content=body_bytes, headers=headers)
            if 200 <= resp.status_code < 300:
                await _record_success(webhook_url)
                return True
            last_exc = RuntimeError(f"HTTP {resp.status_code}")
            logger.warning(
                "IoT relay webhook non-2xx for %s: %s (attempt %s/%s)",
                webhook_url,
                resp.status_code,
                attempt + 1,
                MAX_ATTEMPTS,
            )
        except Exception as exc:  # noqa: BLE001 — network errors are expected
            last_exc = exc
            logger.warning(
                "IoT relay webhook failed for %s (attempt %s/%s): %s",
                webhook_url,
                attempt + 1,
                MAX_ATTEMPTS,
                exc,
            )

        if attempt + 1 < MAX_ATTEMPTS:
            delay = BASE_BACKOFF_SECONDS * (2**attempt)
            await asyncio.sleep(delay)

    await _record_failure(webhook_url)
    if last_exc is not None:
        logger.warning("IoT relay webhook exhausted retries for %s", webhook_url)
    return False


# Back-compat alias used by thin wrappers in sentinel_routes.
dispatch_relay_webhook_async = dispatch_relay_webhook
