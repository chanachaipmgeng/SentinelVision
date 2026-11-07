"""B7 background worker: outbox dispatched by the worker runner, import job lifecycle, runner
shutdown / single-run semantics. DB-backed tests use the embedded PostgreSQL from conftest."""
from __future__ import annotations

import asyncio
import io
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
import pytest_asyncio

for _mod in ("insightface", "insightface.app", "cv2", "onnxruntime"):
    sys.modules.setdefault(_mod, MagicMock())

from src.services import observability as obs  # noqa: E402
from src.worker import runner as worker_runner  # noqa: E402
from src.worker.runner import JobSpec, WorkerRunner, parse_job_list, run_jobs_once  # noqa: E402

pytestmark = pytest.mark.asyncio(loop_scope="module")


# ----------------------------------------------------------------------------- runner (no DB)
def test_parse_job_list_defaults_and_validation():
    assert parse_job_list("") == ["outbox", "retention", "imports", "attendance_summary"]
    assert parse_job_list("all") == ["outbox", "retention", "imports", "attendance_summary"]
    assert parse_job_list(" imports , outbox ") == ["imports", "outbox"]
    with pytest.raises(ValueError):
        parse_job_list("outbox,nope")


async def test_run_jobs_once_reports_per_job_result(monkeypatch):
    calls = []

    async def ok_job():
        calls.append("ok")
        return {"n": 1}

    async def bad_job(*, worker_id, stop_event):
        calls.append(worker_id)
        raise RuntimeError("boom")

    monkeypatch.setitem(worker_runner.JOBS, "ok", JobSpec("ok", ok_job))
    monkeypatch.setitem(worker_runner.JOBS, "bad", JobSpec("bad", bad_job, takes_context=True))
    results = await run_jobs_once(["ok", "bad"], worker_id="w-test")
    assert results == {"ok": True, "bad": False}
    assert calls == ["ok", "w-test"]
    text = obs.render_metrics()
    assert 'dpu_job_runs_total{job_name="ok",result="ok"}' in text
    assert 'dpu_job_runs_total{job_name="bad",result="error"}' in text
    assert 'dpu_job_last_success_timestamp_seconds{job_name="ok"}' in text


async def test_runner_stops_gracefully_and_cancels_slow_jobs(monkeypatch):
    started = asyncio.Event()
    finished = {"fast": 0}

    async def fast_job():
        finished["fast"] += 1
        return {}

    async def slow_job(*, worker_id, stop_event):
        started.set()
        await asyncio.sleep(30)

    monkeypatch.setitem(worker_runner.JOBS, "fast", JobSpec("fast", fast_job))
    monkeypatch.setitem(worker_runner.JOBS, "slow", JobSpec("slow", slow_job, takes_context=True))
    monkeypatch.setattr(worker_runner.job_bodies, "poll_interval", lambda name: 60.0)

    runner = WorkerRunner(["fast", "slow"], worker_id="w-stop")
    await runner.start()
    await asyncio.wait_for(started.wait(), 2)
    assert finished["fast"] == 1
    await asyncio.wait_for(runner.stop(grace_seconds=0.2), 5)
    assert runner.stop_event.is_set()
    assert runner._tasks == []  # noqa: SLF001


async def test_runner_wakes_job_on_trigger(monkeypatch):
    runs = {"n": 0}

    async def counting_job():
        runs["n"] += 1
        return {}

    monkeypatch.setitem(worker_runner.JOBS, "count", JobSpec("count", counting_job))
    monkeypatch.setattr(worker_runner.job_bodies, "poll_interval", lambda name: 60.0)
    runner = WorkerRunner(["count"], worker_id="w-trigger")
    await runner.start()
    await asyncio.sleep(0.05)
    runner.trigger("count")
    await asyncio.sleep(0.05)
    await runner.stop(grace_seconds=1)
    assert runs["n"] == 2


# ----------------------------------------------------------------------------- DB-backed
if not os.environ.get("DPU_TEST_DB_READY"):
    _db = pytest.mark.skip(reason="No test database: set TEST_DATABASE_URL or `pip install pgserver`")
else:
    _db = pytest.mark.usefixtures("fx")


