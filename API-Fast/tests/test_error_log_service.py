"""Tests for system-admin error_log capture, redact, dedupe, and routes."""
from __future__ import annotations

import asyncio
import sys
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import delete, text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import src.models  # noqa: E402,F401
from src.config.database import async_session, engine  # noqa: E402
from src.models.member import Member, RoleType, StatusType  # noqa: E402
from src.routes import system_routes  # noqa: E402
from src.security.jwt import create_access_token  # noqa: E402
from src.security.middleware import AuthzMiddleware, _is_kiosk_path_allowed  # noqa: E402
from src.services.error_log_service import (  # noqa: E402
    SOURCE_API,
    SOURCE_CLIENT,
    ErrorLog,
    build_fingerprint,
    normalize_path,
    purge_old_error_logs,
    should_capture_client_status,
    should_capture_status,
    write_error_log,
)
from src.services.observability import redact  # noqa: E402
from src.services.rate_limit_service import reset_rate_limits_for_tests  # noqa: E402


async def _probe_database() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            await conn.execute(text("SELECT 1 FROM error_log LIMIT 1"))
        return True
    except Exception:
        return False
    finally:
        await engine.dispose()


@pytest.fixture(scope="module", autouse=True)
def _require_database():
    if not asyncio.run(_probe_database()):
        pytest.skip("Postgres/error_log not reachable; skipping error log DB tests")


def _make_member(*, role: RoleType, suffix: str) -> Member:
    return Member(
        memberId=uuid.uuid4(),
        username=f"errlog-{suffix}",
        email=f"errlog-{suffix}@test.local",
        passwordHash="!",
        role=role,
        status=StatusType.ENABLE,
    )


async def _cleanup(*member_ids: uuid.UUID) -> None:
    async with async_session() as db:
        await db.execute(delete(ErrorLog))
        for mid in member_ids:
            await db.execute(delete(Member).where(Member.memberId == mid))
        await db.commit()


def test_should_capture_status_matrix():
    assert should_capture_status(500) is True
    assert should_capture_status(400) is True
    assert should_capture_status(409) is True
    assert should_capture_status(422) is True
    assert should_capture_status(401) is False
    assert should_capture_status(403) is False
    assert should_capture_status(404) is False
    assert should_capture_status(429) is False
    assert should_capture_client_status(0) is True


def test_normalize_path_strips_ids_and_query():
    path = normalize_path("/companys/11111111-1111-1111-1111-111111111111/employees/42?x=1")
    assert path == "/companys/{id}/employees/{id}"


def test_fingerprint_stable():
    a = build_fingerprint(
        source="api", method="post", path="/x/1", status_code=500, exception_type="ValueError"
    )
    b = build_fingerprint(
        source="api", method="POST", path="/x/2", status_code=500, exception_type="ValueError"
    )
    assert a == b


def test_redact_password_in_detail():
    masked = redact({"password": "secret", "ok": 1})
    assert masked["password"] == "[REDACTED]"
    assert masked["ok"] == 1


def test_kiosk_may_post_client_errors_only():
    assert _is_kiosk_path_allowed("POST", "/system/client-errors") is True
    assert _is_kiosk_path_allowed("GET", "/system/client-errors") is False


@pytest.mark.asyncio
async def test_write_error_log_dedupes_and_redacts():
    suffix = uuid.uuid4().hex[:8]
    member = _make_member(role=RoleType.ADMIN_SYSTEM, suffix=suffix)
    try:
        async with async_session() as db:
            db.add(member)
            await db.commit()

        first = await write_error_log(
            source=SOURCE_API,
            status_code=500,
            message="boom",
            method="GET",
            path="/probe/err",
            exception_type="RuntimeError",
            detail={"password": "nope", "nested": {"token": "abc"}},
            actor_member_id=member.memberId,
            request_id="req-1",
        )
        assert first is not None
        assert first.hitCount == 1
        assert first.detail["password"] == "[REDACTED]"
        assert first.detail["nested"]["token"] == "[REDACTED]"

        second = await write_error_log(
            source=SOURCE_API,
            status_code=500,
            message="boom again",
            method="GET",
            path="/probe/err",
            exception_type="RuntimeError",
            request_id="req-2",
        )
        assert second is not None
        assert second.id == first.id
        assert second.hitCount == 2
        assert second.requestId == "req-2"
    finally:
        await _cleanup(member.memberId)
        await engine.dispose()


