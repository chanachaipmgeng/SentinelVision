"""C1+C2: attendance_daily recompute and holiday/leave-aware shift metrics."""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio

if not os.environ.get("DPU_TEST_DB_READY"):
    pytest.skip(
        "No test database: set TEST_DATABASE_URL or `pip install pgserver`",
        allow_module_level=True,
    )

from sqlalchemy import select  # noqa: E402

from src.config.database import async_session  # noqa: E402
from src.controllers.employee_timestamp_controller import (  # noqa: E402
    _compute_shift_metrics,
    _round_local_time,
)
from src.models.attendance_daily import AttendanceDaily, AttendanceDailyStatus  # noqa: E402
from src.models.employee_timestamp import ApprovalStatus, EmployeeTimestamp, TimestampType  # noqa: E402
from src.models.hr_schedule import CompanyHoliday, LeaveRequest, WorkShift  # noqa: E402
from src.schemas.hr_schema import WorkShiftCreate  # noqa: E402
from src.services import attendance_summary_service as summary  # noqa: E402
from tests.support import seed_world, teardown_world  # noqa: E402

BKK = ZoneInfo("Asia/Bangkok")
DAY_SHIFT = {
    "name": "Office",
    "startTime": "09:00",
    "endTime": "18:00",
    "graceMinutes": 15,
    "roundingMinutes": 0,
    "breakMinutes": 60,
    "breakWindows": [],
    "otThresholdMinutes": 0,
}


def _at(hhmm: str, *, day: int = 10, month: int = 3) -> datetime:
    h, m = (int(x) for x in hhmm.split(":"))
    return datetime(2026, month, day, h, m, tzinfo=BKK)


# ---------------------------------------------------------------- C2 pure metrics
def test_holiday_and_leave_suppress_late_and_ot():
    late = _compute_shift_metrics(
        _at("10:30"), DAY_SHIFT, is_checkout=False, is_holiday=True
    )
    assert late == (False, 0, 0, "Office")
    ot = _compute_shift_metrics(
        _at("20:00"), DAY_SHIFT, is_checkout=True, is_on_leave=True
    )
    assert ot == (False, 0, 0, "Office")


def test_ot_threshold_gates_overtime():
    gated = {**DAY_SHIFT, "otThresholdMinutes": 30}
    # 18:20 is within the 30-minute threshold → no OT
    assert _compute_shift_metrics(_at("18:20"), gated, is_checkout=True)[2] == 0
    # 18:45 → 45 past end − 30 threshold = 15 OT minutes
    assert _compute_shift_metrics(_at("18:45"), gated, is_checkout=True)[2] == 15


def test_rounding_minutes_snaps_before_late_check():
    rounded = {**DAY_SHIFT, "roundingMinutes": 15, "graceMinutes": 0}
    # 09:07 rounds to 09:00 → on time
    assert _compute_shift_metrics(_at("09:07"), rounded, is_checkout=False)[:2] == (False, 0)
    # 09:08 rounds to 09:15 → 15 minutes late from 09:00
    assert _compute_shift_metrics(_at("09:08"), rounded, is_checkout=False)[:2] == (True, 15)


def test_round_local_time_helper():
    assert _round_local_time(_at("09:07"), 15).minute == 0
    assert _round_local_time(_at("09:08"), 15).minute == 15
    assert _round_local_time(_at("09:07"), 0).minute == 7


def test_work_shift_schema_rejects_bad_hhmm():
    with pytest.raises(Exception):
        WorkShiftCreate(name="Bad", startTime="9:00", endTime="18:00")
    ok = WorkShiftCreate(name="Ok", startTime="09:00", endTime="18:30", breakMinutes=45)
    assert ok.breakMinutes == 45


# ---------------------------------------------------------------- C1 recompute (DB)
@pytest_asyncio.fixture
async def world():
    w = await seed_world()
    yield w
    await teardown_world(w)


async def _seed_shift(company_id, **over):
    ws = WorkShift(
        companyId=company_id,
        name=over.get("name", "Office"),
        startTime=over.get("startTime", "09:00"),
        endTime=over.get("endTime", "18:00"),
        graceMinutes=over.get("graceMinutes", 15),
        roundingMinutes=over.get("roundingMinutes", 0),
        breakMinutes=over.get("breakMinutes", 60),
        breakWindows=over.get("breakWindows", []),
        otThresholdMinutes=over.get("otThresholdMinutes", 0),
        isDefault=True,
    )
    async with async_session() as db:
        db.add(ws)
        await db.commit()
        await db.refresh(ws)
        return ws


