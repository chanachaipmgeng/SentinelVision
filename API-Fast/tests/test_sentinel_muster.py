"""F4: muster roll includes attendance_daily PRESENT (+ open presence / visitors)."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio

if not os.environ.get("DPU_TEST_DB_READY"):
    pytest.skip(
        "No test database: set TEST_DATABASE_URL or `pip install pgserver`",
        allow_module_level=True,
    )

from src.config.database import async_session  # noqa: E402
from src.models.attendance_daily import AttendanceDaily, AttendanceDailyStatus  # noqa: E402
from src.models.employee_timestamp import EmployeeTimestamp, TimestampType  # noqa: E402
from src.services.sentinel_muster_service import build_muster_roll, bangkok_tz  # noqa: E402
from tests.support import seed_world, teardown_world  # noqa: E402

BKK = ZoneInfo("Asia/Bangkok")


@pytest_asyncio.fixture
async def world():
    w = await seed_world()
    yield w
    await teardown_world(w)


@pytest.mark.asyncio
async def test_muster_includes_present_from_attendance_daily(world):
    company_id = world.a.company_id
    emp = world.a.employee_employment
    work_date = datetime.now(bangkok_tz()).date()

    async with async_session() as db:
        db.add(
            AttendanceDaily(
                id=uuid.uuid4(),
                companyId=company_id,
                employeeId=emp.company_employeeId,
                workDate=work_date,
                firstIn=datetime.now(timezone.utc),
                workMinutes=120,
                status=AttendanceDailyStatus.PRESENT.value,
            )
        )
        await db.commit()

    async with async_session() as db:
        muster = await build_muster_roll(db, company_id, limit=50, offset=0)

    assert muster["workDate"] == work_date.isoformat()
    assert muster["total"] >= 1
    ids = {p["subjectId"] for p in muster["items"]}
    assert str(emp.company_employeeId) in ids
    present_row = next(
        p for p in muster["items"] if p["subjectId"] == str(emp.company_employeeId)
    )
    assert present_row["category"] == "EMPLOYEE"
    assert "attendance_daily" in (present_row.get("source") or "")


@pytest.mark.asyncio
async def test_muster_includes_open_check_in_presence(world):
    company_id = world.a.company_id
    emp = world.a.employee_employment
    now_local = datetime.now(BKK)
    # Store naive UTC to match EmployeeTimestamp conventions used by overview.
    punch_at = now_local.astimezone(timezone.utc).replace(tzinfo=None)

    async with async_session() as db:
        db.add(
            EmployeeTimestamp(
                companyId=company_id,
                company_employeeId=emp.company_employeeId,
                timestamp=punch_at,
                timestampType=TimestampType.CHECK_IN,
                locationName="Lobby Kiosk",
            )
        )
        await db.commit()

    async with async_session() as db:
        muster = await build_muster_roll(db, company_id, limit=50, offset=0)

    match = next(
        (p for p in muster["items"] if p["subjectId"] == str(emp.company_employeeId)),
        None,
    )
    assert match is not None
    assert match["zoneOrLocation"] == "Lobby Kiosk"
    assert "open_presence" in (match.get("source") or "") or match["category"] == "EMPLOYEE"


@pytest.mark.asyncio
async def test_muster_pagination_cap(world):
    company_id = world.a.company_id
    async with async_session() as db:
        page = await build_muster_roll(db, company_id, limit=1, offset=0)
    assert page["limit"] == 1
    assert page["offset"] == 0
    assert len(page["items"]) <= 1
