"""Real-time Watchlist & Security Incident WebSocket broadcast hub.

Supports single-node in-memory fanout plus optional Redis Pub/Sub fanout across
multi-replica API deployments (channel ``sv:incidents:{companyId}``).
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
import json
import logging
from typing import Any
from uuid import UUID

from fastapi import WebSocket

from .redis_client import get_redis

logger = logging.getLogger("dpu.incident_ws")


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


async def publish_incident_event(company_id: str | UUID, incident_payload: dict[str, Any]) -> None:
    """Push a new/updated security incident to all connected consoles for ``company_id``."""
    envelope = {"type": "incident", "data": incident_payload}
    await incident_ws_hub.broadcast_local(company_id, envelope)
    redis = get_redis()
    if redis is not None:
        try:
            await redis.publish(
                f"sv:incidents:{company_id}",
                json.dumps(envelope, default=str),
            )
        except Exception:
            logger.debug("redis publish_incident_event failed", exc_info=True)