def _workbook(rows) -> bytes:
    from openpyxl import Workbook

    from src.controllers.employee_import_controller import HEADERS

    wb = Workbook()
    ws = wb.active
    ws.title = "Employees"
    ws.append(HEADERS)
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


class Fixture:
    pass


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def fx(tmp_path_factory):
    from sqlalchemy import text

    import src.models  # noqa: F401
    from src.config.database import Base, async_session, engine
    from src.config.settings import settings
    from src.models.company import Company
    from src.models.company_employee import CompanyEmployee, CompanyRoleType
    from src.models.department import Department
    from src.models.member import Member, RoleType, StatusType
    from src.models.position import Position
    from src.security.jwt import create_access_token
    from src.services import audit_service, notification_service  # noqa: F401

    await engine.dispose(close=False)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"test database not reachable: {exc}")

    job_dir = tmp_path_factory.mktemp("import_jobs")
    old_dir = settings.IMPORT_JOB_DIR
    settings.IMPORT_JOB_DIR = str(job_dir)

    f = Fixture()
    tag = uuid.uuid4().hex[:6]
    f.tag = tag
    f.company = Company(
        companyId=uuid.uuid4(),
        companyName=f"worker-co-{tag}",
        companyCode=f"WRK{tag}".upper(),
        companyInfo="worker test",
        address="n/a",
    )
    f.dept = Department(departmentId=uuid.uuid4(), thName="ฝ่ายบุคคล", engName="HR", companyId=f.company.companyId)
    f.pos = Position(positionId=uuid.uuid4(), thName="เจ้าหน้าที่", engName="Officer", companyId=f.company.companyId)
    f.admin = Member(
        memberId=uuid.uuid4(),
        username=f"wadmin-{tag}",
        email=f"wadmin-{tag}@example.com",
        firstName="Admin",
        lastName="Worker",
        role=RoleType.MEMBER,
        status=StatusType.ENABLE,
    )
    f.admin.hash_password("Passw0rd!xyz")
    async with async_session() as db:
        db.add(f.company)
        await db.flush()
        db.add_all([f.dept, f.pos, f.admin])
        await db.flush()
        db.add(
            CompanyEmployee(
                memberId=f.admin.memberId,
                companyId=f.company.companyId,
                departmentId=f.dept.departmentId,
                positionId=f.pos.positionId,
                companyRoleType=CompanyRoleType.ADMIN_COMPANY,
            )
        )
        await db.commit()
    f.token = create_access_token(str(f.admin.memberId), f.admin.username)
    yield f

    settings.IMPORT_JOB_DIR = old_dir
    async with async_session() as db:
        cid = {"cid": f.company.companyId}
        await db.execute(text('DELETE FROM import_job WHERE "companyId" = :cid'), cid)
        await db.execute(text('DELETE FROM notification_outbox WHERE "companyId" = :cid'), cid)
        member_ids = (
            await db.execute(text('SELECT "memberId" FROM company_employee WHERE "companyId" = :cid'), cid)
        ).scalars().all()
        for tbl in ("company_employee", "department", "position"):
            await db.execute(text(f'DELETE FROM {tbl} WHERE "companyId" = :cid'), cid)
        await db.execute(text('DELETE FROM company WHERE "companyId" = :cid'), cid)
        for mid in member_ids:
            await db.execute(text('DELETE FROM member WHERE "memberId" = :mid'), {"mid": mid})
        await db.commit()
    await engine.dispose()


@_db
async def test_outbox_row_is_dispatched_by_worker_runner(fx):
    from sqlalchemy import select

    from src.config.database import async_session
    from src.services.notification_service import NotificationOutbox, enqueue, refresh_outbox_backlog

    # webhook without URL → _send_webhook logs "skipped" and the row counts as sent (no network).
    await enqueue("test.event", "webhook", {"body": "hello"}, company_id=str(fx.company.companyId))
    pending, oldest = await refresh_outbox_backlog()
    assert pending >= 1 and oldest is not None

    results = await run_jobs_once(["outbox"], worker_id="w-outbox")
    assert results == {"outbox": True}

    async with async_session() as db:
        rows = (
            await db.execute(
                select(NotificationOutbox).where(NotificationOutbox.companyId == fx.company.companyId)
            )
        ).scalars().all()
    assert rows and all(r.status == "sent" and r.attempts == 1 for r in rows)
    text = obs.render_metrics()
    assert 'dpu_outbox_deliveries_total{channel="webhook",result="sent"}' in text
    assert "dpu_outbox_claims_total" in text
    assert 'dpu_job_runs_total{job_name="outbox",result="ok"}' in text


