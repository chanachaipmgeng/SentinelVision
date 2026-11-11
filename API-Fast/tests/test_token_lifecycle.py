"""A5: token lifecycle — jti/typ claims, revocation, refresh rotation + reuse detection, kiosk
pairing codes, and the removal of `?token=`.

Unit tests run everywhere. The integration tests need the PostgreSQL that tests/conftest.py
prepares (``TEST_DATABASE_URL`` or the embedded ``pgserver``) and is migrated to Alembic head.
"""
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from starlette.requests import Request

import src.config.settings as settings_mod
from src.security import kiosk_pairing
from src.security.jwt import (
    create_kiosk_token_pair,
    create_token_pair,
    decode_token,
)
from src.security.middleware import _token_from
from src.services import token_revocation_service as revocation

requires_db = pytest.mark.skipif(
    not os.environ.get("DPU_TEST_DB_READY"),
    reason="No test database: set TEST_DATABASE_URL or `pip install pgserver`",
)


def _request(path: str, query: str = "", headers: dict | None = None) -> Request:
    raw_headers = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "query_string": query.encode(),
        "headers": raw_headers,
        "client": ("127.0.0.1", 1234),
    }
    return Request(scope)


# ---------------------------------------------------------------------------
# Unit: claims, query-token extraction, pairing code helpers
# ---------------------------------------------------------------------------
def test_member_tokens_carry_jti_typ_and_shared_family():
    access, refresh = create_token_pair("m-1", "alice")
    a = decode_token(access, expected_typ="access")
    r = decode_token(refresh, expected_typ="refresh")
    assert a["typ"] == "access" and r["typ"] == "refresh"
    assert len(a["jti"]) == 32 and len(r["jti"]) == 32 and a["jti"] != r["jti"]
    assert a["fam"] == r["fam"]
    with pytest.raises(HTTPException):
        decode_token(refresh, expected_typ="access")


def test_kiosk_token_pair_claims_and_short_ttl(monkeypatch):
    monkeypatch.setattr(settings_mod.settings, "KIOSK_TOKEN_EXPIRE_HOURS", 12)
    access, refresh = create_kiosk_token_pair("dev-1", "comp-1", location_id="loc-1")
    a = decode_token(access, expected_typ="kiosk")
    r = decode_token(refresh, expected_typ="kiosk_refresh")
    assert a["deviceId"] == "dev-1" and a["companyId"] == "comp-1" and a["locationId"] == "loc-1"
    assert a["fam"] == r["fam"] and a["jti"] != r["jti"]
    ttl = a["exp"] - a["iat"]
    assert ttl <= 12 * 3600 + 5
    with pytest.raises(HTTPException):
        decode_token(refresh, expected_typ="kiosk")


def test_query_token_rejected_by_default(monkeypatch):
    monkeypatch.setattr(settings_mod.settings, "AUTH_ALLOW_QUERY_TOKEN", False)
    assert _token_from(_request("/system/whoami", "token=abc.def.ghi")) == ""
    assert _token_from(_request("/system/whoami", headers={"Authorization": "Bearer hdr"})) == "hdr"


def test_query_token_only_behind_deprecation_flag(monkeypatch):
    monkeypatch.setattr(settings_mod.settings, "AUTH_ALLOW_QUERY_TOKEN", True)
    assert _token_from(_request("/images/x.jpg", "token=legacy")) == "legacy"
    # header still wins over the query string
    assert _token_from(_request("/images/x.jpg", "token=legacy", {"Authorization": "Bearer hdr"})) == "hdr"


def test_pairing_code_format_normalize_and_hash():
    code = kiosk_pairing.generate_pairing_code()
    assert len(code) == 9 and code[4] == "-"
    assert not any(ch in code for ch in "01OI")
    typed = f" {code.lower()} "
    assert kiosk_pairing.normalize_pairing_code(typed) == code.replace("-", "")
    assert kiosk_pairing.hash_pairing_code(typed) == kiosk_pairing.hash_pairing_code(code)
    assert kiosk_pairing.hash_pairing_code(code) != kiosk_pairing.hash_pairing_code(kiosk_pairing.generate_pairing_code())


