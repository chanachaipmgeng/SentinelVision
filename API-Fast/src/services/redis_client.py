"""Optional Redis client for rate limits + idempotency (Phase D7).

When ``REDIS_URL`` is empty the helpers return ``None`` and callers fall back to
in-process memory (fine for single-replica / pytest).
"""
from __future__ import annotations

import logging
from typing import Any

from ..config.settings import settings

logger = logging.getLogger("dpu.redis")

_client: Any = None
_failed = False


def redis_url() -> str:
    return (getattr(settings, "REDIS_URL", None) or "").strip()


def get_redis() -> Any:
    """Return a shared ``redis.asyncio.Redis`` or ``None`` when unavailable."""
    global _client, _failed
    url = redis_url()
    if not url or _failed:
        return None
    if _client is not None:
        return _client
    try:
        from redis.asyncio import Redis

        _client = Redis.from_url(url, decode_responses=True)
        return _client
    except Exception:
        logger.warning("redis unavailable at %s; using in-process fallback", url, exc_info=True)
        _failed = True
        return None


async def redis_ping() -> bool:
    client = get_redis()
    if client is None:
        return False
    try:
        return bool(await client.ping())
    except Exception:
        return False


def reset_redis_for_tests() -> None:
    global _client, _failed
    _client = None
    _failed = False
