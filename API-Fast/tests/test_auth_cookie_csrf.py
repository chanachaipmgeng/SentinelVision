"""E4: httpOnly refresh cookie + double-submit CSRF + reset-password paths."""
from __future__ import annotations

import asyncio
import os
import uuid

import pytest
from fastapi import FastAPI
from starlette.requests import Request

requires_db = pytest.mark.skipif(
    not os.environ.get("DPU_TEST_DB_READY"),
    reason="No test database: set TEST_DATABASE_URL or `pip install pgserver`",
)


def _run(coro):
    async def wrapper():
        from src.config.database import engine

        try:
            return await coro
        finally:
            pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
            if pending:
                await asyncio.wait(pending, timeout=2)
            await engine.dispose()

    return asyncio.run(wrapper())


@pytest.fixture(scope="module")
def db_env():
    if not os.environ.get("DPU_TEST_DB_READY"):
        pytest.skip("No test database: set TEST_DATABASE_URL or `pip install pgserver`")

    async def _reset_pool():
        from src.config.database import engine

        await engine.dispose(close=False)

    asyncio.run(_reset_pool())
    yield


@pytest.fixture
def app(db_env, monkeypatch):
    import src.config.settings as settings_mod
    from src.routes import auth_routes
    from src.security.middleware import AuthzMiddleware
    from src.services import token_revocation_service as revocation

    monkeypatch.setattr(settings_mod.settings, "AUTH_FAIL_FAST", False)
    monkeypatch.setattr(settings_mod.settings, "APP_ENV", "test")
    monkeypatch.setattr(settings_mod.settings, "AUTH_COOKIE_SECURE", False)
    monkeypatch.setattr(settings_mod.settings, "AUTH_EXPOSE_RESET_TOKEN", True)
    monkeypatch.setattr(settings_mod.settings, "AUTH_REVOCATION_CACHE_SECONDS", 30)
    revocation.reset_cache()

    test_app = FastAPI()
    test_app.add_middleware(AuthzMiddleware)
    test_app.include_router(auth_routes.router, prefix="/auth")

    @test_app.get("/system/whoami")
    async def whoami(request: Request):
        return {"memberId": str(request.state.member.memberId)}

    return test_app


@pytest.fixture
def seed(db_env):
    from src.config.database import async_session
    from src.models.member import Member, RoleType, StatusType
    from src.security.passwords import hash_password

    suffix = uuid.uuid4().hex[:8]
    email = f"cookie_{suffix}@example.com"
    data = {
        "username": f"cookie_{suffix}",
        "password": "Str0ngPassw0rd!",
        "email": email,
    }

    async def _seed():
        async with async_session() as db:
            db.add(
                Member(
                    memberId=uuid.uuid4(),
                    username=data["username"],
                    passwordHash=hash_password(data["password"]),
                    email=email,
                    role=RoleType.ADMIN_SYSTEM,
                    status=StatusType.ENABLE,
                )
            )
            await db.commit()

    _run(_seed())
    yield data

    async def _cleanup():
        from sqlalchemy import text

        async with async_session() as db:
            await db.execute(text("DELETE FROM member WHERE username = :u"), {"u": data["username"]})
            await db.commit()

    _run(_cleanup())


def _client(app):
    import httpx

    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def _login_cookie(client, seed):
    from src.security.auth_cookies import csrf_cookie_name, refresh_cookie_name

    res = await client.post(
        "/auth/login",
        json={"username": seed["username"], "password": seed["password"]},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body.get("accessToken")
    assert body.get("csrfToken")
    assert refresh_cookie_name() in res.cookies
    assert csrf_cookie_name() in res.cookies
    return body, res.cookies


@requires_db
def test_login_sets_httponly_refresh_and_csrf_cookies(app, seed):
    from src.security.auth_cookies import csrf_cookie_name, refresh_cookie_name

    async def flow():
        async with _client(app) as c:
            body, cookies = await _login_cookie(c, seed)
            assert body.get("refreshToken")
            assert cookies.get(refresh_cookie_name())
            assert cookies.get(csrf_cookie_name()) == body["csrfToken"]

    _run(flow())


@requires_db
def test_cookie_refresh_requires_csrf_header(app, seed):
    from src.security.auth_cookies import csrf_cookie_name, csrf_header_name, refresh_cookie_name

    async def flow():
        async with _client(app) as c:
            body, cookies = await _login_cookie(c, seed)
            c.cookies.set(refresh_cookie_name(), cookies.get(refresh_cookie_name()))
            c.cookies.set(csrf_cookie_name(), cookies.get(csrf_cookie_name()))

            missing = await c.post("/auth/refresh-token", json={})
            assert missing.status_code == 403
            assert "CSRF" in missing.json()["detail"]

            ok = await c.post(
                "/auth/refresh-token",
                json={},
                headers={csrf_header_name(): body["csrfToken"]},
            )
            assert ok.status_code == 200, ok.text
            rotated = ok.json()
            assert rotated["accessToken"] != body["accessToken"]
            assert rotated.get("csrfToken")
            assert refresh_cookie_name() in ok.cookies

            body_ok = await c.post(
                "/auth/refresh-token",
                json={"refreshToken": rotated["refreshToken"]},
            )
            assert body_ok.status_code == 200

    _run(flow())


@requires_db
def test_cookie_logout_clears_session(app, seed):
    from src.security.auth_cookies import csrf_cookie_name, csrf_header_name, refresh_cookie_name

    async def flow():
        async with _client(app) as c:
            body, cookies = await _login_cookie(c, seed)
            access = body["accessToken"]
            c.cookies.set(refresh_cookie_name(), cookies.get(refresh_cookie_name()))
            c.cookies.set(csrf_cookie_name(), cookies.get(csrf_cookie_name()))
            res = await c.post(
                "/auth/logout",
                json={},
                headers={
                    "Authorization": f"Bearer {access}",
                    csrf_header_name(): body["csrfToken"],
                },
            )
            assert res.status_code == 200
            denied = await c.get(
                "/system/whoami",
                headers={"Authorization": f"Bearer {access}"},
            )
            assert denied.status_code == 401

    _run(flow())


@requires_db
def test_reset_password_flow_with_exposed_token(app, seed):
    from src.security.jwt import decode_token

    async def flow():
        async with _client(app) as c:
            ghost = await c.post("/auth/send-reset-password", json={"email": "nobody@example.com"})
            assert ghost.status_code == 200
            assert ghost.json()["ok"] is True
            assert "resetToken" not in ghost.json()

            sent = await c.post("/auth/send-reset-password", json={"email": seed["email"]})
            assert sent.status_code == 200, sent.text
            token = sent.json().get("resetToken")
            assert token
            assert decode_token(token, expected_typ="password_reset")["memberId"]

            bad = await c.post("/auth/reset-password", json={"token": token, "newPassword": "short"})
            assert bad.status_code == 400

            new_pw = f"ResetOk-{uuid.uuid4().hex[:8]}!"
            ok = await c.post(
                "/auth/reset-password",
                json={"token": token, "newPassword": new_pw},
            )
            assert ok.status_code == 200, ok.text

            login = await c.post(
                "/auth/login",
                json={"username": seed["username"], "password": new_pw},
            )
            assert login.status_code == 200, login.text

    _run(flow())
