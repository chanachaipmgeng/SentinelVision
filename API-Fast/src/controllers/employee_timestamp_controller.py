from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy import asc, desc, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from ..models.company_employee import CompanyEmployee
from ..models.company_location import CompanyLocation
from ..models.employee_timestamp import ApprovalStatus, EmployeeTimestamp, TimestampType
from ..models.hr_schedule import WorkShift
from ..models.member import Member
from ..models.system_setting import SystemSetting
from ..schemas.employee_timestamp_schema import EmployeeTimestampUpdate, TimestampApprovalAction
from ..schemas.page_schema import page_envelope
from ..utils.geolocation import get_distance_in_km

_TS_SORT_COLUMNS = {
    "timestamp": EmployeeTimestamp.timestamp,
    "timestampType": EmployeeTimestamp.timestampType,
    "approvalStatus": EmployeeTimestamp.approvalStatus,
}

DEFAULT_SHIFT = {
    "name": "กะปกติ (09:00 - 18:00)",
    "startTime": "09:00",
    "endTime": "18:00",
    "graceMinutes": 15,
    "roundingMinutes": 0,
    "breakMinutes": 0,
    "breakWindows": [],
    "otThresholdMinutes": 0,
    "isCrossMidnight": False,
}


def get_bangkok_tz():
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo("Asia/Bangkok")
    except Exception:
        return timezone(timedelta(hours=7))


def _shift_key(company_id: str | UUID) -> str:
    return f"shift:{company_id}"


async def get_company_shift_settings(companyId: str | UUID, db: AsyncSession) -> dict:
    row = await db.get(SystemSetting, _shift_key(companyId))
    if row and isinstance(row.value, dict):
        return {**DEFAULT_SHIFT, **row.value}
    return dict(DEFAULT_SHIFT)


async def update_company_shift_settings(companyId: str | UUID, payload: dict, db: AsyncSession) -> dict:
    key = _shift_key(companyId)
    row = await db.get(SystemSetting, key)
    clean = {
        "name": str(payload.get("name") or DEFAULT_SHIFT["name"]).strip(),
        "startTime": str(payload.get("startTime") or DEFAULT_SHIFT["startTime"]).strip(),
        "endTime": str(payload.get("endTime") or DEFAULT_SHIFT["endTime"]).strip(),
        "graceMinutes": max(0, int(payload.get("graceMinutes", DEFAULT_SHIFT["graceMinutes"]) or 0)),
        "roundingMinutes": max(0, int(payload.get("roundingMinutes", DEFAULT_SHIFT["roundingMinutes"]) or 0)),
        "breakMinutes": max(0, int(payload.get("breakMinutes", DEFAULT_SHIFT["breakMinutes"]) or 0)),
        "breakWindows": payload.get("breakWindows") if isinstance(payload.get("breakWindows"), list) else [],
        "otThresholdMinutes": max(
            0, int(payload.get("otThresholdMinutes", DEFAULT_SHIFT["otThresholdMinutes"]) or 0)
        ),
        "isCrossMidnight": bool(payload.get("isCrossMidnight", False)),
    }
    if row:
        row.value = clean
    else:
        db.add(SystemSetting(key=key, value=clean))
    await db.commit()
    return clean


def _shift_row_to_dict(ws: WorkShift) -> dict:
    windows = getattr(ws, "breakWindows", None) or []
    if not isinstance(windows, list):
        windows = []
    return {
        "shiftId": str(ws.shiftId),
        "name": ws.name,
        "startTime": ws.startTime,
        "endTime": ws.endTime,
        "graceMinutes": int(ws.graceMinutes or 0),
        "roundingMinutes": int(getattr(ws, "roundingMinutes", 0) or 0),
        "breakMinutes": int(getattr(ws, "breakMinutes", 0) or 0),
        "breakWindows": windows,
        "otThresholdMinutes": int(getattr(ws, "otThresholdMinutes", 0) or 0),
        "isCrossMidnight": bool(ws.isCrossMidnight),
        "isDefault": bool(ws.isDefault),
    }