@pytest.fixture()
def error_log_client():
    reset_rate_limits_for_tests()
    admin = _make_member(role=RoleType.ADMIN_SYSTEM, suffix=uuid.uuid4().hex[:8])
    company_admin = _make_member(role=RoleType.ADMIN_COMPANY, suffix=uuid.uuid4().hex[:8])

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        async with async_session() as db:
            db.add(admin)
            db.add(company_admin)
            await db.commit()
        try:
            yield
        finally:
            await _cleanup(admin.memberId, company_admin.memberId)
            await engine.dispose()

    app = FastAPI(lifespan=lifespan)
    app.add_middleware(AuthzMiddleware)
    app.include_router(system_routes.router, prefix="/system")

    admin_token = create_access_token(str(admin.memberId), admin.username)
    company_token = create_access_token(str(company_admin.memberId), company_admin.username)
    with TestClient(app) as client:
        yield client, admin_token, company_token, admin


def test_client_error_ingest_and_list_requires_system_admin(error_log_client):
    client, admin_token, company_token, _admin = error_log_client

    denied = client.get(
        "/system/error-logs",
        headers={"Authorization": f"Bearer {company_token}"},
    )
    assert denied.status_code == 403, denied.text

    accepted = client.post(
        "/system/client-errors",
        headers={"Authorization": f"Bearer {company_token}"},
        json={
            "message": "Network failed",
            "statusCode": 0,
            "method": "GET",
            "path": "/companys/x",
            "pageUrl": "http://localhost/admin",
        },
    )
    assert accepted.status_code == 202, accepted.text
    assert accepted.json().get("accepted") is True

    skipped = client.post(
        "/system/client-errors",
        headers={"Authorization": f"Bearer {company_token}"},
        json={"message": "unauthorized", "statusCode": 401, "path": "/x"},
    )
    assert skipped.status_code == 202, skipped.text
    assert skipped.json().get("accepted") is False

    rows = []
    for _ in range(50):
        listing = client.get(
            "/system/error-logs",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"paged": "true", "source": SOURCE_CLIENT, "q": "Network failed"},
        )
        assert listing.status_code == 200, listing.text
        payload = listing.json()
        rows = payload.get("items") if isinstance(payload, dict) else payload
        if rows:
            break
        time.sleep(0.05)

    assert rows, "client error was never persisted"
    row = rows[0]
    assert row["source"] == SOURCE_CLIENT
    assert row["statusCode"] == 0
    assert row["message"] == "Network failed"

    detail = client.get(
        f"/system/error-logs/{row['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert detail.status_code == 200, detail.text

    patched = client.patch(
        f"/system/error-logs/{row['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"resolved": True},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["resolvedAt"] is not None

    company_patch = client.patch(
        f"/system/error-logs/{row['id']}",
        headers={"Authorization": f"Bearer {company_token}"},
        json={"resolved": False},
    )
    assert company_patch.status_code == 403


@pytest.mark.asyncio
async def test_purge_old_error_logs_respects_retention():
    row = await write_error_log(
        source=SOURCE_API,
        status_code=500,
        message="old",
        method="GET",
        path="/old",
        exception_type="RuntimeError",
    )
    assert row is not None
    async with async_session() as db:
        db_row = await db.get(ErrorLog, row.id)
        assert db_row is not None
        db_row.occurredAt = datetime.now(timezone.utc) - timedelta(days=60)
        await db.commit()

    removed = await purge_old_error_logs(retention_days=30)
    assert removed >= 1
    async with async_session() as db:
        gone = await db.get(ErrorLog, row.id)
        assert gone is None
    await engine.dispose()