@_db
async def test_outbox_failures_back_off_and_eventually_fail(fx, monkeypatch):
    from sqlalchemy import select

    from src.config.database import async_session
    from src.services import notification_service as ns

    def _boom(payload, **kwargs):
        raise RuntimeError("endpoint down")

    monkeypatch.setattr(ns, "_send_webhook", _boom)
    await ns.enqueue("test.fail", "webhook", {"webhookUrl": "http://127.0.0.1:9/x"}, company_id=str(fx.company.companyId))
    await ns.drain_outbox()
    async with async_session() as db:
        row = (
            await db.execute(
                select(ns.NotificationOutbox).where(
                    ns.NotificationOutbox.companyId == fx.company.companyId,
                    ns.NotificationOutbox.event == "test.fail",
                )
            )
        ).scalar_one()
        assert row.status == "pending" and row.attempts == 1 and "endpoint down" in (row.lastError or "")
        # Force the backoff window to elapse and exhaust the remaining attempts.
        row.attempts = ns.OUTBOX_MAX_ATTEMPTS - 1
        row.createdAt = datetime.now(timezone.utc) - timedelta(hours=1)
        await db.commit()
    await ns.drain_outbox()
    async with async_session() as db:
        row = (
            await db.execute(
                select(ns.NotificationOutbox).where(
                    ns.NotificationOutbox.companyId == fx.company.companyId,
                    ns.NotificationOutbox.event == "test.fail",
                )
            )
        ).scalar_one()
        assert row.status == "failed" and row.attempts == ns.OUTBOX_MAX_ATTEMPTS
    assert 'dpu_outbox_deliveries_total{channel="webhook",result="failed"}' in obs.render_metrics()


