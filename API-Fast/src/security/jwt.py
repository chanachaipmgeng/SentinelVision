"""JWT issue/verify. SECRET_KEY comes from settings (env), never hardcoded."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
from typing import Any, Optional

import jwt
from fastapi import HTTPException, status

from ..config.settings import settings

ALGORITHM = "HS256"
WEAK_SECRETS = {
    "",
    "change-me-in-production",
    "changeme",
    "secret",
}


def assert_secret_configured() -> None:
    if not settings.AUTH_FAIL_FAST:
        return
    key = (settings.SECRET_KEY or "").strip()
    if key in WEAK_SECRETS or len(key) < 32:
        raise RuntimeError(
            "SECRET_KEY must be set to a random string of at least 32 characters"
        )


def _now() -> datetime:
    return datetime.now(timezone.utc)


def hash_kiosk_token(token: str) -> str:
    return hashlib.sha256((token or "").strip().encode("utf-8")).hexdigest()


def create_token(member_id: str, username: str, *, typ: str, expires: timedelta) -> str:
    payload = {
        "memberId": str(member_id),
        "username": username,
        "typ": typ,
        "exp": _now() + expires,
        "iat": _now(),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(member_id: str, username: str) -> str:
    return create_token(
        member_id,
        username,
        typ="access",
        expires=timedelta(minutes=max(5, int(settings.ACCESS_TOKEN_EXPIRE_MINUTES))),
    )


def create_refresh_token(member_id: str, username: str) -> str:
    return create_token(
        member_id,
        username,
        typ="refresh",
        expires=timedelta(days=max(1, int(settings.REFRESH_TOKEN_EXPIRE_DAYS))),
    )


def create_kiosk_token(
    device_id: str,
    company_id: str,
    *,
    location_id: Optional[str] = None,
    expires_days: Optional[int] = None,
) -> str:
    days = max(1, int(expires_days or getattr(settings, "KIOSK_TOKEN_EXPIRE_DAYS", 365)))
    payload: dict[str, Any] = {
        "deviceId": str(device_id),
        "companyId": str(company_id),
        "typ": "kiosk",
        "exp": _now() + timedelta(days=days),
        "iat": _now(),
    }
    if location_id:
        payload["locationId"] = str(location_id)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str, *, expected_typ: Optional[str] = "access") -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    typ = payload.get("typ") or "access"
    if expected_typ and typ != expected_typ:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong token type")
    if typ == "kiosk":
        if not payload.get("deviceId") or not payload.get("companyId"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid kiosk token")
        return payload
    if not payload.get("memberId"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return payload