@pytest.mark.asyncio
async def test_recompute_present_from_punches(world):
    await _seed_shift(world.a.company_id)
    emp_id = world.a.employee_employment.company_employeeId
    company_id = world.a.company_id
    work_date = date(2026, 3, 10)
    tz = BKK
    first = datetime(2026, 3, 10, 9, 20, tzinfo=tz)
    last = datetime(2026, 3, 10, 18, 45, tzinfo=tz)

    async with async_session() as db:
        db.add(
            EmployeeTimestamp(
                company_employeeId=emp_id,
                companyId=company_id,
                timestamp=first,
                timestampType=TimestampType.CHECK_IN,
                approvalStatus=ApprovalStatus.NONE.value,
                latitude=13.75,
                longitude=100.5,
                isLate=True,
                lateMinutes=20,
                overtimeMinutes=0,
                shiftName="Office",
            )
        )
        db.add(
            EmployeeTimestamp(
                company_employeeId=emp_id,
                companyId=company_id,
                timestamp=last,
                timestampType=TimestampType.CHECK_OUT,
                approvalStatus=ApprovalStatus.NONE.value,
                latitude=13.75,
                longitude=100.5,
                isLate=False,
                lateMinutes=0,
                overtimeMinutes=45,
                shiftName="Office",
            )
        )
        await db.commit()

        row = await summary.recompute_daily(company_id, emp_id, work_date, db)
        assert row.status == AttendanceDailyStatus.PRESENT.value
        assert row.firstIn is not None and row.lastOut is not None
        assert row.lateMinutes == 20
        assert row.otMinutes == 45
        # 9:20 → 18:45 = 565 minutes − 60 break = 505
        assert row.workMinutes == 505
        assert row.breakMinutes == 60


@pytest.mark.asyncio
async def test_recompute_holiday_clears_late_ot(world):
    await _seed_shift(world.a.company_id)
    emp_id = world.a.employee_employment.company_employeeId
    company_id = world.a.company_id
    work_date = date(2026, 4, 13)

    async with async_session() as db:
        db.add(CompanyHoliday(companyId=company_id, holidayDate=work_date, name="Songkran"))
        db.add(
            EmployeeTimestamp(
                company_employeeId=emp_id,
                companyId=company_id,
                timestamp=datetime(2026, 4, 13, 10, 0, tzinfo=BKK),
                timestampType=TimestampType.CHECK_IN,
                approvalStatus=ApprovalStatus.NONE.value,
                latitude=13.75,
                longitude=100.5,
                isLate=True,
                lateMinutes=60,
                overtimeMinutes=0,
            )
        )
        await db.commit()
        row = await summary.recompute_daily(company_id, emp_id, work_date, db)
        assert row.status == AttendanceDailyStatus.HOLIDAY.value
        assert row.lateMinutes == 0
        assert row.otMinutes == 0


@pytest.mark.asyncio
async def test_recompute_approved_leave_status(world):
    await _seed_shift(world.a.company_id)
    emp_id = world.a.employee_employment.company_employeeId
    company_id = world.a.company_id
    work_date = date(2026, 5, 1)

    async with async_session() as db:
        db.add(
            LeaveRequest(
                companyId=company_id,
                company_employeeId=emp_id,
                leaveType="ANNUAL",
                startDate=work_date,
                endDate=work_date + timedelta(days=2),
                status="APPROVED",
            )
        )
        await db.commit()
        row = await summary.recompute_daily(company_id, emp_id, work_date, db)
        assert row.status == AttendanceDailyStatus.LEAVE.value
        assert row.lateMinutes == 0
        assert row.firstIn is None


@pytest.mark.asyncio
async def test_recompute_absent_when_no_punches(world):
    await _seed_shift(world.a.company_id)
    emp_id = world.a.employee_employment.company_employeeId
    company_id = world.a.company_id
    work_date = date(2026, 6, 1)

    async with async_session() as db:
        row = await summary.recompute_daily(company_id, emp_id, work_date, db)
        assert row.status == AttendanceDailyStatus.ABSENT.value
        assert row.workMinutes == 0
        # Upsert is idempotent
        again = await summary.recompute_daily(company_id, emp_id, work_date, db)
        assert again.id == row.id
        found = (
            await db.execute(
                select(AttendanceDaily).where(
                    AttendanceDaily.companyId == company_id,
                    AttendanceDaily.employeeId == emp_id,
                    AttendanceDaily.workDate == work_date,
                )
            )
        ).scalars().all()
        assert len(found) == 1


@pytest.mark.asyncio
async def test_metrics_consult_holiday_via_flags(world):
    """Integration: holiday lookup helpers feed _compute_shift_metrics correctly."""
    company_id = world.a.company_id
    emp_id = world.a.employee_employment.company_employeeId
    work_date = date(2026, 7, 28)

    async with async_session() as db:
        db.add(CompanyHoliday(companyId=company_id, holidayDate=work_date, name="Asalha"))
        await db.commit()
        is_h, is_l = await summary.is_company_holiday(db, company_id, work_date), False
        assert is_h is True
        metrics = _compute_shift_metrics(
            datetime(2026, 7, 28, 10, 0, tzinfo=BKK),
            DAY_SHIFT,
            is_checkout=False,
            is_holiday=is_h,
            is_on_leave=is_l,
        )
        assert metrics[:3] == (False, 0, 0)

        on_leave = await summary.is_on_approved_leave(db, company_id, emp_id, work_date)
        assert on_leave is False
