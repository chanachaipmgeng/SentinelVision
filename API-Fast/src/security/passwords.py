"""Temporary passwords and login lockout."""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

import bcrypt

from ..config.settings import settings


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def generate_temp_password() -> str:
    # urlsafe, at least 10 chars, mixed enough for a first-login secret
    return secrets.token_urlsafe(9)


def apply_temp_password(member) -> str:
    plain = generate_temp_password()
    member.hash_password(plain)
    member.mustChangePassword = True
    member.failedLoginCount = 0
    member.lockedUntil = None
    return plain


def assert_not_locked(member) -> None:
    from fastapi import HTTPException

    locked = getattr(member, "lockedUntil", None)
    if locked is None:
        return
    now = datetime.now(timezone.utc)
    if locked.tzinfo is None:
        locked = locked.replace(tzinfo=timezone.utc)
    if locked > now:
        raise HTTPException(status_code=423, detail="Account locked. Try again later.")


def register_failure(member) -> None:
    count = int(getattr(member, "failedLoginCount", 0) or 0) + 1
    member.failedLoginCount = count
    if count >= int(settings.MAX_FAILED_LOGINS):
        member.lockedUntil = datetime.now(timezone.utc) + timedelta(minutes=int(settings.LOCKOUT_MINUTES))
        member.failedLoginCount = 0


def register_success(member) -> None:
    member.failedLoginCount = 0
    member.lockedUntil = None
