"""Application-layer rate limits (Phase D7) — complements nginx ``limit_req``.

Fixed-window counters per (bucket, key). Redis when ``REDIS_URL`` is set; otherwise
an in-process dict (good enough for pytest / single replica).
"""
from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock
from typing import Optional, Tuple

from fastapi import HTTPException, Request
from starlette.responses import JSONResponse

from ..config.settings import settings
from ..schemas.error_schema import error_body
from .redis_client import get_redis

_memory: dict[str, list[float]] = defaultdict(list)
_lock = Lock()


def _client_ip(request: Request) -> str:
    xff = (request.headers.get("x-forwarded-for") or "").strip()
    if xff:
        return xff.split(",")[0].strip()
    xrip = (request.headers.get("x-real-ip") or "").strip()
    if xrip:
        return xrip
    return request.client.host if request.client else "unknown"


def _window_key(bucket: str, key: str, window_seconds: int) -> str:
    slot = int(time.time()) // max(1, window_seconds)
    return f"dpu:rl:{bucket}:{key}:{slot}"


def _memory_hit(full_key: str, limit: int, window_seconds: int) -> Tuple[bool, int]:
    now = time.time()
    cutoff = now - window_seconds
    with _lock:
        stamps = [t for t in _memory[full_key] if t >= cutoff]
        if len(stamps) >= limit:
            _memory[full_key] = stamps
            return False, 0
        stamps.append(now)
        _memory[full_key] = stamps
        return True, max(0, limit - len(stamps))


async def check_rate_limit(
    bucket: str,
    key: str,
    *,
    limit: int,
    window_seconds: int = 60,
) -> Tuple[bool, int]:
    """Return ``(allowed, remaining)``. ``limit <= 0`` disables the bucket."""
    if limit <= 0:
        return True, -1
    redis = get_redis()
    full = _window_key(bucket, key, window_seconds)
    if redis is not None:
        try:
            count = await redis.incr(full)
            if count == 1:
                await redis.expire(full, window_seconds + 1)
            remaining = max(0, limit - int(count))
            return int(count) <= limit, remaining
        except Exception:
            pass
    # Memory key includes the window slot already; reuse full as map key.
    return _memory_hit(full, limit, window_seconds)


def reset_rate_limits_for_tests() -> None:
    with _lock:
        _memory.clear()


def rate_limit_response(request: Request, *, retry_after: int = 60) -> JSONResponse:
    body = error_body(
        code="rate_limited",
        message="Too many requests",
        status_code=429,
        request_id=getattr(request.state, "request_id", None),
    )
    return JSONResponse(
        body,
        status_code=429,
        headers={"Retry-After": str(max(1, int(retry_after)))},
    )


async def enforce_rate_limit(
    request: Request,
    bucket: str,
    *,
    limit: int,
    window_seconds: int = 60,
    key: Optional[str] = None,
) -> None:
    """Raise HTTP 429 when the bucket is exhausted."""
    identity = key or _client_ip(request)
    allowed, _remaining = await check_rate_limit(
        bucket, identity, limit=limit, window_seconds=window_seconds
    )
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Too many requests",
            headers={"Retry-After": str(window_seconds)},
        )


async def rate_limit_login(request: Request) -> None:
    await enforce_rate_limit(
        request,
        "login",
        limit=int(getattr(settings, "RATE_LIMIT_LOGIN_PER_MINUTE", 20) or 20),
    )


async def rate_limit_face_login(request: Request) -> None:
    await enforce_rate_limit(
        request,
        "face_login",
        limit=int(getattr(settings, "RATE_LIMIT_FACE_LOGIN_PER_MINUTE", 8) or 8),
    )


async def rate_limit_identify(request: Request) -> None:
    await enforce_rate_limit(
        request,
        "identify",
        limit=int(getattr(settings, "RATE_LIMIT_IDENTIFY_PER_MINUTE", 120) or 120),
    )


async def rate_limit_import(request: Request) -> None:
    await enforce_rate_limit(
        request,
        "import",
        limit=int(getattr(settings, "RATE_LIMIT_IMPORT_PER_MINUTE", 10) or 10),
    )
