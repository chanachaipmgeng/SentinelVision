"""C1: recompute ``attendance_daily`` for one (company, employee, Asia/Bangkok work date).

Called from punch create/approve hooks, leave/holiday mutations, and the nightly worker job.
"""
from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config.database import async_session
from ..models.attendance_daily import AttendanceDaily, AttendanceDailyStatus
from ..models.company_employee import CompanyEmployee
from ..models.employee_timestamp import ApprovalStatus, EmployeeTimestamp, TimestampType
from ..models.hr_schedule import CompanyHoliday, LeaveRequest

logger = logging.getLogger("dpu.attendance_summary")


def bangkok_tz():
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo("Asia/Bangkok")
    except Exception:  # pragma: no cover
        return timezone(timedelta(hours=7))


def work_date_for(ts: datetime) -> date:
    """Asia/Bangkok calendar date for a punch timestamp."""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(bangkok_tz()).date()


def _day_window_utc(work_date: date) -> tuple[datetime, datetime]:
    """[start, end) of the Bangkok work day expressed as aware datetimes."""
    tz = bangkok_tz()
    start_local = datetime(work_date.year, work_date.month, work_date.day, tzinfo=tz)
    end_local = start_local + timedelta(days=1)
    return start_local, end_local


async def is_company_holiday(
    db: AsyncSession, company_id: UUID, work_date: date
) -> bool:
    row = (
        await db.execute(
            select(CompanyHoliday.holidayId)
            .where(
                CompanyHoliday.companyId == company_id,
                CompanyHoliday.holidayDate == work_date,
                CompanyHoliday.deletedAt.is_(None),
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    return row is not None


async def is_on_approved_leave(
    db: AsyncSession, company_id: UUID, employee_id: UUID, work_date: date
) -> bool:
    row = (
        await db.execute(
            select(LeaveRequest.leaveId)
            .where(
                LeaveRequest.companyId == company_id,
                LeaveRequest.company_employeeId == employee_id,
                LeaveRequest.startDate <= work_date,
                LeaveRequest.endDate >= work_date,
                or_(
                    LeaveRequest.status == "APPROVED",
                    LeaveRequest.status == "1",
                ),
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    return row is not None


def _is_check_in(ts: EmployeeTimestamp) -> bool:
    t = ts.timestampType
    val = int(getattr(t, "value", t) if t is not None else -1)
    if val == TimestampType.CHECK_IN.value:
        return True
    # Approved geofence warnings become CHECK_IN after approval; also count APPROVED warnings.
    if val == TimestampType.WARNING.value:
        status = getattr(ts, "approvalStatus", None)
        return status in (ApprovalStatus.APPROVED, ApprovalStatus.APPROVED.value, "APPROVED")
    return False


def _is_check_out(ts: EmployeeTimestamp) -> bool:
    t = ts.timestampType
    val = int(getattr(t, "value", t) if t is not None else -1)
    return val == TimestampType.CHECK_OUT.value


async def recompute_daily(
    company_id: UUID,
    employee_id: UUID,
    work_date: date,
    db: AsyncSession,
    *,
    commit: bool = True,
) -> AttendanceDaily:
    """Upsert the daily summary for one employee on one Bangkok work date."""
    from ..controllers.employee_timestamp_controller import (
        _compute_shift_metrics,
        _resolve_employee_shift,
    )

    holiday = await is_company_holiday(db, company_id, work_date)
    on_leave = await is_on_approved_leave(db, company_id, employee_id, work_date)

    window_start, window_end = _day_window_utc(work_date)
    punches = (
        await db.execute(
            select(EmployeeTimestamp)
            .where(
                EmployeeTimestamp.companyId == company_id,
                EmployeeTimestamp.company_employeeId == employee_id,
                EmployeeTimestamp.timestamp >= window_start,
                EmployeeTimestamp.timestamp < window_end,
            )
            .order_by(EmployeeTimestamp.timestamp.asc())
        )
    ).scalars().all()

    # Exclude rejected / disapproved punches from the summary.
    usable = [
        p
        for p in punches
        if getattr(p, "approvalStatus", None)
        not in (ApprovalStatus.REJECTED, ApprovalStatus.REJECTED.value, "REJECTED")
        and int(getattr(p.timestampType, "value", p.timestampType) or -1)
        != TimestampType.DISAPPROVE.value
    ]

    first_in: Optional[datetime] = None
    last_out: Optional[datetime] = None
    late_minutes = 0
    ot_minutes = 0

    for p in usable:
        if _is_check_in(p) and first_in is None:
            first_in = p.timestamp
            late_minutes = max(late_minutes, int(getattr(p, "lateMinutes", 0) or 0))
        if _is_check_out(p):
            last_out = p.timestamp
            ot_minutes = max(ot_minutes, int(getattr(p, "overtimeMinutes", 0) or 0))

    emp = (
        await db.execute(
            select(CompanyEmployee)
            .where(CompanyEmployee.company_employeeId == employee_id)
            .options(selectinload(CompanyEmployee.department))
        )
    ).scalar_one_or_none()
    if emp is not None:
        shift = await _resolve_employee_shift(company_id, emp, db)
    else:
        shift = {}

    break_minutes = max(0, int(shift.get("breakMinutes", 0) or 0))
    # Prefer explicit break windows sum when present.
    windows = shift.get("breakWindows") or []
    if isinstance(windows, list) and windows:
        from ..controllers.employee_timestamp_controller import _parse_hhmm

        total = 0
        for w in windows:
            if not isinstance(w, dict):
                continue
            sh, sm = _parse_hhmm(w.get("start", "00:00"), 0, 0)
            eh, em = _parse_hhmm(w.get("end", "00:00"), 0, 0)
            total += max(0, (eh * 60 + em) - (sh * 60 + sm))
        if total > 0:
            break_minutes = total

    # Holiday / leave override late & OT (C2); status takes precedence over punches.
    if holiday:
        status = AttendanceDailyStatus.HOLIDAY.value
        late_minutes = 0
        ot_minutes = 0
    elif on_leave:
        status = AttendanceDailyStatus.LEAVE.value
        late_minutes = 0
        ot_minutes = 0
    elif first_in is not None or last_out is not None:
        status = AttendanceDailyStatus.PRESENT.value
    else:
        status = AttendanceDailyStatus.ABSENT.value

    work_minutes = 0
    if first_in is not None and last_out is not None and last_out > first_in:
        span = int((last_out - first_in).total_seconds() // 60)
        work_minutes = max(0, span - break_minutes)

    # If punches lack late/OT (e.g. imported) but we have a check-in, recompute from shift.
    if status == AttendanceDailyStatus.PRESENT.value and first_in is not None and late_minutes == 0:
        local = first_in.astimezone(bangkok_tz()) if first_in.tzinfo else first_in.replace(tzinfo=timezone.utc).astimezone(bangkok_tz())
        _late_flag, late_minutes, _, _ = _compute_shift_metrics(
            local, shift, is_checkout=False, is_holiday=holiday, is_on_leave=on_leave
        )
    if status == AttendanceDailyStatus.PRESENT.value and last_out is not None and ot_minutes == 0:
        local = last_out.astimezone(bangkok_tz()) if last_out.tzinfo else last_out.replace(tzinfo=timezone.utc).astimezone(bangkok_tz())
        _, _, ot_minutes, _ = _compute_shift_metrics(
            local, shift, is_checkout=True, is_holiday=holiday, is_on_leave=on_leave
        )

    if holiday or on_leave:
        late_minutes = 0
        ot_minutes = 0

    existing = (
        await db.execute(
            select(AttendanceDaily).where(
                AttendanceDaily.companyId == company_id,
                AttendanceDaily.employeeId == employee_id,
                AttendanceDaily.workDate == work_date,
            )
        )
    ).scalar_one_or_none()

    if existing is None:
        existing = AttendanceDaily(
            id=uuid.uuid4(),
            companyId=company_id,
            employeeId=employee_id,
            workDate=work_date,
        )
        db.add(existing)

    existing.firstIn = first_in
    existing.lastOut = last_out
    existing.workMinutes = int(work_minutes)
    existing.breakMinutes = int(break_minutes)
    existing.lateMinutes = int(late_minutes)
    existing.otMinutes = int(ot_minutes)
    existing.status = status
    existing.updatedAt = datetime.now(timezone.utc)

    if commit:
        await db.commit()
        await db.refresh(existing)
    else:
        await db.flush()

    return existing


async def recompute_daily_safe(
    company_id: UUID,
    employee_id: UUID,
    work_date: date,
    db: Optional[AsyncSession] = None,
) -> None:
    """Fire-and-forget friendly wrapper — never raises into the request path."""
    try:
        if db is not None:
            await recompute_daily(company_id, employee_id, work_date, db, commit=True)
            return
        async with async_session() as session:
            await recompute_daily(company_id, employee_id, work_date, session, commit=True)
    except Exception:
        logger.exception(
            "recompute_daily failed company=%s emp=%s date=%s",
            company_id,
            employee_id,
            work_date,
        )


async def recompute_for_punch(
    company_id: UUID,
    employee_id: UUID,
    punch_at: Optional[datetime],
    db: AsyncSession,
) -> None:
    if punch_at is None:
        punch_at = datetime.now(timezone.utc)
    await recompute_daily_safe(company_id, employee_id, work_date_for(punch_at), db)


async def recompute_leave_range(
    company_id: UUID,
    employee_id: UUID,
    start: date,
    end: date,
    db: AsyncSession,
) -> int:
    """Recompute every day in [start, end] inclusive for one employee."""
    if end < start:
        start, end = end, start
    n = 0
    cur = start
    while cur <= end:
        await recompute_daily(company_id, employee_id, cur, db, commit=False)
        n += 1
        cur += timedelta(days=1)
    await db.commit()
    return n


async def recompute_company_holiday(
    company_id: UUID, work_date: date, db: AsyncSession
) -> int:
    """Recompute the holiday date for every active employee in the company."""
    emps: list[UUID] = list(
        (
            await db.execute(
                select(CompanyEmployee.company_employeeId).where(
                    CompanyEmployee.companyId == company_id,
                    CompanyEmployee.deletedAt.is_(None),
                )
            )
        ).scalars().all()
    )
    for emp_id in emps:
        await recompute_daily(company_id, emp_id, work_date, db, commit=False)
    await db.commit()
    return len(emps)


async def recompute_yesterday_all(*, lookback_days: int = 1) -> dict:
    """Nightly worker: recompute yesterday (Bangkok) for every active employee.

    ``lookback_days`` > 1 also refreshes the prior N-1 days (catch-up after downtime).
    """
    tz = bangkok_tz()
    today = datetime.now(tz).date()
    total = 0
    companies = 0
    async with async_session() as db:
        emp_rows = (
            await db.execute(
                select(CompanyEmployee.companyId, CompanyEmployee.company_employeeId).where(
                    CompanyEmployee.deletedAt.is_(None)
                )
            )
        ).all()
        company_ids = {row[0] for row in emp_rows}
        companies = len(company_ids)
        for offset in range(1, max(1, lookback_days) + 1):
            work_date = today - timedelta(days=offset)
            for company_id, emp_id in emp_rows:
                await recompute_daily(company_id, emp_id, work_date, db, commit=False)
                total += 1
            await db.commit()
    return {"rows": total, "companies": companies, "lookbackDays": lookback_days}
