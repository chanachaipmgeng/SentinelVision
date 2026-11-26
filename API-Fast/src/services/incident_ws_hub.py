"""Real-time Watchlist & Security Incident WebSocket broadcast hub.

Supports single-node in-memory fanout plus optional Redis Pub/Sub fanout across
multi-replica API deployments (channel ``sv:incidents:{companyId}``).
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
import json
import logging
from typing import Any, Optional
from uuid import UUID, uuid4

from fastapi import WebSocket

from .redis_client import get_redis

logger = logging.getLogger("dpu.incident_ws")

_CHANNEL_PREFIX = "sv:incidents:"
_NODE_ID = str(uuid4())
_subscriber_task: Optional[asyncio.Task[None]] = None
_subscriber_stop: Optional[asyncio.Event] = None


class IncidentWsHub:
    """Tracks active WebSocket subscribers per companyId."""

    def __init__(self) -> None:
        self._subs: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def subscribe(self, company_id: str | UUID, ws: WebSocket) -> None:
        key = str(company_id)
        async with self._lock:
            self._subs[key].add(ws)

    async def unsubscribe(self, company_id: str | UUID, ws: WebSocket) -> None:
        key = str(company_id)
        async with self._lock:
            bucket = self._subs.get(key)
            if bucket is not None:
                bucket.discard(ws)
                if not bucket:
                    self._subs.pop(key, None)

    async def broadcast_local(self, company_id: str | UUID, message: dict[str, Any]) -> int:
        key = str(company_id)
        async with self._lock:
            targets = list(self._subs.get(key, ()))
        if not targets:
            return 0
        payload = json.dumps(message, default=str)
        sent = 0
        stale: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_text(payload)
                sent += 1
            except Exception:
                stale.append(ws)
        if stale:
            async with self._lock:
                bucket = self._subs.get(key)
                if bucket is not None:
                    for ws in stale:
                        bucket.discard(ws)
                    if not bucket:
                        self._subs.pop(key, None)
        return sent

    def subscriber_count(self, company_id: str | UUID) -> int:
        return len(self._subs.get(str(company_id), ()))


incident_ws_hub = IncidentWsHub()


async def handle_redis_incident_message(raw_message: dict[str, Any]) -> int:
    """Decode one Redis Pub/Sub pmessage and deliver to local company sockets if remote."""
    channel = raw_message.get("channel")
    if isinstance(channel, bytes):
        channel = channel.decode("utf-8", errors="replace")
    if not isinstance(channel, str) or not channel.startswith(_CHANNEL_PREFIX):
        return 0
    company_id = channel[len(_CHANNEL_PREFIX) :].strip()
    if not company_id:
        return 0
    raw_data = raw_message.get("data")
    if isinstance(raw_data, bytes):
        raw_data = raw_data.decode("utf-8", errors="replace")
    if not isinstance(raw_data, str) or not raw_data:
        return 0
    try:
        envelope = json.loads(raw_data)
    except Exception:
        return 0
    if not isinstance(envelope, dict):
        return 0
    if envelope.get("originNode") == _NODE_ID:
        return 0
    client_frame = {
        "type": envelope.get("type") or "incident",
        "data": envelope.get("data"),
    }
    return await incident_ws_hub.broadcast_local(company_id, client_frame)


async def _incident_redis_listener(stop_event: asyncio.Event) -> None:
    backoff = 1.0
    while not stop_event.is_set():
        redis = get_redis()
        if redis is None:
            return
        pubsub = None
        try:
            pubsub = redis.pubsub()
            await pubsub.psubscribe(f"{_CHANNEL_PREFIX}*")
            backoff = 1.0
            while not stop_event.is_set():
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg and msg.get("type") in ("pmessage", "message"):
                    await handle_redis_incident_message(msg)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.debug("incident_ws_hub redis subscriber error; reconnecting", exc_info=True)
            if stop_event.is_set():
                break
            await asyncio.sleep(backoff)
            backoff = min(15.0, backoff * 2.0)
        finally:
            if pubsub is not None:
                try:
                    await pubsub.close()
                except Exception:
                    pass


async def start_incident_ws_subscriber() -> None:
    """Start background Redis Pub/Sub listener when REDIS_URL is configured."""
    global _subscriber_task, _subscriber_stop
    if _subscriber_task is not None and not _subscriber_task.done():
        return
    if get_redis() is None:
        return
    _subscriber_stop = asyncio.Event()
    _subscriber_task = asyncio.create_task(
        _incident_redis_listener(_subscriber_stop),
        name="incident-ws-redis-sub",
    )


async def stop_incident_ws_subscriber() -> None:
    """Stop the background Redis Pub/Sub listener cleanly."""
    global _subscriber_task, _subscriber_stop
    if _subscriber_stop is not None:
        _subscriber_stop.set()
    if _subscriber_task is not None:
        _subscriber_task.cancel()
        try:
            await _subscriber_task
        except asyncio.CancelledError:
            pass
    _subscriber_task = None
    _subscriber_stop = None


async def publish_incident_event(company_id: str | UUID, incident_payload: dict[str, Any]) -> None:
    """Push a new/updated security incident to all connected consoles for ``company_id``."""
    client_frame = {"type": "incident", "data": incident_payload}
    await incident_ws_hub.broadcast_local(company_id, client_frame)
    redis = get_redis()
    if redis is not None:
        try:
            redis_envelope = {**client_frame, "originNode": _NODE_ID}
            await redis.publish(
                f"{_CHANNEL_PREFIX}{company_id}",
                json.dumps(redis_envelope, default=str),
            )
        except Exception:
            logger.debug("redis publish_incident_event failed", exc_info=True)
