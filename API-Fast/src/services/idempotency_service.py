"""Idempotency-Key replay for punch create and employee import (Phase D6).

Stores the completed response JSON (and status) under
``(scope, company_id, key)`` for ``IDEMPOTENCY_TTL_SECONDS``. Redis when available;
in-process memory otherwise.
"""
from __future__ import annotations

import json
import time
from threading import Lock
from typing import Any, Optional, Tuple

from fastapi import HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from ..config.settings import settings
from .redis_client import get_redis

_memory: dict[str, Tuple[float, int, Any]] = {}
_lock = Lock()


def _ttl() -> int:
    return max(60, int(getattr(settings, "IDEMPOTENCY_TTL_SECONDS", 86400) or 86400))


def _storage_key(scope: str, company_id: str, key: str) -> str:
    return f"dpu:idem:{scope}:{company_id}:{key}"


def extract_idempotency_key(request: Request) -> Optional[str]:
    raw = (request.headers.get("idempotency-key") or request.headers.get("Idempotency-Key") or "").strip()
    if not raw:
        return None
    if len(raw) > 128:
        raise HTTPException(status_code=400, detail="Idempotency-Key too long (max 128)")
    return raw


async def get_cached_response(
    scope: str, company_id: str, key: str
) -> Optional[Tuple[int, Any]]:
    full = _storage_key(scope, str(company_id), key)
    redis = get_redis()
    if redis is not None:
        try:
            raw = await redis.get(full)
            if raw:
                payload = json.loads(raw)
                return int(payload["status"]), payload["body"]
        except Exception:
            pass
    now = time.time()
    with _lock:
        hit = _memory.get(full)
        if not hit:
            return None
        expires, status, body = hit
        if expires < now:
            _memory.pop(full, None)
            return None
        return status, body


async def store_response(
    scope: str, company_id: str, key: str, *, status_code: int, body: Any
) -> None:
    full = _storage_key(scope, str(company_id), key)
    encoded = jsonable_encoder(body)
    ttl = _ttl()
    redis = get_redis()
    if redis is not None:
        try:
            await redis.set(
                full,
                json.dumps({"status": int(status_code), "body": encoded}),
                ex=ttl,
            )
            return
        except Exception:
            pass
    with _lock:
        _memory[full] = (time.time() + ttl, int(status_code), encoded)


def reset_idempotency_for_tests() -> None:
    with _lock:
        _memory.clear()


async def idempotent_json(
    request: Request,
    *,
    scope: str,
    company_id: str,
    compute,
):
    """Run ``compute`` once per Idempotency-Key; replay prior JSON on retries.

    ``compute`` is an async callable returning a JSON-serializable body (or a
    response model). When the header is absent, ``compute`` runs normally.
    """
    key = extract_idempotency_key(request)
    if not key:
        return await compute()
    cached = await get_cached_response(scope, company_id, key)
    if cached is not None:
        status, body = cached
        return JSONResponse(content=body, status_code=status, headers={"Idempotency-Replayed": "true"})
    result = await compute()
    if isinstance(result, JSONResponse):
        # Unusual — leave as-is without caching opaque responses.
        return result
    await store_response(scope, company_id, key, status_code=200, body=result)
    return result
