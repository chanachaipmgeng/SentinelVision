"""One-time kiosk pairing codes.

An admin provisions a ``kiosk_device`` and receives a short code (``ABCD-EFGH``) that is valid
for ``KIOSK_PAIRING_CODE_TTL_MINUTES``. The kiosk posts it once to ``/auth/kiosk/pair`` and gets
a device-scoped token pair; only the sha256 of the code is stored.
"""
from __future__ import annotations

import hashlib
import secrets
import time
from collections import deque
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status

from ..config.settings import settings

# No 0/O/1/I to keep the code easy to type on a tablet.
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 8


def generate_pairing_code() -> str:
    raw = "".join(secrets.choice(_ALPHABET) for _ in range(CODE_LENGTH))
    return f"{raw[:4]}-{raw[4:]}"


def normalize_pairing_code(code: str) -> str:
    return "".join(ch for ch in (code or "").upper() if ch.isalnum())


def hash_pairing_code(code: str) -> str:
    return hashlib.sha256(normalize_pairing_code(code).encode("utf-8")).hexdigest()


def pairing_code_expiry(now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    return now + timedelta(minutes=max(1, int(settings.KIOSK_PAIRING_CODE_TTL_MINUTES)))


_attempts: dict[str, deque[float]] = {}
_ATTEMPT_KEYS_MAX = 5000


def reset_pair_rate_limit() -> None:
    _attempts.clear()


def assert_pair_attempt_allowed(client_key: str, *, now: float | None = None) -> None:
    """Fixed 60s sliding window per client IP; codes are short so brute force must be slow."""
    now = time.time() if now is None else now
    limit = max(1, int(settings.KIOSK_PAIR_MAX_ATTEMPTS_PER_MINUTE))
    window = _attempts.setdefault(client_key or "unknown", deque())
    while window and now - window[0] >= 60:
        window.popleft()
    if len(window) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many pairing attempts; try again in a minute",
        )
    window.append(now)
    if len(_attempts) > _ATTEMPT_KEYS_MAX:
        for key in [k for k, q in _attempts.items() if not q or now - q[-1] >= 60]:
            _attempts.pop(key, None)