async def _resolve_employee_shift(
    company_id: UUID,
    emp: Optional[CompanyEmployee],
    db: AsyncSession,
) -> dict:
    """Resolve work shift hierarchy: Employee -> Department -> Default WorkShift -> Company SystemSetting."""
    if emp is not None:
        emp_shift_id = getattr(emp, "shiftId", None)
        if emp_shift_id:
            ws = await db.get(WorkShift, emp_shift_id)
            if ws and ws.companyId == company_id and ws.deletedAt is None:
                return _shift_row_to_dict(ws)
        dept = getattr(emp, "department", None)
        dept_shift_id = getattr(dept, "shiftId", None) if dept else None
        if dept_shift_id:
            ws = await db.get(WorkShift, dept_shift_id)
            if ws and ws.companyId == company_id and ws.deletedAt is None:
                return _shift_row_to_dict(ws)

    default_ws = (
        await db.execute(
            select(WorkShift)
            .where(
                WorkShift.companyId == company_id,
                WorkShift.isDefault.is_(True),
                WorkShift.deletedAt.is_(None),
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if default_ws:
        return _shift_row_to_dict(default_ws)

    return await get_company_shift_settings(company_id, db)


def _parse_hhmm(val: str, default_h: int, default_m: int) -> tuple[int, int]:
    try:
        parts = str(val).strip().split(":")
        return int(parts[0]), int(parts[1])
    except Exception:
        return default_h, default_m


def _round_local_time(now_local: datetime, rounding_minutes: int) -> datetime:
    """Round punch time to the nearest ``rounding_minutes`` (no-op when 0)."""
    step = max(0, int(rounding_minutes or 0))
    if step <= 0:
        return now_local
    total = now_local.hour * 60 + now_local.minute
    rounded = int((total + step / 2) // step) * step
    # Clamp to same calendar day (24:00 → 23:59 equivalent minute 1439).
    rounded = min(rounded, 24 * 60 - 1)
    return now_local.replace(
        hour=rounded // 60, minute=rounded % 60, second=0, microsecond=0
    )


def _compute_shift_metrics(
    now_local: datetime,
    shift: dict,
    *,
    is_checkout: bool,
    is_holiday: bool = False,
    is_on_leave: bool = False,
) -> tuple[bool, int, int, str]:
    """Late / OT for a single punch against the resolved shift.

    C2: CompanyHoliday and approved LeaveRequest suppress late and OT entirely.
    ``roundingMinutes`` snaps the punch clock before comparison; ``otThresholdMinutes``
    gates OT so only minutes past (shift end + threshold) count.
    """
    shift_name = str(shift.get("name") or DEFAULT_SHIFT["name"])
    if is_holiday or is_on_leave:
        return False, 0, 0, shift_name

    rounding = max(0, int(shift.get("roundingMinutes", 0) or 0))
    clock = _round_local_time(now_local, rounding)

    sh, sm = _parse_hhmm(shift.get("startTime", "09:00"), 9, 0)
    eh, em = _parse_hhmm(shift.get("endTime", "18:00"), 18, 0)
    grace = max(0, int(shift.get("graceMinutes", 15) or 0))
    ot_threshold = max(0, int(shift.get("otThresholdMinutes", 0) or 0))
    cross_midnight = bool(shift.get("isCrossMidnight")) or (eh, em) < (sh, sm)

    shift_start = clock.replace(hour=sh, minute=sm, second=0, microsecond=0)
    shift_end = clock.replace(hour=eh, minute=em, second=0, microsecond=0)

    if cross_midnight:
        if is_checkout:
            if clock.hour >= 12:
                shift_end = shift_end + timedelta(days=1)
        else:
            if clock.hour < 12:
                shift_start = shift_start - timedelta(days=1)

    if is_checkout:
        ot_gate = shift_end + timedelta(minutes=ot_threshold)
        if clock > ot_gate:
            ot_mins = int((clock - shift_end).total_seconds() // 60) - ot_threshold
            return False, 0, max(0, ot_mins), shift_name
        return False, 0, 0, shift_name

    late_cutoff = shift_start + timedelta(minutes=grace)
    if clock > late_cutoff:
        late_mins = int((clock - shift_start).total_seconds() // 60)
        return True, max(1, late_mins), 0, shift_name
    return False, 0, 0, shift_name


async def _holiday_or_leave_flags(
    db: AsyncSession,
    company_id: UUID,
    employee_id: UUID,
    work_date,
) -> tuple[bool, bool]:
    from ..services.attendance_summary_service import is_company_holiday, is_on_approved_leave

    holiday = await is_company_holiday(db, company_id, work_date)
    on_leave = False if holiday else await is_on_approved_leave(db, company_id, employee_id, work_date)
    return holiday, on_leave


def _employee_brief(emp: Optional[CompanyEmployee]) -> Optional[dict]:
    if not emp:
        return None
    member = emp.member
    position = emp.position
    department = emp.department
    return {
        "member": {
            "memberId": member.memberId,
            "username": member.username,
            "email": member.email,
            "firstName": member.firstName,
            "lastName": member.lastName,
            "phoneNumber": getattr(member, "phoneNumber", None),
            "picture": getattr(member, "picture", None),
            "role": getattr(member, "role", None),
            "status": getattr(member, "status", None),
            "birthDate": getattr(member, "birthDate", None),
            "address": getattr(member, "address", None),
            "emergencyContactName": getattr(member, "emergencyContactName", None),
            "emergencyContactPhone": getattr(member, "emergencyContactPhone", None),
            "attachmentUrls": getattr(member, "attachmentUrls", None),
            "biometricConsentAt": getattr(member, "biometricConsentAt", None),
        }
        if member
        else None,
        "position": {
            "positionId": position.positionId,
            "thName": position.thName,
            "engName": position.engName,
        }
        if position
        else None,
        "department": {
            "departmentId": department.departmentId,
            "thName": department.thName,
            "engName": department.engName,
            "shiftId": getattr(department, "shiftId", None),
        }
        if department
        else None,
        "company_employeeId": emp.company_employeeId,
        "employeeId": emp.employeeId or "",
        "bossId": emp.bossId or "",
        "shiftId": getattr(emp, "shiftId", None),
    }


def _timestamp_payload(time: EmployeeTimestamp) -> dict:
    return {
        "employee": _employee_brief(time.company_employee),
        "company_employeeId": time.company_employeeId,
        "timestampType": time.timestampType,
        "locationName": time.locationName,
        "latitude": time.latitude,
        "longitude": time.longitude,
        "photoTimestamp": time.photoTimestamp,
        "timestampId": time.timestampId,
        "companyId": time.companyId,
        "timestamp": time.timestamp,
        "createdAt": time.createdAt,
        "updatedAt": time.updatedAt,
        "note": time.note,
        "approvalStatus": time.approvalStatus,
        "approvedBy": time.approvedBy,
        "approvedAt": time.approvedAt,
        "rejectReason": time.rejectReason,
        "isLate": bool(getattr(time, "isLate", False)),
        "lateMinutes": int(getattr(time, "lateMinutes", 0) or 0),
        "overtimeMinutes": int(getattr(time, "overtimeMinutes", 0) or 0),
        "shiftName": getattr(time, "shiftName", None),
    }


async def get_all_timestamps(
    companyId: str | UUID,
    db: AsyncSession,
    *,
    limit: int = 500,
    offset: int = 0,
    q: str | None = None,
    sort_by: str | None = None,
    sort_dir: str = "desc",
    paged: bool = False,
):
    return await search_timestamps(
        str(companyId),
        None,
        None,
        None,
        None,
        None,
        db,
        limit=limit,
        offset=offset,
        q=q,
        sort_by=sort_by,
        sort_dir=sort_dir,
        paged=paged,
    )


async def get_timestamp_by_id(timestampId: UUID, companyId: UUID, db: AsyncSession):
    result = await db.execute(
        select(EmployeeTimestamp)
        .where(
            EmployeeTimestamp.timestampId == timestampId,
            EmployeeTimestamp.companyId == companyId,
        )
        .options(
            selectinload(EmployeeTimestamp.company_employee).joinedload(CompanyEmployee.member),
            selectinload(EmployeeTimestamp.company_employee).joinedload(CompanyEmployee.position),
            selectinload(EmployeeTimestamp.company_employee).joinedload(CompanyEmployee.department),
        )
    )
    timestamp = result.scalar_one_or_none()
    if not timestamp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timestamp not found")
    return _timestamp_payload(timestamp)


def _is_null_island(lat: float, lon: float) -> bool:
    """Placeholder / failed geolocation often arrives as exactly 0,0."""
    try:
        return abs(float(lat)) < 1e-6 and abs(float(lon)) < 1e-6
    except (TypeError, ValueError):
        return True


_PUNCH_STATE_TYPES = (
    TimestampType.CHECK_IN,
    TimestampType.BREAK_OUT,
    TimestampType.BREAK_IN,
    TimestampType.CHECK_OUT,
)


def _parse_explicit_punch_type(requested_punch: Optional[str]) -> Optional[TimestampType]:
    """Map explicit kiosk/API punch strings to TimestampType. AUTO/unknown → None."""
    req = (requested_punch or "AUTO").strip().upper()
    if req in ("AUTO", "", "HYBRID"):
        return None
    if req in ("CHECK_OUT", "CHECKOUT", "OUT", "2"):
        return TimestampType.CHECK_OUT
    if req in ("CHECK_IN", "CHECKIN", "IN", "1"):
        return TimestampType.CHECK_IN
    if req in ("BREAK_OUT", "BREAKOUT", "BREAK-OUT", "4"):
        return TimestampType.BREAK_OUT
    if req in ("BREAK_IN", "BREAKIN", "BREAK-IN", "5"):
        return TimestampType.BREAK_IN
    return None


def _next_auto_punch_type(last: Optional[TimestampType]) -> TimestampType:
    """AUTO cycle: IN → BREAK_OUT → BREAK_IN → OUT (then stay OUT until next day/window)."""
    if last is None or last == TimestampType.CHECK_OUT:
        # After OUT, further AUTO punches in the same window stay OUT (walk-by re-punch).
        if last == TimestampType.CHECK_OUT:
            return TimestampType.CHECK_OUT
        return TimestampType.CHECK_IN
    if last == TimestampType.CHECK_IN:
        return TimestampType.BREAK_OUT
    if last == TimestampType.BREAK_OUT:
        return TimestampType.BREAK_IN
    if last == TimestampType.BREAK_IN:
        return TimestampType.CHECK_OUT
    return TimestampType.CHECK_IN


async def _resolve_hybrid_punch_type(
    db: AsyncSession,
    company_id: UUID,
    company_employee_id: UUID,
    requested_punch: Optional[str],
    now_local: datetime,
    *,
    is_cross_midnight: bool = False,
) -> TimestampType:
    """Resolve punch type: explicit modes honored; AUTO advances IN→BREAK_OUT→BREAK_IN→OUT."""
    explicit = _parse_explicit_punch_type(requested_punch)
    if explicit is not None:
        return explicit

    today_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    if is_cross_midnight and now_local.hour < 12:
        window_start = today_start - timedelta(hours=12)
    else:
        window_start = today_start
    tomorrow = today_start + timedelta(days=1)
    existing = await db.execute(
        select(EmployeeTimestamp.timestampType)
        .where(
            EmployeeTimestamp.companyId == company_id,
            EmployeeTimestamp.company_employeeId == company_employee_id,
            EmployeeTimestamp.timestamp >= window_start,
            EmployeeTimestamp.timestamp < tomorrow,
            EmployeeTimestamp.timestampType.in_(_PUNCH_STATE_TYPES),
        )
        .order_by(EmployeeTimestamp.timestamp.desc())
        .limit(1)
    )
    row = existing.first()
    last = row[0] if row else None
    if isinstance(last, str):
        try:
            last = TimestampType[last]
        except KeyError:
            last = None
    return _next_auto_punch_type(last)


async def create_timestamp(data: dict, companyId: UUID, db: AsyncSession):
    user_lat = data.get("latitude")
    user_lon = data.get("longitude")
    note = (data.get("note") or "").strip() if data.get("note") else ""
    requested_punch = data.get("punchType")

    if user_lat is None or user_lon is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Latitude and Longitude are required.",
        )
    if _is_null_island(user_lat, user_lon):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid GPS coordinates (0,0). Enable location / open kiosk via HTTPS.",
        )

    stmt = select(CompanyLocation).where(
        CompanyLocation.companyId == companyId,
        CompanyLocation.deletedAt.is_(None),
    )
    result = await db.execute(stmt)
    locations = result.scalars().all()

    is_in_area = False
    found_location_name = "Outside Registered Area"

    if locations:
        for loc in locations:
            distance = get_distance_in_km(user_lat, user_lon, loc.latitude, loc.longitude)
            if distance <= loc.radius:
                is_in_area = True
                found_location_name = loc.locationName
                break

    tz = get_bangkok_tz()
    now_local = datetime.now(tz)
    emp_id = UUID(str(data["company_employeeId"]))

    emp_res = await db.execute(
        select(CompanyEmployee)
        .where(
            CompanyEmployee.company_employeeId == emp_id,
            CompanyEmployee.companyId == companyId,
        )
        .options(
            selectinload(CompanyEmployee.member),
            selectinload(CompanyEmployee.company),
            selectinload(CompanyEmployee.position),
            selectinload(CompanyEmployee.department),
        )
    )
    company_employee = emp_res.scalar_one_or_none()
    if not company_employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company Employee not found")

    shift = await _resolve_employee_shift(companyId, company_employee, db)
    sh, sm = _parse_hhmm(shift.get("startTime", "09:00"), 9, 0)
    eh, em = _parse_hhmm(shift.get("endTime", "18:00"), 18, 0)
    is_cross_midnight = bool(shift.get("isCrossMidnight")) or (eh, em) < (sh, sm)

    resolved_type = await _resolve_hybrid_punch_type(
        db, companyId, emp_id, requested_punch, now_local, is_cross_midnight=is_cross_midnight
    )
    is_checkout = resolved_type == TimestampType.CHECK_OUT
    # Cross-midnight early-morning punches belong to the previous Bangkok work date.
    work_date = now_local.date()
    if is_cross_midnight and now_local.hour < 12:
        work_date = (now_local - timedelta(days=1)).date()
    # Late only on CHECK_IN; OT only on CHECK_OUT. Break punches skip both.
    apply_late_ot = resolved_type in (TimestampType.CHECK_IN, TimestampType.CHECK_OUT)
    if apply_late_ot:
        is_holiday, is_on_leave = await _holiday_or_leave_flags(db, companyId, emp_id, work_date)
        is_late, late_mins, ot_mins, shift_name = _compute_shift_metrics(
            now_local,
            shift,
            is_checkout=is_checkout,
            is_holiday=is_holiday,
            is_on_leave=is_on_leave,
        )
    else:
        is_late, late_mins, ot_mins = False, 0, 0
        shift_name = str(shift.get("name") or DEFAULT_SHIFT["name"])

    if is_in_area:
        data["timestampType"] = resolved_type
        data["approvalStatus"] = ApprovalStatus.NONE.value
    else:
        if not note:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Note is required when checking in outside registered area.",
            )
        data["timestampType"] = TimestampType.WARNING
        data["approvalStatus"] = ApprovalStatus.PENDING.value

    data["locationName"] = found_location_name
    data["companyId"] = companyId
    data["note"] = note or None
    data["isLate"] = is_late
    data["lateMinutes"] = late_mins
    data["overtimeMinutes"] = ot_mins
    data["shiftName"] = shift_name

    allowed = {
        "company_employeeId",
        "companyId",
        "timestampType",
        "locationName",
        "latitude",
        "longitude",
        "photoTimestamp",
        "note",
        "approvalStatus",
        "isLate",
        "lateMinutes",
        "overtimeMinutes",
        "shiftName",
    }
    clean = {k: v for k, v in data.items() if k in allowed}

    new_timestamp = EmployeeTimestamp(**clean)
    db.add(new_timestamp)
    await db.commit()
    await db.refresh(new_timestamp)

    new_timestamp.company_employee = company_employee
    payload_out = _timestamp_payload(new_timestamp)

    # C1: refresh daily summary for this Bangkok work date (also covers face finalize path).
    try:
        from ..services.attendance_summary_service import recompute_daily

        await recompute_daily(companyId, emp_id, work_date, db, commit=True)
    except Exception:
        pass

    # Emit signed outbound Payroll / ERP webhook event asynchronously
    try:
        import asyncio
        from ..services.notification_service import emit_company_webhook_event

        ts_type_val = int(getattr(new_timestamp.timestampType, "value", new_timestamp.timestampType))
        if ts_type_val == TimestampType.CHECK_OUT.value:
            event_name = "attendance.checked_out"
        elif ts_type_val == TimestampType.WARNING.value:
            event_name = "attendance.warning"
        elif ts_type_val == TimestampType.BREAK_OUT.value:
            event_name = "attendance.break_out"
        elif ts_type_val == TimestampType.BREAK_IN.value:
            event_name = "attendance.break_in"
        else:
            event_name = "attendance.checked_in"
        member_obj = company_employee.member
        full_name = (
            f"{getattr(member_obj, 'firstName', '') or ''} {getattr(member_obj, 'lastName', '') or ''}".strip()
            if member_obj
            else ""
        )
        webhook_data = {
            "timestampId": str(new_timestamp.timestampId),
            "company_employeeId": str(company_employee.company_employeeId),
            "employeeId": company_employee.employeeId or "",
            "employeeName": full_name,
            "timestampType": ts_type_val,
            "shiftName": shift_name,
            "isLate": bool(is_late),
            "lateMinutes": int(late_mins),
            "overtimeMinutes": int(ot_mins),
            "locationName": found_location_name,
            "timestamp": new_timestamp.timestamp.isoformat() if new_timestamp.timestamp else None,
        }
        asyncio.create_task(emit_company_webhook_event(companyId, event_name, webhook_data))
    except Exception:
        pass

    return payload_out


async def update_timestamp(
    timestampId: UUID, companyId: UUID, data: EmployeeTimestampUpdate, db: AsyncSession
):
    result = await db.execute(
        select(EmployeeTimestamp).where(
            EmployeeTimestamp.timestampId == timestampId,
            EmployeeTimestamp.companyId == companyId,
        )
    )
    timestamp = result.scalar_one_or_none()
    if not timestamp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timestamp not found")

    payload = data.dict(exclude_unset=True)
    for key, value in payload.items():
        setattr(timestamp, key, value)
    await db.commit()
    await db.refresh(timestamp)
    return timestamp


async def approve_or_reject_timestamp(
    timestampId: UUID,
    companyId: UUID,
    action: TimestampApprovalAction,
    db: AsyncSession,
    *,
    approved_by: Optional[UUID] = None,
):
    """Decide a geofence warning punch. ``approved_by`` must come from the JWT caller — never the body."""
    result = await db.execute(
        select(EmployeeTimestamp)
        .where(
            EmployeeTimestamp.timestampId == timestampId,
            EmployeeTimestamp.companyId == companyId,
        )
        .options(
            selectinload(EmployeeTimestamp.company_employee).joinedload(CompanyEmployee.member),
            selectinload(EmployeeTimestamp.company_employee).joinedload(CompanyEmployee.position),
            selectinload(EmployeeTimestamp.company_employee).joinedload(CompanyEmployee.department),
        )
    )
    timestamp = result.scalar_one_or_none()
    if not timestamp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timestamp not found")

    if timestamp.approvalStatus != ApprovalStatus.PENDING.value and timestamp.approvalStatus != ApprovalStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PENDING timestamps can be approved or rejected.",
        )

    subject = timestamp.company_employee
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found for timestamp")

    from ..models.member import Member
    from ..services.approval_gate import assert_can_approve_for_employee

    if approved_by is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization required")
    caller = await db.get(Member, approved_by)
    if caller is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization required")
    await assert_can_approve_for_employee(db, caller, companyId, subject)

    # Period lock: cannot decide punches whose Bangkok date falls in a locked payroll period.
    from ..services.payroll_period_service import assert_date_not_locked

    punch_day = timestamp.timestamp
    if punch_day is not None:
        if punch_day.tzinfo is None:
            punch_day = punch_day.replace(tzinfo=timezone.utc)
        await assert_date_not_locked(db, companyId, punch_day.astimezone(get_bangkok_tz()).date())

    if action.approve:
        timestamp.approvalStatus = ApprovalStatus.APPROVED.value
        timestamp.timestampType = TimestampType.CHECK_IN
        timestamp.rejectReason = None
    else:
        if not (action.rejectReason or "").strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="rejectReason is required when rejecting.",
            )
        timestamp.approvalStatus = ApprovalStatus.REJECTED.value
        timestamp.rejectReason = action.rejectReason.strip()
        timestamp.timestampType = TimestampType.DISAPPROVE

    # Ignore client-supplied action.approvedBy — JWT only.
    timestamp.approvedBy = approved_by
    timestamp.approvedAt = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(timestamp)
    try:
        from ..services.attendance_summary_service import recompute_for_punch

        await recompute_for_punch(
            companyId, timestamp.company_employeeId, timestamp.timestamp, db
        )
    except Exception:
        pass
    try:
        import asyncio
        from ..services.notification_service import emit_company_webhook_event, enqueue

        await enqueue(
            "approval.decided",
            "line",
            {"body": f"Timestamp {timestampId} {'approved' if action.approve else 'rejected'}"},
            company_id=str(companyId),
        )
        ev_name = "attendance.approved" if action.approve else "attendance.rejected"
        asyncio.create_task(
            emit_company_webhook_event(
                companyId,
                ev_name,
                {
                    "timestampId": str(timestamp.timestampId),
                    "company_employeeId": str(timestamp.company_employeeId),
                    "approvalStatus": timestamp.approvalStatus,
                    "approvedBy": str(timestamp.approvedBy) if timestamp.approvedBy else None,
                    "rejectReason": timestamp.rejectReason,
                },
            )
        )
    except Exception:
        pass
    return _timestamp_payload(timestamp)


async def delete_timestamp(timestampId: UUID, companyId: UUID, db: AsyncSession):
    result = await db.execute(
        select(EmployeeTimestamp).where(
            EmployeeTimestamp.timestampId == timestampId,
            EmployeeTimestamp.companyId == companyId,
        )
    )
    timestamp = result.scalar_one_or_none()
    if not timestamp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timestamp not found")
    await db.delete(timestamp)
    await db.commit()


async def search_timestamps(
    companyId: str,
    company_employeeId: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    timestampType: Optional[int] = None,
    approvalStatus: Optional[str] = None,
    db: AsyncSession = None,
    *,
    limit: int = 500,
    offset: int = 0,
    q: str | None = None,
    sort_by: str | None = None,
    sort_dir: str = "desc",
    paged: bool = False,
):
    safe_limit = min(max(1, int(limit or 500)), 5000)
    safe_offset = max(0, int(offset or 0))
    query = select(EmployeeTimestamp).where(EmployeeTimestamp.companyId == companyId)

    if start_date:
        query = query.where(EmployeeTimestamp.timestamp >= start_date)
    if end_date:
        query = query.where(EmployeeTimestamp.timestamp <= end_date)
    if company_employeeId:
        query = query.where(EmployeeTimestamp.company_employeeId == company_employeeId)
    if timestampType is not None:
        try:
            ts_enum = TimestampType(int(timestampType))
            query = query.where(EmployeeTimestamp.timestampType == ts_enum)
        except ValueError:
            query = query.where(EmployeeTimestamp.timestampType == timestampType)
    if approvalStatus:
        query = query.where(EmployeeTimestamp.approvalStatus == approvalStatus)

    needle = (q or "").strip()
    if needle:
        like = f"%{needle}%"
        query = (
            query.join(CompanyEmployee, EmployeeTimestamp.company_employeeId == CompanyEmployee.company_employeeId)
            .join(Member, CompanyEmployee.memberId == Member.memberId)
            .where(
                or_(
                    Member.firstName.ilike(like),
                    Member.lastName.ilike(like),
                    Member.username.ilike(like),
                    CompanyEmployee.employeeId.ilike(like),
                    EmployeeTimestamp.note.ilike(like),
                )
            )
        )

    count_stmt = select(func.count()).select_from(query.order_by(None).subquery())
    total = int((await db.execute(count_stmt)).scalar_one() or 0)

    sort_col = _TS_SORT_COLUMNS.get(sort_by or "", EmployeeTimestamp.timestamp)
    order = asc(sort_col) if (sort_dir or "").lower() == "asc" else desc(sort_col)
    query = query.order_by(order).offset(safe_offset).limit(safe_limit)

    result = await db.execute(
        query.options(
            selectinload(EmployeeTimestamp.company_employee).joinedload(CompanyEmployee.member),
            selectinload(EmployeeTimestamp.company_employee).joinedload(CompanyEmployee.position),
            selectinload(EmployeeTimestamp.company_employee).joinedload(CompanyEmployee.department),
        )
    )
    items = [_timestamp_payload(time) for time in result.unique().scalars().all()]
    if paged:
        return page_envelope(items, total=total, limit=safe_limit, offset=safe_offset)
    return items


def _type_label(ts_type) -> str:
    val = getattr(ts_type, "value", ts_type)
    if val == 1:
        return "เข้างาน (Check-In)"
    if val == 2:
        return "ออกงาน (Check-Out)"
    if val == 0:
        return "นอกพื้นที่ (Warning)"
    if val == 3:
        return "ไม่อนุมัติ (Absent)"
    if val == 4:
        return "พักนอก (Break-Out)"
    if val == 5:
        return "พักเข้า (Break-In)"
    return str(val)


def _format_export_rows(items: list[dict]) -> list[list[str]]:
    tz = get_bangkok_tz()
    rows: list[list[str]] = []
    for item in items:
        emp = item.get("employee") or {}
        member = emp.get("member") or {}
        dept = emp.get("department") or {}
        pos = emp.get("position") or {}
        full_name = f"{member.get('firstName') or ''} {member.get('lastName') or ''}".strip() or member.get("username") or "-"
        ts_val = item.get("timestamp")
        if isinstance(ts_val, datetime):
            local_dt = ts_val.astimezone(tz) if ts_val.tzinfo else ts_val.replace(tzinfo=timezone.utc).astimezone(tz)
            date_str = local_dt.strftime("%Y-%m-%d")
            time_str = local_dt.strftime("%H:%M:%S")
        else:
            date_str = str(ts_val or "")[:10]
            time_str = str(ts_val or "")[11:19]
        rows.append(
            [
                date_str,
                time_str,
                str(emp.get("employeeId") or ""),
                full_name,
                str(dept.get("thName") or dept.get("engName") or ""),
                str(pos.get("thName") or pos.get("engName") or ""),
                _type_label(item.get("timestampType")),
                str(item.get("shiftName") or ""),
                "สาย" if item.get("isLate") else "ปกติ",
                str(item.get("lateMinutes") or 0),
                str(item.get("overtimeMinutes") or 0),
                str(item.get("locationName") or ""),
                f"{item.get('latitude') or ''}, {item.get('longitude') or ''}",
                str(item.get("approvalStatus") or "NONE"),
                str(item.get("note") or ""),
            ]
        )
    return rows


EXPORT_HEADERS = [
    "วันที่",
    "เวลา",
    "รหัสพนักงาน",
    "ชื่อ-นามสกุล",
    "แผนก",
    "ตำแหน่ง",
    "ประเภทการลงเวลา",
    "กะการทำงาน",
    "สถานะการมาสาย",
    "นาทีที่สาย",
    "นาทีล่วงเวลา (OT)",
    "สถานที่",
    "พิกัด (Lat, Lng)",
    "สถานะอนุมัติ",
    "หมายเหตุ",
]


def build_timestamps_csv(items: list[dict]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(EXPORT_HEADERS)
    for row in _format_export_rows(items):
        writer.writerow(row)
    return ("\ufeff" + buf.getvalue()).encode("utf-8")


def build_timestamps_xlsx(items: list[dict]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Attendance Report"

    header_fill = PatternFill("solid", fgColor="0F766E")
    header_font = Font(color="FFFFFF", bold=True)

    for col_idx, header in enumerate(EXPORT_HEADERS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    rows = _format_export_rows(items)
    for row_idx, row in enumerate(rows, start=2):
        for col_idx, val in enumerate(row, start=1):
            ws.cell(row=row_idx, column=col_idx, value=val)

    widths = [14, 12, 16, 26, 20, 20, 22, 22, 16, 14, 16, 26, 24, 16, 30]
    for idx, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = width

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
