"""BL-08 Leave Policy & Thai Labor Law OT Rate Engine (1.0x, 1.5x, 2.0x, 3.0x)."""
from __future__ import annotations

from datetime import date
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.approvals_payroll import LeavePolicy, OtRatePolicy
from ..models.attendance_daily import AttendanceDaily
from ..models.company_employee import CompanyEmployee
from ..models.hr_schedule import CompanyHoliday, LeaveRequest


def compute_leave_units(
    start_d: date,
    end_d: date,
    leave_unit: str = "FULL_DAY",
    leave_hours: Optional[float] = None,
    daily_work_hours: float = 8.0,
) -> tuple[float, float]:
    """Return ``(days_equivalent, hours_equivalent)`` for a leave request."""
    unit = (leave_unit or "FULL_DAY").upper()
    if unit == "HALF_DAY":
        hours = float(leave_hours) if leave_hours and leave_hours > 0 else daily_work_hours / 2.0
        return round(hours / daily_work_hours, 4), round(hours, 2)
    if unit == "HOURLY":
        hours = max(0.5, float(leave_hours or 1.0))
        return round(hours / daily_work_hours, 4), round(hours, 2)
    days = float(max(1, (end_d - start_d).days + 1))
    return days, round(days * daily_work_hours, 2)


def compute_effective_quota(
    policy: LeavePolicy,
    hire_date: Optional[date],
    as_of: Optional[date] = None,
) -> float:
    """Resolve annual leave quota considering seniority tiers."""
    base = float(policy.annualQuotaDays or 0.0)
    tiers = policy.seniorityTiers or []
    if not hire_date or not isinstance(tiers, list):
        return base
    ref = as_of or date.today()
    years = max(0.0, (ref - hire_date).days / 365.25)
    best = base
    for tier in tiers:
        if not isinstance(tier, dict):
            continue
        min_y = float(tier.get("minYears") or 0)
        q = float(tier.get("quotaDays") or 0)
        if years >= min_y and q > best:
            best = q
    return best


async def get_or_default_ot_policy(db: AsyncSession, company_id: UUID) -> dict[str, Any]:
    row = (
        await db.execute(select(OtRatePolicy).where(OtRatePolicy.companyId == company_id))
    ).scalar_one_or_none()
    if row is None:
        return {
            "companyId": str(company_id),
            "normalOtRate": 1.0,
            "workdayOtRate": 1.5,
            "holidayWorkRate": 2.0,
            "holidayOtRate": 3.0,
            "dailyWorkMinutes": 480,
            "roundingMinutes": 15,
        }
    return {
        "policyId": str(row.policyId),
        "companyId": str(row.companyId),
        "normalOtRate": float(row.normalOtRate),
        "workdayOtRate": float(row.workdayOtRate),
        "holidayWorkRate": float(row.holidayWorkRate),
        "holidayOtRate": float(row.holidayOtRate),
        "dailyWorkMinutes": int(row.dailyWorkMinutes),
        "roundingMinutes": int(row.roundingMinutes),
    }


def classify_ot_minutes(
    work_minutes: int,
    ot_minutes: int,
    is_holiday: bool,
    is_weekend: bool,
    daily_work_minutes: int = 480,
) -> dict[str, int]:
    """Classify OT minutes into Thai labor law buckets (1.0x, 1.5x, 2.0x, 3.0x)."""
    ot = max(0, int(ot_minutes or 0))
    work = max(0, int(work_minutes or 0))
    if not (is_holiday or is_weekend):
        return {
            "ot10Minutes": 0,
            "ot15Minutes": ot,
            "ot20Minutes": 0,
            "ot30Minutes": 0,
        }

    # On holidays / weekly rest days: work within daily_work_minutes is 2.0x (or 1.0x regular),
    # overtime beyond daily_work_minutes is 3.0x.
    ot_20 = min(work, daily_work_minutes) if ot > 0 or work > 0 else 0
    ot_30 = max(0, ot - ot_20) if ot > daily_work_minutes else (ot if work >= daily_work_minutes else 0)
    if ot > 0 and ot_20 == 0 and ot_30 == 0:
        ot_20 = ot
    return {
        "ot10Minutes": 0,
        "ot15Minutes": 0,
        "ot20Minutes": ot_20,
        "ot30Minutes": ot_30,
    }


