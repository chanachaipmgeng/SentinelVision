"""Unit tests for E4 cookie/CSRF helpers (no database)."""
from __future__ import annotations

import secrets

from starlette.requests import Request
from starlette.responses import Response

from src.security import auth_cookies as cookies
from src.security.jwt import (
    TYP_PASSWORD_RESET,
    create_password_reset_token,
    decode_token,
)


def _request(*, cookie: str | None = None, header: str | None = None) -> Request:
    header_items = []
    if cookie:
        header_items.append((b"cookie", cookie.encode()))
    if header:
        header_items.append((cookies.csrf_header_name().lower().encode(), header.encode()))
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/auth/refresh",
        "query_string": b"",
        "headers": header_items,
        "client": ("127.0.0.1", 1234),
    }
    return Request(scope)


def test_set_and_clear_auth_cookies(monkeypatch):
    monkeypatch.setattr(cookies.settings, "AUTH_COOKIE_SECURE", False)
    monkeypatch.setattr(cookies.settings, "APP_ENV", "test")
    response = Response()
    csrf = cookies.set_auth_cookies(response, "refresh-token-value")
    raw = response.headers.getlist("set-cookie")
    joined = "\n".join(raw)
    assert cookies.refresh_cookie_name() in joined
    assert "HttpOnly" in joined
    assert cookies.csrf_cookie_name() in joined
    assert csrf in joined
    assert "refresh-token-value" in joined

    cookies.clear_auth_cookies(response)
    cleared = "\n".join(response.headers.getlist("set-cookie"))
    assert "Max-Age=0" in cleared or "max-age=0" in cleared.lower()


def test_csrf_double_submit_ok_and_fail():
    token = secrets.token_urlsafe(16)
    assert cookies.csrf_ok(
        _request(
            cookie=f"{cookies.csrf_cookie_name()}={token}",
            header=token,
        )
    )
    assert not cookies.csrf_ok(_request(cookie=f"{cookies.csrf_cookie_name()}={token}"))
    assert not cookies.csrf_ok(
        _request(cookie=f"{cookies.csrf_cookie_name()}={token}", header="nope")
    )
    assert not cookies.csrf_ok(_request())


def test_password_reset_token_round_trip():
    raw = create_password_reset_token(
        "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "alice",
        "Alice@Example.COM",
    )
    payload = decode_token(raw, expected_typ=TYP_PASSWORD_RESET)
    assert payload["username"] == "alice"
    assert payload["email"] == "alice@example.com"
    assert payload["typ"] == TYP_PASSWORD_RESET