def test_pair_attempt_rate_limit(monkeypatch):
    from fastapi import HTTPException

    monkeypatch.setattr(settings_mod.settings, "KIOSK_PAIR_MAX_ATTEMPTS_PER_MINUTE", 3)
    kiosk_pairing.reset_pair_rate_limit()
    for _ in range(3):
        kiosk_pairing.assert_pair_attempt_allowed("10.0.0.1", now=1000.0)
    with pytest.raises(HTTPException) as exc:
        kiosk_pairing.assert_pair_attempt_allowed("10.0.0.1", now=1001.0)
    assert exc.value.status_code == 429
    # another client is unaffected, and the window slides
    kiosk_pairing.assert_pair_attempt_allowed("10.0.0.2", now=1001.0)
    kiosk_pairing.assert_pair_attempt_allowed("10.0.0.1", now=1061.0)
    kiosk_pairing.reset_pair_rate_limit()


def test_legacy_token_without_jti_is_not_treated_as_revoked():
    revocation.reset_cache()
    assert asyncio.run(revocation.is_token_revoked({"memberId": "x", "typ": "access"})) is False


# ---------------------------------------------------------------------------
# Integration (PostgreSQL): revocation, rotation, reuse, pairing, ?token= end-to-end
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def db_env():
    """Schema comes from Alembic (conftest); only drop pooled connections from other loops."""
    if not os.environ.get("DPU_TEST_DB_READY"):
        pytest.skip("No test database: set TEST_DATABASE_URL or `pip install pgserver`")

    async def _reset_pool():
        from src.config.database import engine

        await engine.dispose(close=False)

    asyncio.run(_reset_pool())
    yield


@pytest.fixture
def app(db_env, monkeypatch):
    from fastapi import FastAPI

    from src.routes import auth_routes, hr_routes
    from src.security.middleware import AuthzMiddleware

    monkeypatch.setattr(settings_mod.settings, "AUTH_ALLOW_QUERY_TOKEN", False)
    monkeypatch.setattr(settings_mod.settings, "AUTH_REVOCATION_CACHE_SECONDS", 30)
    revocation.reset_cache()
    kiosk_pairing.reset_pair_rate_limit()

    test_app = FastAPI()
    test_app.add_middleware(AuthzMiddleware)
    test_app.include_router(auth_routes.router, prefix="/auth")
    test_app.include_router(hr_routes.router, prefix="/hr")

    @test_app.get("/system/whoami")
    async def whoami(request: Request):
        return {"memberId": str(request.state.member.memberId)}

    @test_app.get("/system/tts-settings")
    async def tts(request: Request):
        return {"kioskCompanyId": str(getattr(request.state, "kiosk_company_id", ""))}

    return test_app


@pytest.fixture
def seed(db_env):
    """System admin member + one company (system admins pass assert_company_access)."""
    from src.config.database import async_session
    from src.models.company import Company
    from src.models.member import Member, RoleType, StatusType
    from src.security.passwords import hash_password

    suffix = uuid.uuid4().hex[:8]
    data = {"username": f"admin_{suffix}", "password": "Str0ngPassw0rd!", "companyId": uuid.uuid4()}

    async def _seed():
        async with async_session() as db:
            db.add(
                Member(
                    memberId=uuid.uuid4(),
                    username=data["username"],
                    passwordHash=hash_password(data["password"]),
                    email=f"{data['username']}@example.com",
                    role=RoleType.ADMIN_SYSTEM,
                    status=StatusType.ENABLE,
                )
            )
            db.add(
                Company(
                    companyId=data["companyId"],
                    companyName=f"Co {suffix}",
                    companyCode=f"CO{suffix}",
                    companyInfo="test",
                    address="test",
                )
            )
            await db.commit()

    _run(_seed())
    yield data

    # Remove what this module created so a reused TEST_DATABASE_URL does not accumulate companies
    # without picture/ownerName (the /companys listing in test_authz_matrix validates every row).
    async def _cleanup():
        from sqlalchemy import text

        cid = {"cid": str(data["companyId"])}
        async with async_session() as db:
            for tbl in ("kiosk_device", "company_employee", "department", "position", "company_location"):
                await db.execute(text(f'DELETE FROM "{tbl}" WHERE "companyId" = :cid'), cid)
            await db.execute(text('DELETE FROM company WHERE "companyId" = :cid'), cid)
            await db.execute(text("DELETE FROM member WHERE username = :u"), {"u": data["username"]})
            await db.commit()

    _run(_cleanup())


