"""Regression tests for company-scoped audit writes.

``write_audit`` used ``UUID`` / ``Optional`` / ``Any`` without importing them, so every
audit row that carried a ``company_id`` died with ``NameError`` inside the middleware's
fire-and-forget task and the company audit log stayed empty.

These tests need the PostgreSQL prepared by ``tests/conftest.py`` (migrated to Alembic head);
they skip when the database cannot be reached so the rest of the suite still runs.
"""

from __future__ import annotations

import asyncio
import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import src.models  # noqa: E402,F401  (register mappers so Member relationships resolve)
from src.config.database import async_session, engine  # noqa: E402
from src.models.member import Member, RoleType, StatusType  # noqa: E402
from src.routes.company_routes import router as company_router  # noqa: E402
from src.security.jwt import create_access_token  # noqa: E402
from src.security.middleware import AuthzMiddleware  # noqa: E402
from src.services.audit_service import AuditLog, write_audit  # noqa: E402


async def _probe_database() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
    finally:
        # asyncpg connections are bound to the loop that created them; never leak them
        # from this throwaway loop into the loop pytest/TestClient will use next.
        await engine.dispose()


@pytest.fixture(scope="module", autouse=True)
def _require_database():
    if not asyncio.run(_probe_database()):
        pytest.skip("Postgres not reachable at DATABASE_URL; skipping audit DB tests")


def _make_admin(suffix: str) -> Member:
    return Member(
        memberId=uuid.uuid4(),
        username=f"audit-test-{suffix}",
        email=f"audit-test-{suffix}@test.local",
        passwordHash="!",  # never logged in through this account
        role=RoleType.ADMIN_SYSTEM,
        status=StatusType.ENABLE,
    )


async def _cleanup(member_id: uuid.UUID, company_id: uuid.UUID) -> None:
    async with async_session() as db:
        await db.execute(delete(AuditLog).where(AuditLog.companyId == company_id))
        await db.execute(delete(Member).where(Member.memberId == member_id))
        await db.commit()


@pytest.mark.asyncio
async def test_write_audit_persists_company_id_directly():
    """Direct service call with a real ``company_id`` must insert a row (was ``NameError``)."""
    company_id = uuid.uuid4()
    member = _make_admin(uuid.uuid4().hex[:8])
    try:
        async with async_session() as db:
            db.add(member)
            await db.commit()

        await write_audit(
            actor=member,
            action="POST",
            path=f"/companys/{company_id}/direct",
            status_code=200,
            ip="127.0.0.1",
            user_agent="pytest",
            request_id="req-direct",
            company_id=str(company_id),
            entity_type="company",
            entity_id=str(company_id),
            detail={"source": "test"},
        )

        async with async_session() as db:
            rows = (
                await db.execute(select(AuditLog).where(AuditLog.companyId == company_id))
            ).scalars().all()
        assert len(rows) == 1
        row = rows[0]
        assert row.companyId == company_id
        assert row.actorMemberId == member.memberId
        assert row.actorRole == "ADMIN_SYSTEM"
        assert row.action == "POST"
        assert row.statusCode == "200"
        assert row.detail == {"source": "test"}
    finally:
        await _cleanup(member.memberId, company_id)
        await engine.dispose()


@pytest.fixture(scope="module")
def audited_client():
    """Minimal app wired with the real ``AuthzMiddleware`` and the real audit-log read route.

    The full ``src.main`` app is not used because its startup pulls InsightFace / ONNX and the
    GPU queue; the middleware → ``_audit`` → ``write_audit`` path
    exercised here is exactly the one that silently failed in production.
    """
    company_id = uuid.uuid4()
    member = _make_admin(uuid.uuid4().hex[:8])

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        async with async_session() as db:
            db.add(member)
            await db.commit()
        try:
            yield
        finally:
            await _cleanup(member.memberId, company_id)
            await engine.dispose()

    app = FastAPI(lifespan=lifespan)
    app.add_middleware(AuthzMiddleware)

    @app.post("/companys/{companyId}/audit-probe")
    async def audit_probe(companyId: str):
        return {"ok": True, "companyId": companyId}

    app.include_router(company_router, prefix="/companys")

    token = create_access_token(str(member.memberId), member.username)
    with TestClient(app) as client:
        client.headers.update({"Authorization": f"Bearer {token}"})
        yield client, company_id, member


def test_company_write_appears_in_company_audit_log(audited_client):
    client, company_id, member = audited_client
    probe_path = f"/companys/{company_id}/audit-probe"

    resp = client.post(probe_path, headers={"User-Agent": "pytest-audit"})
    assert resp.status_code == 200, resp.text

    # The middleware audits via asyncio.create_task after the response; poll briefly.
    rows = []
    for _ in range(50):
        listing = client.get(f"/companys/{company_id}/audit-logs")
        assert listing.status_code == 200, listing.text
        rows = [r for r in listing.json() if r["path"] == probe_path]
        if rows:
            break
        time.sleep(0.05)

    assert rows, "company-scoped audit row was never written"
    row = rows[0]
    assert row["action"] == "POST"
    assert row["statusCode"] == "200"
    assert row["actorMemberId"] == str(member.memberId)
    assert row["actorRole"] == "ADMIN_SYSTEM"


def test_read_only_request_is_not_audited(audited_client):
    client, company_id, _member = audited_client
    before = client.get(f"/companys/{company_id}/audit-logs").json()
    # Two more GETs must not add rows (only POST/PUT/PATCH/DELETE are audited).
    client.get(f"/companys/{company_id}/audit-logs")
    time.sleep(0.1)
    after = client.get(f"/companys/{company_id}/audit-logs").json()
    assert len(after) == len(before)
