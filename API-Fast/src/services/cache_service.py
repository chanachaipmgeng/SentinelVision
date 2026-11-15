"""Lightweight Redis JSON cache and Kiosk scan debounce helpers.

Falls back transparently to cache-miss / allow-scan when ``REDIS_URL`` is unset
or Redis is temporarily unreachable, so API availability never depends on Redis.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from ..config.settings import settings
from .redis_client import get_redis

logger = logging.getLogger("dpu.cache")


async def cache_get_json(key: str) -> Optional[Any]:
    """Return deserialized JSON value for ``key`` or ``None`` on miss/error."""
    redis = get_redis()
    if redis is None:
        return None
    try:
        raw = await redis.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception:
        logger.debug("redis cache_get_json failed for %s", key, exc_info=True)
        return None


async def cache_set_json(key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
    """Serialize ``value`` as JSON into Redis with TTL; returns False on skip/error."""
    redis = get_redis()
    if redis is None:
        return False
    ttl = int(ttl_seconds if ttl_seconds is not None else getattr(settings, "CACHE_TTL_SECONDS", 300))
    if ttl <= 0:
        return False
    try:
        await redis.set(key, json.dumps(value), ex=ttl)
        return True
    except Exception:
        logger.debug("redis cache_set_json failed for %s", key, exc_info=True)
        return False


async def cache_delete(key: str) -> bool:
    """Invalidate ``key`` in Redis; returns False when Redis is unavailable."""
    redis = get_redis()
    if redis is None:
        return False
    try:
        await redis.delete(key)
        return True
    except Exception:
        logger.debug("redis cache_delete failed for %s", key, exc_info=True)
        return False


async def kiosk_scan_debounce_check(
    company_id: str,
    member_id: str,
    *,
    ttl_seconds: int = 5,
) -> bool:
    """Return True if this scan should proceed, False if recently debounced.

    Uses atomic ``SET ... NX EX`` across all API replicas. When Redis is
    unavailable, returns True so check-ins are never blocked.
    """
    if ttl_seconds <= 0:
        return True
    redis = get_redis()
    if redis is None:
        return True
    key = f"sv:kiosk:debounce:{company_id}:{member_id}"
    try:
        acquired = await redis.set(key, "1", nx=True, ex=int(ttl_seconds))
        return bool(acquired)
    except Exception:
        logger.debug("redis kiosk_scan_debounce_check failed for %s", key, exc_info=True)
        return True
