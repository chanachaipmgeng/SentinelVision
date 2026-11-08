"""C4/C5: JWT-only approvedBy, thin approver gate, streaming payroll export, period lock."""
from __future__ import annotations

import io
import os
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
import pytest_asyncio
from openpyxl import load_workbook

if not os.environ.get("DPU_TEST_DB_READY"):
    pytest.skip(
        "No test database: set TEST_DATABASE_URL or `pip install pgserver`",
        allow_module_level=True,
    )

from sqlalchemy import select  # noqa: E402

from src.config.database import async_session  # noqa: E402
from src.models.company_employee import CompanyEmployee  # noqa: E402
from src.models.employee_timestamp import ApprovalStatus, EmployeeTimestamp, TimestampType  # noqa: E402
from src.models.approvals_payroll import PayrollPeriod, PayrollPeriodStatus  # noqa: E402
from src.routes import employee_timestamp_routes, hr_routes  # noqa: E402
from src.services.payroll_export_service import (  # noqa: E402
    SUMMARY_HEADERS,
    build_payroll_csv_bytes,
    iter_payroll_csv_chunks,
)
from tests.support import build_app, client, seed_world, teardown_world  # noqa: E402

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def world():
    w = await seed_world()
    # Manager relation: admin_a is boss of emp_a
    async with async_session() as db:
        emp = await db.get(CompanyEmployee, w.a.employee_employment.company_employeeId)
        emp.bossId = str(w.a.admin.memberId)
        await db.commit()
    w.app = build_app(
        (employee_timestamp_routes.router, "/timestamp"),
        (hr_routes.router, "/hr"),
    )
    yield w
    await teardown_world(w)


async def _seed_pending_warning(world, *, company="a") -> uuid.UUID:
    tenant = world.a if company == "a" else world.b
    ts_id = uuid.uuid4()
    async with async_session() as db:
        db.add(
            EmployeeTimestamp(
                timestampId=ts_id,
                companyId=tenant.company_id,
                company_employeeId=tenant.employee_employment.company_employeeId,
                timestamp=datetime.now(timezone.utc),
                timestampType=TimestampType.WARNING,
                approvalStatus=ApprovalStatus.PENDING.value,
                locationName="Outside",
                latitude=1.0,
                longitude=1.0,
                note="geofence",
            )
        )
        await db.commit()
    return ts_id


async def test_client_cannot_forge_approver(world):
    """approvedBy in the body is ignored; JWT member becomes the approver."""
    ts_id = await _seed_pending_warning(world)
    forged = uuid.uuid4()
    async with client(world.app) as c:
        r = await c.post(
            f"/timestamp/company/{world.a.company_id}/{ts_id}/approval",
            headers=world.auth("admin_a"),
            json={"approve": True, "approvedBy": str(forged)},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["approvedBy"] == str(world.a.admin.memberId)
    assert body["approvedBy"] != str(forged)
    assert body["approvalStatus"] in (ApprovalStatus.APPROVED.value, "APPROVED")


async def test_non_boss_employee_cannot_approve(world):
    ts_id = await _seed_pending_warning(world)
    async with client(world.app) as c:
        r = await c.post(
            f"/timestamp/company/{world.a.company_id}/{ts_id}/approval",
            headers=world.auth("emp_a"),
            json={"approve": True, "approvedBy": str(world.a.admin.memberId)},
        )
    assert r.status_code == 403, r.text


async def test_payroll_csv_streams_summary_and_detail(world):
    # Seed a few punches beyond what matters for streaming shape.
    async with async_session() as db:
        for i in range(3):
            db.add(
                EmployeeTimestamp(
                    timestampId=uuid.uuid4(),
                    companyId=world.a.company_id,
                    company_employeeId=world.a.employee_employment.company_employeeId,
                    timestamp=datetime.now(timezone.utc) - timedelta(hours=i),
                    timestampType=TimestampType.CHECK_IN if i % 2 == 0 else TimestampType.CHECK_OUT,
                    approvalStatus=ApprovalStatus.NONE.value,
                    locationName="HQ",
                    latitude=13.75,
                    longitude=100.5,
                )
            )
        await db.commit()

    chunks: list[bytes] = []
    async with async_session() as db:
        async for chunk in iter_payroll_csv_chunks(
            db,
            world.a.company_id,
            date.today() - timedelta(days=1),
            date.today() + timedelta(days=1),
            None,
        ):
            chunks.append(chunk)
    assert chunks, "expected at least one streamed chunk"
    text = b"".join(chunks).decode("utf-8-sig")
    assert "# Summary" in text
    assert "# Punch Detail" in text
    assert SUMMARY_HEADERS[0] in text

    async with client(world.app) as c:
        r = await c.get(
            f"/timestamp/export/company/{world.a.company_id}",
            params={"format": "csv", "mode": "payroll"},
            headers=world.auth("admin_a"),
        )
    assert r.status_code == 200, r.text
    assert "text/csv" in r.headers.get("content-type", "")
    assert "# Summary" in r.text


async def test_payroll_xlsx_has_two_sheets(world):
    async with async_session() as db:
        data = await build_payroll_csv_bytes(
            db, world.a.company_id, date.today() - timedelta(days=7), date.today(), None
        )
    assert data.startswith(b"\xef\xbb\xbf") or b"Summary" in data

    async with client(world.app) as c:
        r = await c.get(
            f"/timestamp/export/company/{world.a.company_id}",
            params={"format": "xlsx", "mode": "payroll"},
            headers=world.auth("admin_a"),
        )
    assert r.status_code == 200, r.text
    wb = load_workbook(io.BytesIO(r.content))
    names = set(wb.sheetnames)
    assert "Daily Summary" in names
    assert "Punch Detail" in names


async def test_payroll_period_lock_blocks_leave_and_emits_close(world):
    start = date.today().replace(day=1)
    end = (start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    async with client(world.app) as c:
        created = await c.post(
            f"/hr/company/{world.a.company_id}/payroll-periods",
            headers=world.auth("admin_a"),
            json={"name": "Test Period", "startDate": start.isoformat(), "endDate": end.isoformat()},
        )
        assert created.status_code == 200, created.text
        period_id = created.json()["periodId"]

        closed = await c.post(
            f"/hr/company/{world.a.company_id}/payroll-periods/{period_id}/close",
            headers=world.auth("admin_a"),
        )
        assert closed.status_code == 200, closed.text
        assert closed.json()["status"] == PayrollPeriodStatus.LOCKED.value
        assert closed.json()["lockedBy"] == str(world.a.admin.memberId)

        leave = await c.post(
            f"/hr/company/{world.a.company_id}/leaves",
            headers=world.auth("admin_a"),
            json={
                "company_employeeId": str(world.a.employee_employment.company_employeeId),
                "leaveType": "ANNUAL",
                "startDate": start.isoformat(),
                "endDate": start.isoformat(),
                "reason": "should fail",
            },
        )
        assert leave.status_code == 409, leave.text

    async with async_session() as db:
        row = (
            await db.execute(select(PayrollPeriod).where(PayrollPeriod.periodId == uuid.UUID(period_id)))
        ).scalar_one()
        assert row.status == PayrollPeriodStatus.LOCKED.value
