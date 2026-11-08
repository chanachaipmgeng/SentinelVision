"""F4: Emergency muster roll enriched with C1 ``attendance_daily`` + open presence."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.attendance_daily import AttendanceDaily, AttendanceDailyStatus
from ..models.company_employee import CompanyEmployee
from ..models.employee_timestamp import EmployeeTimestamp, TimestampType
from ..models.sentinel import SentinelIncidentLog


def bangkok_tz():
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo("Asia/Bangkok")
    except Exception:  # pragma: no cover
        return timezone(timedelta(hours=7))


def _person(
    *,
    subject_id: str,
    full_name: str,
    badge_code: str,
    category: str,
    zone_or_location: str,
    last_seen_at: Any,
    source: str,
) -> dict[str, Any]:
    return {
        "subjectId": subject_id,
        "fullName": full_name,
        "badgeCode": badge_code,
        "category": category,
        "zoneOrLocation": zone_or_location,
        "lastSeenAt": last_seen_at,
        "source": source,
    }


def _emp_name(emp: CompanyEmployee) -> str:
    m = emp.member
    if m:
        name = f"{m.firstName or ''} {m.lastName or ''}".strip()
        if name:
            return name
    return emp.employeeId or "Employee"


async def build_muster_roll(
    db: AsyncSession,
    company_id: UUID,
    *,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """People on-prem today: PRESENT daily rows and/or open CHECK_IN, plus visitor feed.

    Returns a pagination-friendly payload::

        { "items": [...], "total": N, "limit": L, "offset": O, "workDate": "YYYY-MM-DD" }
    """
    safe_limit = min(max(1, int(limit or 100)), 500)
    safe_offset = max(0, int(offset or 0))

    tz = bangkok_tz()
    now_local = datetime.now(tz)
    work_date = now_local.date()
    day_start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end_local = day_start_local + timedelta(days=1)
    day_start_utc = day_start_local.astimezone(timezone.utc)
    day_end_utc = day_end_local.astimezone(timezone.utc)
    # Naive UTC for columns that historically store without tz (EmployeeTimestamp).
    day_start_naive = day_start_utc.replace(tzinfo=None)
    day_end_naive = day_end_utc.replace(tzinfo=None)

    by_id: dict[str, dict[str, Any]] = {}

    # --- C1: attendance_daily PRESENT for Bangkok today ---
    present_rows = (
        await db.execute(
            select(AttendanceDaily, CompanyEmployee)
            .join(
                CompanyEmployee,
                CompanyEmployee.company_employeeId == AttendanceDaily.employeeId,
            )
            .options(selectinload(CompanyEmployee.member))
            .where(
                AttendanceDaily.companyId == company_id,
                AttendanceDaily.workDate == work_date,
                AttendanceDaily.status == AttendanceDailyStatus.PRESENT.value,
                CompanyEmployee.deletedAt.is_(None),
            )
        )
    ).all()

    for daily, emp in present_rows:
        emp_id = str(emp.company_employeeId)
        by_id[emp_id] = _person(
            subject_id=emp_id,
            full_name=_emp_name(emp),
            badge_code=emp.employeeId or "-",
            category="EMPLOYEE",
            zone_or_location="Attendance (PRESENT)",
            last_seen_at=daily.lastOut or daily.firstIn or daily.updatedAt or daily.createdAt,
            source="attendance_daily",
        )

    # --- Open presence: CHECK_IN today without a later CHECK_OUT ---
    punches = (
        await db.execute(
            select(EmployeeTimestamp)
            .options(
                selectinload(EmployeeTimestamp.company_employee).selectinload(
                    CompanyEmployee.member
                )
            )
            .where(
                EmployeeTimestamp.companyId == company_id,
                EmployeeTimestamp.timestamp >= day_start_naive,
                EmployeeTimestamp.timestamp < day_end_naive,
            )
            .order_by(EmployeeTimestamp.timestamp.asc())
        )
    ).scalars().all()

    last_punch_by_emp: dict[str, EmployeeTimestamp] = {}
    for ts in punches:
        emp = ts.company_employee
        if not emp:
            continue
        last_punch_by_emp[str(emp.company_employeeId)] = ts

    for emp_id, ts in last_punch_by_emp.items():
        punch_type = ts.timestampType
        is_check_in = punch_type == TimestampType.CHECK_IN or (
            getattr(punch_type, "value", punch_type) == TimestampType.CHECK_IN.value
            if punch_type is not None
            else False
        )
        if not is_check_in:
            # Last punch is CHECK_OUT (or other) → not open presence; keep PRESENT if already present.
            continue
        emp = ts.company_employee
        if not emp:
            continue
        existing = by_id.get(emp_id)
        person = _person(
            subject_id=emp_id,
            full_name=_emp_name(emp),
            badge_code=emp.employeeId or "-",
            category="EMPLOYEE",
            zone_or_location=ts.locationName or "Main Kiosk",
            last_seen_at=ts.timestamp,
            source="open_presence" if not existing else "attendance_daily+open_presence",
        )
        by_id[emp_id] = person

    # --- Visitors / VIP / event check-ins from today's incident feed (existing overview) ---
    visitor_logs = (
        await db.execute(
            select(SentinelIncidentLog)
            .where(
                SentinelIncidentLog.companyId == company_id,
                SentinelIncidentLog.occurredAt >= day_start_local,
                SentinelIncidentLog.eventType.in_(
                    ["ACCESS_GRANTED", "VISITOR_CHECKIN", "VIP_ARRIVAL", "EVENT_CHECKIN"]
                ),
            )
            .order_by(SentinelIncidentLog.occurredAt.desc())
            .limit(200)
        )
    ).scalars().all()

    seen_ident: set[str] = set()
    for vlog in visitor_logs:
        # Skip pure employee access rows already covered by attendance/presence.
        if (vlog.identityType or "").upper() == "EMPLOYEE" and vlog.memberId:
            continue
        key = str(vlog.identityId or vlog.memberId or vlog.incidentId)
        if key in seen_ident or key in by_id:
            continue
        seen_ident.add(key)
        by_id[key] = _person(
            subject_id=key,
            full_name=vlog.subjectName or "Guest",
            badge_code=vlog.identityType or "VISITOR",
            category=vlog.identityType or "VISITOR",
            zone_or_location=vlog.zoneName or "Access Gate",
            last_seen_at=vlog.occurredAt,
            source="visitor_incident",
        )

    def _sort_key(p: dict[str, Any]) -> tuple:
        seen = p.get("lastSeenAt")
        if seen is None:
            return (0, "")
        if isinstance(seen, datetime):
            return (1, seen.isoformat())
        return (1, str(seen))

    ordered = sorted(by_id.values(), key=_sort_key, reverse=True)
    total = len(ordered)
    page = ordered[safe_offset : safe_offset + safe_limit]
    return {
        "items": page,
        "total": total,
        "limit": safe_limit,
        "offset": safe_offset,
        "workDate": work_date.isoformat(),
    }