def _client(app):
    import httpx

    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


def _run(coro):
    """Run ``coro`` on a fresh loop, let fire-and-forget audit tasks finish, then drop pooled
    asyncpg connections (they are bound to the loop that created them)."""

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


async def _login(client, seed):
    res = await client.post("/auth/login", json={"username": seed["username"], "password": seed["password"]})
    assert res.status_code == 200, res.text
    body = res.json()
    return body["accessToken"], body["refreshToken"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@requires_db
def test_login_tokens_have_jti_and_query_token_is_rejected_end_to_end(app, seed):
    async def flow():
        async with _client(app) as c:
            access, refresh = await _login(c, seed)
            assert decode_token(access)["jti"]
            ok = await c.get("/system/whoami", headers=_auth(access))
            assert ok.status_code == 200
            via_query = await c.get("/system/whoami", params={"token": access})
            assert via_query.status_code == 401
            assert via_query.json()["detail"] == "Authorization required"

    _run(flow())


@requires_db
def test_logout_revokes_access_and_refresh(app, seed):
    async def flow():
        async with _client(app) as c:
            access, refresh = await _login(c, seed)
            res = await c.post("/auth/logout", json={"refreshToken": refresh}, headers=_auth(access))
            assert res.status_code == 200
            assert res.json()["familyRevoked"] is True
            denied = await c.get("/system/whoami", headers=_auth(access))
            assert denied.status_code == 401
            assert denied.json()["detail"] == "Token has been revoked"
            refresh_denied = await c.post("/auth/refresh", json={"refreshToken": refresh})
            assert refresh_denied.status_code == 401
            # logout without any token is a 401, with only a refresh token is fine
            assert (await c.post("/auth/logout", json={})).status_code == 401
            access2, refresh2 = await _login(c, seed)
            only_refresh = await c.post("/auth/logout", json={"refreshToken": refresh2})
            assert only_refresh.status_code == 200
            assert (await c.get("/system/whoami", headers=_auth(access2))).status_code == 401

    _run(flow())


@requires_db
def test_refresh_rotates_and_reuse_revokes_family(app, seed):
    async def flow():
        async with _client(app) as c:
            access1, refresh1 = await _login(c, seed)
            fam = decode_token(refresh1, expected_typ="refresh")["fam"]

            rotated = await c.post("/auth/refresh-token", json={"refreshToken": refresh1})
            assert rotated.status_code == 200
            access2, refresh2 = rotated.json()["accessToken"], rotated.json()["refreshToken"]
            assert refresh2 != refresh1
            assert decode_token(refresh2, expected_typ="refresh")["fam"] == fam
            assert (await c.get("/system/whoami", headers=_auth(access2))).status_code == 200

            # Replaying the rotated refresh token = theft signal → whole family dies.
            reuse = await c.post("/auth/refresh", json={"refreshToken": refresh1})
            assert reuse.status_code == 401
            assert "reuse" in reuse.json()["detail"].lower()
            assert (await c.post("/auth/refresh", json={"refreshToken": refresh2})).status_code == 401
            assert (await c.get("/system/whoami", headers=_auth(access2))).status_code == 401
            assert (await c.get("/system/whoami", headers=_auth(access1))).status_code == 401

    _run(flow())


@requires_db
def test_kiosk_pairing_code_single_use_and_device_token_scope(app, seed):
    async def flow():
        async with _client(app) as c:
            access, _ = await _login(c, seed)
            cid = str(seed["companyId"])
            created = await c.post(f"/hr/company/{cid}/kiosk-devices", json={"name": "Gate 1"}, headers=_auth(access))
            assert created.status_code == 200, created.text
            body = created.json()
            code = body["pairingCode"]
            assert "kioskToken" not in body and "kioskUrl" not in body
            assert body["pairingPending"] is True and body["isPaired"] is False

            # wrong code → 401, no device token
            bad = await c.post("/auth/kiosk/pair", json={"pairingCode": "ZZZZ-ZZZZ"})
            assert bad.status_code == 401

            paired = await c.post("/auth/kiosk/pair", json={"pairingCode": code.lower()})
            assert paired.status_code == 200, paired.text
            session = paired.json()
            device_token = session["deviceToken"]
            payload = decode_token(device_token, expected_typ="kiosk")
            assert payload["deviceId"] == body["deviceId"] and payload["companyId"] == cid
            assert session["expiresIn"] <= 12 * 3600

            # single use
            again = await c.post("/auth/kiosk/pair", json={"pairingCode": code})
            assert again.status_code == 401

            # device token works on kiosk-allowed paths only
            allowed = await c.get("/system/tts-settings", headers=_auth(device_token))
            assert allowed.status_code == 200 and allowed.json()["kioskCompanyId"] == cid
            forbidden = await c.get("/system/whoami", headers=_auth(device_token))
            assert forbidden.status_code == 403
            listing = await c.get(f"/hr/company/{cid}/kiosk-devices", headers=_auth(access))
            row = next(r for r in listing.json() if r["deviceId"] == body["deviceId"])
            assert row["isPaired"] is True and row["pairingPending"] is False

            # kiosk refresh rotates; replay of the old refresh kills the device family
            refresh1 = session["deviceRefreshToken"]
            rotated = await c.post("/auth/kiosk/refresh", json={"refreshToken": refresh1})
            assert rotated.status_code == 200, rotated.text
            device_token2 = rotated.json()["deviceToken"]
            assert (await c.get("/system/tts-settings", headers=_auth(device_token2))).status_code == 200
            # previous device token no longer matches the stored hash
            assert (await c.get("/system/tts-settings", headers=_auth(device_token))).status_code == 401
            reuse = await c.post("/auth/kiosk/refresh", json={"refreshToken": refresh1})
            assert reuse.status_code == 401
            assert (await c.get("/system/tts-settings", headers=_auth(device_token2))).status_code == 401
            assert (
                await c.post("/auth/kiosk/refresh", json={"refreshToken": rotated.json()["deviceRefreshToken"]})
            ).status_code == 401

            # re-pair issues a fresh code; admin revoke denies the new token immediately
            reissued = await c.post(
                f"/hr/company/{cid}/kiosk-devices/{body['deviceId']}/pairing-code", headers=_auth(access)
            )
            assert reissued.status_code == 200
            paired2 = await c.post("/auth/kiosk/pair", json={"pairingCode": reissued.json()["pairingCode"]})
            assert paired2.status_code == 200
            device_token3 = paired2.json()["deviceToken"]
            assert (await c.get("/system/tts-settings", headers=_auth(device_token3))).status_code == 200
            revoked = await c.delete(f"/hr/company/{cid}/kiosk-devices/{body['deviceId']}", headers=_auth(access))
            assert revoked.status_code == 200 and revoked.json()["isActive"] is False
            assert (await c.get("/system/tts-settings", headers=_auth(device_token3))).status_code == 401
            assert (
                await c.post("/auth/kiosk/refresh", json={"refreshToken": paired2.json()["deviceRefreshToken"]})
            ).status_code == 401
            # revoked devices cannot be re-paired
            assert (
                await c.post(f"/hr/company/{cid}/kiosk-devices/{body['deviceId']}/pairing-code", headers=_auth(access))
            ).status_code == 409

    _run(flow())


@requires_db
def test_kiosk_pairing_code_expires(app, seed):
    from sqlalchemy import update

    from src.config.database import async_session
    from src.models.hr_schedule import KioskDevice

    async def flow():
        async with _client(app) as c:
            access, _ = await _login(c, seed)
            cid = str(seed["companyId"])
            created = await c.post(f"/hr/company/{cid}/kiosk-devices", json={"name": "Gate 2"}, headers=_auth(access))
            body = created.json()
            async with async_session() as db:
                await db.execute(
                    update(KioskDevice)
                    .where(KioskDevice.deviceId == uuid.UUID(body["deviceId"]))
                    .values(pairingExpiresAt=datetime.now(timezone.utc) - timedelta(seconds=1))
                )
                await db.commit()
            expired = await c.post("/auth/kiosk/pair", json={"pairingCode": body["pairingCode"]})
            assert expired.status_code == 401
            assert "expired" in expired.json()["detail"].lower()
            # the code is consumed on expiry too
            assert (await c.post("/auth/kiosk/pair", json={"pairingCode": body["pairingCode"]})).status_code == 401

    _run(flow())


@requires_db
def test_purge_expired_revocations(db_env):
    from src.config.database import async_session

    async def flow():
        revocation.reset_cache()
        async with async_session() as db:
            await revocation.revoke_jti(db, "old-jti", datetime.now(timezone.utc) - timedelta(minutes=1), reason="logout")
            await revocation.revoke_jti(db, "live-jti", datetime.now(timezone.utc) + timedelta(minutes=5), reason="logout")
            await db.commit()
            removed = await revocation.purge_expired(db)
            assert removed >= 1
            assert await revocation.lookup_revocation(db, "old-jti", None) is None
            assert (await revocation.lookup_revocation(db, "live-jti", None))["reason"] == "logout"
        # cache answers without a DB round-trip once seen
        assert await revocation.is_token_revoked({"jti": "live-jti"}) is True
        assert await revocation.is_token_revoked({"jti": "old-jti"}) is False

    _run(flow())


# ---------------------------------------------------------------------------
# B2 regressions: lockout, disabled accounts, token-type confusion, logout idempotence
# ---------------------------------------------------------------------------
@requires_db
def test_login_locks_after_max_failures_and_unlocks_on_expiry(app, seed, monkeypatch):
    from sqlalchemy import select, update

    from src.config.database import async_session
    from src.models.member import Member

    monkeypatch.setattr(settings_mod.settings, "MAX_FAILED_LOGINS", 3)

    async def flow():
        async with _client(app) as c:
            for _ in range(2):
                bad = await c.post("/auth/login", json={"username": seed["username"], "password": "wrong"})
                assert bad.status_code == 401 and bad.json()["detail"] == "Invalid credentials"
            async with async_session() as db:
                m = (await db.execute(select(Member).where(Member.username == seed["username"]))).scalar_one()
                assert m.failedLoginCount == 2 and m.lockedUntil is None
            third = await c.post("/auth/login", json={"username": seed["username"], "password": "wrong"})
            assert third.status_code == 401
            # locked: even the correct password is refused with 423 and the counter was reset
            locked = await c.post("/auth/login", json={"username": seed["username"], "password": seed["password"]})
            assert locked.status_code == 423
            assert "locked" in locked.json()["detail"].lower()
            async with async_session() as db:
                m = (await db.execute(select(Member).where(Member.username == seed["username"]))).scalar_one()
                assert m.lockedUntil is not None and m.failedLoginCount == 0
                await db.execute(
                    update(Member)
                    .where(Member.memberId == m.memberId)
                    .values(lockedUntil=datetime.now(timezone.utc) - timedelta(seconds=1))
                )
                await db.commit()
            # lock expired → login succeeds and clears the lock
            access, _ = await _login(c, seed)
            assert (await c.get("/system/whoami", headers=_auth(access))).status_code == 200
            async with async_session() as db:
                m = (await db.execute(select(Member).where(Member.username == seed["username"]))).scalar_one()
                assert m.lockedUntil is None and m.failedLoginCount == 0

    _run(flow())


@requires_db
def test_disabled_account_cannot_login_refresh_or_use_live_tokens(app, seed):
    from sqlalchemy import select, update

    from src.config.database import async_session
    from src.models.member import Member, StatusType

    async def flow():
        async with _client(app) as c:
            access, refresh = await _login(c, seed)
            async with async_session() as db:
                await db.execute(
                    update(Member).where(Member.username == seed["username"]).values(status=StatusType.DISABLED)
                )
                await db.commit()
            try:
                login = await c.post("/auth/login", json={"username": seed["username"], "password": seed["password"]})
                assert login.status_code == 403 and login.json()["detail"] == "Account disabled"
                live = await c.get("/system/whoami", headers=_auth(access))
                assert live.status_code == 403 and live.json()["detail"] == "Account disabled"
                renew = await c.post("/auth/refresh", json={"refreshToken": refresh})
                assert renew.status_code == 403
            finally:
                async with async_session() as db:
                    await db.execute(
                        update(Member).where(Member.username == seed["username"]).values(status=StatusType.ENABLE)
                    )
                    await db.commit()
            # the pair issued before disabling is still valid once re-enabled (nothing was revoked)
            assert (await c.get("/system/whoami", headers=_auth(access))).status_code == 200
            async with async_session() as db:
                m = (await db.execute(select(Member).where(Member.username == seed["username"]))).scalar_one()
                assert m.status == StatusType.ENABLE

    _run(flow())


@requires_db
def test_token_type_confusion_is_rejected(app, seed):
    async def flow():
        async with _client(app) as c:
            access, refresh = await _login(c, seed)
            # access token presented as refresh token
            r = await c.post("/auth/refresh", json={"refreshToken": access})
            assert r.status_code == 401 and r.json()["detail"] == "Wrong token type"
            # refresh token presented as bearer
            r = await c.get("/system/whoami", headers=_auth(refresh))
            assert r.status_code == 401 and r.json()["detail"] == "Wrong token type"
            # kiosk refresh endpoint refuses member refresh tokens
            r = await c.post("/auth/kiosk/refresh", json={"refreshToken": refresh})
            assert r.status_code == 401
            # missing body token
            r = await c.post("/auth/refresh", json={})
            assert r.status_code == 401 and r.json()["detail"] == "Refresh token required"
            # legacy snake_case field is still accepted
            r = await c.post("/auth/refresh", json={"refresh_token": refresh})
            assert r.status_code == 200 and r.json()["accessToken"]

    _run(flow())


@requires_db
def test_logout_is_idempotent_and_accepts_expired_access_token(app, seed):
    from src.security.jwt import TYP_ACCESS, create_token

    async def flow():
        async with _client(app) as c:
            access, refresh = await _login(c, seed)
            first = await c.post("/auth/logout", json={"refreshToken": refresh}, headers=_auth(access))
            assert first.status_code == 200 and first.json()["revokedTokens"] == 2
            second = await c.post("/auth/logout", json={"refreshToken": refresh}, headers=_auth(access))
            assert second.status_code == 200 and second.json()["ok"] is True

            # a lapsed access token can still log out (signature verified, exp ignored)
            access2, refresh2 = await _login(c, seed)
            fam = decode_token(refresh2, expected_typ="refresh")["fam"]
            payload = decode_token(access2)
            expired = create_token(
                payload["memberId"], payload["username"], typ=TYP_ACCESS, expires=timedelta(seconds=-30), family=fam
            )
            assert (await c.get("/system/whoami", headers=_auth(expired))).status_code == 401
            res = await c.post("/auth/logout", json={}, headers=_auth(expired))
            assert res.status_code == 200 and res.json()["familyRevoked"] is True
            # whole family gone: the live access token and the refresh token are both dead
            assert (await c.get("/system/whoami", headers=_auth(access2))).status_code == 401
            assert (await c.post("/auth/refresh", json={"refreshToken": refresh2})).status_code == 401

    _run(flow())