async def build_payroll_summary(
    db: AsyncSession,
    company_id: UUID,
    start_d: date,
    end_d: date,
    company_employee_id: Optional[UUID] = None,
) -> dict[str, Any]:
    """Aggregate attendance, late, absent, hourly leave, and 1.0x/1.5x/2.0x/3.0x OT."""
    ot_pol = await get_or_default_ot_policy(db, company_id)
    daily_work_mins = int(ot_pol.get("dailyWorkMinutes") or 480)

    holiday_rows = (
        await db.execute(
            select(CompanyHoliday.holidayDate).where(
                CompanyHoliday.companyId == company_id,
                CompanyHoliday.deletedAt.is_(None),
                CompanyHoliday.holidayDate >= start_d,
                CompanyHoliday.holidayDate <= end_d,
            )
        )
    ).scalars().all()
    holiday_dates = set(holiday_rows)

    emp_q = (
        select(CompanyEmployee)
        .where(CompanyEmployee.companyId == company_id, CompanyEmployee.deletedAt.is_(None))
        .options(selectinload(CompanyEmployee.member), selectinload(CompanyEmployee.department))
    )
    if company_employee_id:
        emp_q = emp_q.where(CompanyEmployee.company_employeeId == company_employee_id)
    emps = (await db.execute(emp_q)).scalars().all()

    daily_q = select(AttendanceDaily).where(
        AttendanceDaily.companyId == company_id,
        AttendanceDaily.workDate >= start_d,
        AttendanceDaily.workDate <= end_d,
    )
    if company_employee_id:
        daily_q = daily_q.where(AttendanceDaily.employeeId == company_employee_id)
    daily_rows = (await db.execute(daily_q)).scalars().all()

    leave_q = select(LeaveRequest).where(
        LeaveRequest.companyId == company_id,
        LeaveRequest.status == "APPROVED",
        LeaveRequest.startDate <= end_d,
        LeaveRequest.endDate >= start_d,
    )
    if company_employee_id:
        leave_q = leave_q.where(LeaveRequest.company_employeeId == company_employee_id)
    leave_rows = (await db.execute(leave_q)).scalars().all()

    summary: dict[UUID, dict[str, Any]] = {}
    for e in emps:
        m = e.member
        name = (
            f"{getattr(m, 'firstName', '') or ''} {getattr(m, 'lastName', '') or ''}".strip()
            if m
            else ""
        ) or (getattr(m, "username", "") if m else "")
        summary[e.company_employeeId] = {
            "company_employeeId": str(e.company_employeeId),
            "employeeId": e.employeeId or "",
            "employeeName": name,
            "department": (e.department.thName or e.department.engName or "") if e.department else "",
            "presentDays": 0,
            "absentDays": 0,
            "workMinutes": 0,
            "lateMinutes": 0,
            "leaveHours": 0.0,
            "ot10Minutes": 0,
            "ot15Minutes": 0,
            "ot20Minutes": 0,
            "ot30Minutes": 0,
            "weightedOtHours": 0.0,
        }

    for d in daily_rows:
        bucket = summary.get(d.employeeId)
        if bucket is None:
            continue
        st = (d.status or "").upper()
        if st in ("PRESENT", "LATE"):
            bucket["presentDays"] += 1
        elif st == "ABSENT":
            bucket["absentDays"] += 1
        w_mins = int(d.workMinutes or 0)
        ot_mins = int(d.otMinutes or 0)
        bucket["workMinutes"] += w_mins
        bucket["lateMinutes"] += int(d.lateMinutes or 0)

        is_hol = d.workDate in holiday_dates
        is_wknd = d.workDate.weekday() >= 5
        buckets = classify_ot_minutes(w_mins, ot_mins, is_hol, is_wknd, daily_work_mins)
        bucket["ot10Minutes"] += buckets["ot10Minutes"]
        bucket["ot15Minutes"] += buckets["ot15Minutes"]
        bucket["ot20Minutes"] += buckets["ot20Minutes"]
        bucket["ot30Minutes"] += buckets["ot30Minutes"]

    for lr in leave_rows:
        bucket = summary.get(lr.company_employeeId)
        if bucket is None:
            continue
        _, hrs = compute_leave_units(
            lr.startDate,
            lr.endDate,
            getattr(lr, "leaveUnit", "FULL_DAY"),
            getattr(lr, "leaveHours", None),
        )
        bucket["leaveHours"] = round(float(bucket["leaveHours"]) + hrs, 2)

    r10 = float(ot_pol["normalOtRate"])
    r15 = float(ot_pol["workdayOtRate"])
    r20 = float(ot_pol["holidayWorkRate"])
    r30 = float(ot_pol["holidayOtRate"])
    for b in summary.values():
        b["weightedOtHours"] = round(
            (b["ot10Minutes"] * r10 + b["ot15Minutes"] * r15 + b["ot20Minutes"] * r20 + b["ot30Minutes"] * r30)
            / 60.0,
            2,
        )

    items = list(summary.values())
    return {
        "companyId": str(company_id),
        "startDate": start_d.isoformat(),
        "endDate": end_d.isoformat(),
        "otPolicy": ot_pol,
        "items": items,
        "total": len(items),
    }
