"""httpOnly refresh cookie + double-submit CSRF helpers (Phase E4)."""
from __future__ import annotations

import secrets
from typing import Optional

from fastapi import Request, Response

from ..config.settings import settings
from .jwt import refresh_token_ttl


def refresh_cookie_name() -> str:
    return (settings.AUTH_REFRESH_COOKIE_NAME or "dpu_refresh").strip() or "dpu_refresh"


def csrf_cookie_name() -> str:
    return (settings.AUTH_CSRF_COOKIE_NAME or "dpu_csrf").strip() or "dpu_csrf"


def csrf_header_name() -> str:
    return (settings.AUTH_CSRF_HEADER or "X-CSRF-Token").strip() or "X-CSRF-Token"


def cookie_secure() -> bool:
    if settings.AUTH_COOKIE_SECURE is not None:
        return bool(settings.AUTH_COOKIE_SECURE)
    return (settings.APP_ENV or "").strip().lower() not in {"development", "dev", "test", "local"}


def cookie_samesite() -> str:
    raw = (settings.AUTH_COOKIE_SAMESITE or "lax").strip().lower()
    return raw if raw in {"lax", "strict", "none"} else "lax"


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def read_refresh_cookie(request: Request) -> Optional[str]:
    raw = request.cookies.get(refresh_cookie_name())
    return (raw or "").strip() or None


def read_csrf_cookie(request: Request) -> Optional[str]:
    raw = request.cookies.get(csrf_cookie_name())
    return (raw or "").strip() or None


def read_csrf_header(request: Request) -> Optional[str]:
    raw = request.headers.get(csrf_header_name()) or request.headers.get(csrf_header_name().lower())
    return (raw or "").strip() or None


def csrf_ok(request: Request) -> bool:
    """Double-submit: cookie value must equal the CSRF header."""
    cookie = read_csrf_cookie(request)
    header = read_csrf_header(request)
    if not cookie or not header:
        return False
    return secrets.compare_digest(cookie, header)


def set_auth_cookies(response: Response, refresh_token: str, *, csrf: Optional[str] = None) -> str:
    """Attach httpOnly refresh + readable CSRF cookies. Returns the CSRF value used."""
    csrf_value = csrf or new_csrf_token()
    secure = cookie_secure()
    samesite = cookie_samesite()
    max_age = int(refresh_token_ttl().total_seconds())
    response.set_cookie(
        key=refresh_cookie_name(),
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite=samesite,
        max_age=max_age,
        path="/",
    )
    response.set_cookie(
        key=csrf_cookie_name(),
        value=csrf_value,
        httponly=False,
        secure=secure,
        samesite=samesite,
        max_age=max_age,
        path="/",
    )
    return csrf_value


def clear_auth_cookies(response: Response) -> None:
    secure = cookie_secure()
    samesite = cookie_samesite()
    for name in (refresh_cookie_name(), csrf_cookie_name()):
        response.set_cookie(
            key=name,
            value="",
            httponly=name == refresh_cookie_name(),
            secure=secure,
            samesite=samesite,
            max_age=0,
            path="/",
        )
