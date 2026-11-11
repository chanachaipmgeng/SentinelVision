"""JWT issue/verify. SECRET_KEY comes from settings (env), never hardcoded.

Every token carries ``jti`` (unique id), ``typ`` (``access`` / ``refresh`` / ``kiosk`` /
``kiosk_refresh``) and ``fam`` (session family). ``fam`` is shared by the access + refresh pair
issued together and by every pair produced by rotating that refresh token, so revoking the family
invalidates the whole session (logout, refresh-token reuse, device revoke).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import secrets
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

TYP_ACCESS = "access"
TYP_REFRESH = "refresh"
TYP_KIOSK = "kiosk"
TYP_KIOSK_REFRESH = "kiosk_refresh"
TYP_PASSWORD_RESET = "password_reset"
MEMBER_TYPES = (TYP_ACCESS, TYP_REFRESH)
KIOSK_TYPES = (TYP_KIOSK, TYP_KIOSK_REFRESH)


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


def new_jti() -> str:
    return secrets.token_hex(16)


def new_family_id() -> str:
    return secrets.token_hex(16)


def hash_kiosk_token(token: str) -> str:
    return hashlib.sha256((token or "").strip().encode("utf-8")).hexdigest()


def _encode(payload: dict[str, Any], *, expires: timedelta, family: Optional[str]) -> str:
    now = _now()
    payload = {
        **payload,
        "jti": new_jti(),
        "fam": family or new_family_id(),
        "exp": now + expires,
        "iat": now,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_token(
    member_id: str,
    username: str,
    *,
    typ: str,
    expires: timedelta,
    family: Optional[str] = None,
) -> str:
    return _encode(
        {"memberId": str(member_id), "username": username, "typ": typ},
        expires=expires,
        family=family,
    )


def access_token_ttl() -> timedelta:
    return timedelta(minutes=max(5, int(settings.ACCESS_TOKEN_EXPIRE_MINUTES)))


def refresh_token_ttl() -> timedelta:
    return timedelta(days=max(1, int(settings.REFRESH_TOKEN_EXPIRE_DAYS)))


def create_access_token(member_id: str, username: str, *, family: Optional[str] = None) -> str:
    return create_token(member_id, username, typ=TYP_ACCESS, expires=access_token_ttl(), family=family)


def create_refresh_token(member_id: str, username: str, *, family: Optional[str] = None) -> str:
    return create_token(member_id, username, typ=TYP_REFRESH, expires=refresh_token_ttl(), family=family)


def create_token_pair(member_id: str, username: str, *, family: Optional[str] = None) -> tuple[str, str]:
    """Access + refresh token sharing one ``fam`` so they can be revoked together."""
    fam = family or new_family_id()
    return (
        create_access_token(member_id, username, family=fam),
        create_refresh_token(member_id, username, family=fam),
    )


def password_reset_ttl() -> timedelta:
    return timedelta(minutes=max(5, int(settings.AUTH_PASSWORD_RESET_EXPIRE_MINUTES)))


def create_password_reset_token(member_id: str, username: str, email: str) -> str:
    """Short-lived, single-purpose JWT for the reset-password form (not a session)."""
    return _encode(
        {
            "memberId": str(member_id),
            "username": username,
            "email": (email or "").strip().lower(),
            "typ": TYP_PASSWORD_RESET,
        },
        expires=password_reset_ttl(),
        family=new_family_id(),
    )


def kiosk_token_ttl() -> timedelta:
    return timedelta(hours=max(1, int(settings.KIOSK_TOKEN_EXPIRE_HOURS)))


def kiosk_refresh_ttl() -> timedelta:
    return timedelta(days=max(1, int(settings.KIOSK_REFRESH_EXPIRE_DAYS)))


def create_kiosk_token(
    device_id: str,
    company_id: str,
    *,
    location_id: Optional[str] = None,
    expires_days: Optional[int] = None,
    expires: Optional[timedelta] = None,
    family: Optional[str] = None,
    typ: str = TYP_KIOSK,
) -> str:
    """Device-scoped token. Default TTL is ``KIOSK_TOKEN_EXPIRE_HOURS`` (refreshable via
    ``/auth/kiosk/refresh``); ``expires_days`` is kept for callers that still pass days."""
    if expires is None:
        expires = timedelta(days=max(1, int(expires_days))) if expires_days else kiosk_token_ttl()
    payload: dict[str, Any] = {
        "deviceId": str(device_id),
        "companyId": str(company_id),
        "typ": typ,
    }
    if location_id:
        payload["locationId"] = str(location_id)
    return _encode(payload, expires=expires, family=family)


def create_kiosk_token_pair(
    device_id: str,
    company_id: str,
    *,
    location_id: Optional[str] = None,
    family: Optional[str] = None,
) -> tuple[str, str]:
    fam = family or new_family_id()
    access = create_kiosk_token(device_id, company_id, location_id=location_id, family=fam)
    refresh = create_kiosk_token(
        device_id,
        company_id,
        location_id=location_id,
        family=fam,
        typ=TYP_KIOSK_REFRESH,
        expires=kiosk_refresh_ttl(),
    )
    return access, refresh


def token_exp_datetime(payload: dict[str, Any]) -> datetime:
    exp = payload.get("exp")
    if isinstance(exp, datetime):
        return exp if exp.tzinfo else exp.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromtimestamp(int(exp or 0), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return _now()


def decode_token(token: str, *, expected_typ: Optional[str] = "access") -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired") from None
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from None
    typ = payload.get("typ") or TYP_ACCESS
    if expected_typ and typ != expected_typ:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong token type")
    if typ in KIOSK_TYPES:
        if not payload.get("deviceId") or not payload.get("companyId"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid kiosk token")
        return payload
    if not payload.get("memberId"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return payload