@_db
async def test_import_job_lifecycle_api_handoff_to_worker(fx):
    import httpx
    from fastapi import FastAPI

    from src.config.database import async_session
    from src.models.import_job import ImportJob
    from src.routes import employee_routes
    from src.security.middleware import AuthzMiddleware
    from src.services.import_job_service import import_job_root, process_pending_import_jobs

    app = FastAPI(redirect_slashes=False)
    app.add_middleware(AuthzMiddleware)
    app.include_router(employee_routes.router, prefix="/employees")
    headers = {"Authorization": f"Bearer {fx.token}"}
    cid = str(fx.company.companyId)

    good = f"imp-good-{fx.tag}@example.com"
    xlsx = _workbook(
        [
            [good, "สมชาย", "ใจดี", "ฝ่ายบุคคล", "เจ้าหน้าที่", "รายเดือน", f"E{fx.tag}", "", "", "", "", "", "", "", "0", "พนักงาน", ""],
            ["not-an-email", "x", "y", "ฝ่ายบุคคล", "เจ้าหน้าที่", "รายเดือน", "", "", "", "", "", "", "", "", "0", "", ""],
        ]
    )
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        # Wrong file type is rejected before anything is persisted.
        r = await c.post(
            f"/employees/company/{cid}/import-jobs",
            files={"file": ("import.csv", b"a,b", "text/csv")},
            headers=headers,
        )
        assert r.status_code == 400
        r = await c.post(
            f"/employees/company/{cid}/import-jobs",
            files={"file": ("employees.xlsx", xlsx, "application/octet-stream")},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        job_id = body["jobId"]
        assert body["status"] == "pending"
        assert body["progress"]["processed"] == 0

        # API only persisted the hand-off: payload on the shared dir, row pending, nothing processed.
        assert (import_job_root() / job_id / "employees.xlsx").is_file()
        r = await c.get(f"/employees/company/{cid}/import-jobs/{job_id}", headers=headers)
        assert r.status_code == 200
        assert r.json()["status"] == "pending"
        assert r.json()["fileName"] == "employees.xlsx"
        # Other tenants cannot read it.
        other = uuid.uuid4()
        r = await c.get(f"/employees/company/{other}/import-jobs/{job_id}", headers=headers)
        assert r.status_code in (403, 404)

        # Worker side.
        processed = await process_pending_import_jobs("w-import")
        assert processed >= 1

        r = await c.get(f"/employees/company/{cid}/import-jobs/{job_id}", headers=headers)
        assert r.status_code == 200
        job = r.json()
        assert job["status"] == "done", job
        assert job["result"]["total"] == 2
        assert job["result"]["success"] == 1
        assert job["result"]["failed"] == 1
        assert job["progress"] == {"processed": 2, "total": 2, "success": 1, "failed": 1, "facesEnrolled": 0}
        assert job["startedAt"] and job["finishedAt"]

    async with async_session() as db:
        row = await db.get(ImportJob, uuid.UUID(job_id))
        assert row.lockedBy == "w-import"
        assert row.attempts == 1
        assert row.requestedBy == fx.admin.memberId
        assert row.heartbeatAt is not None

    text = obs.render_metrics()
    assert 'dpu_import_jobs_total{result="done"}' in text
    assert 'dpu_import_job_rows_total{result="success"}' in text
    assert "dpu_import_job_duration_seconds_count" in text

    # The finished job emitted an import.finished notification for the outbox.
    from sqlalchemy import select

    from src.services.notification_service import NotificationOutbox

    async with async_session() as db:
        events = (
            await db.execute(
                select(NotificationOutbox.event).where(NotificationOutbox.companyId == fx.company.companyId)
            )
        ).scalars().all()
    assert "import.finished" in events


@_db
async def test_import_job_missing_payload_fails_cleanly(fx):
    import shutil

    from src.config.database import async_session
    from src.models.import_job import ImportJob
    from src.services.import_job_service import create_import_job, import_job_root, process_pending_import_jobs

    job = await create_import_job(fx.company.companyId, file_name="lost.xlsx", data=b"x")
    shutil.rmtree(import_job_root() / str(job.id))
    assert await process_pending_import_jobs("w-lost") == 1
    async with async_session() as db:
        row = await db.get(ImportJob, job.id)
    assert row.status == "failed"
    assert "payload missing" in (row.error or "")


@_db
async def test_stale_running_import_job_is_failed_by_retention(fx):
    from src.config.database import async_session
    from src.models.import_job import ImportJob
    from src.services.import_job_service import fail_stale_running_jobs

    stale_id = uuid.uuid4()
    async with async_session() as db:
        db.add(
            ImportJob(
                id=stale_id,
                companyId=fx.company.companyId,
                status="running",
                lockedBy="dead-worker",
                startedAt=datetime.now(timezone.utc) - timedelta(hours=2),
                heartbeatAt=datetime.now(timezone.utc) - timedelta(hours=2),
                fileName="old.xlsx",
            )
        )
        db.add(
            ImportJob(
                id=uuid.uuid4(),
                companyId=fx.company.companyId,
                status="running",
                lockedBy="live-worker",
                startedAt=datetime.now(timezone.utc),
                heartbeatAt=datetime.now(timezone.utc),
                fileName="fresh.xlsx",
            )
        )
        await db.commit()
    assert await fail_stale_running_jobs(lease_seconds=600) == 1
    async with async_session() as db:
        row = await db.get(ImportJob, stale_id)
    assert row.status == "failed" and "lease expired" in row.error


@_db
async def test_retention_job_runs_in_worker(fx, tmp_path, monkeypatch):
    from src.config.settings import settings
    from src.services import storage_service

    monkeypatch.setitem(storage_service.ROOTS, "temp_images", tmp_path / "temp_images")
    monkeypatch.setitem(storage_service.ROOTS, "uploaded_images", tmp_path / "uploaded_images")
    monkeypatch.setattr(settings, "TEMP_RETENTION_HOURS", 1)
    (tmp_path / "temp_images").mkdir()
    (tmp_path / "uploaded_images").mkdir()
    old = tmp_path / "temp_images" / "old.jpg"
    old.write_bytes(b"x")
    os.utime(old, (0, 0))
    results = await run_jobs_once(["retention"], worker_id="w-ret")
    assert results == {"retention": True}
    assert not old.exists()
    assert 'dpu_job_runs_total{job_name="retention",result="ok"}' in obs.render_metrics()
