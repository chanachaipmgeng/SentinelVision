"""Phase 3 & 4 Enterprise HR Routes: Multi-Shift, Leave, Holidays, PDPA & Kiosk Device Tokens."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config.database import get_db
from ..config.settings import settings
from ..controllers import hr_controller
from ..models.company_employee import CompanyEmployee
from ..models.face_encoding import FaceEncoding
from ..models.approvals_payroll import (
    ApprovalDelegation,
    ApprovalPolicy,
    ApprovalRequestStatus,
    LeaveBalance,
    LeavePolicy,
    OtApprovalRequest,
    OtRatePolicy,
    PayrollPeriod,
    PayrollPeriodStatus,
    RegularizationRequest,
    ShiftSwapRequest,
)
from ..models.employee_timestamp import ApprovalStatus, EmployeeTimestamp
from ..models.hr_schedule import CompanyHoliday, LeaveRequest, ShiftRosterEntry, WorkShift
from ..models.member import Member
from ..schemas.hr_schema import (
    AssignShiftBody,
    CompanyHolidayCreate,
    LeaveApprovalBody,
    LeaveRequestCreate,
    WorkShiftCreate,
    WorkShiftUpdate,
)
from ..security.deps import (
    assert_member_company_access,
    assert_request_company_access,
    assert_request_company_membership,
    assert_request_permission,
)
from ..services.approval_gate import assert_can_approve_for_employee, can_approve_for_employee
from ..services.approval_chain_service import (
    advance_approval_step,
    get_company_approval_levels,
    level_label_for,
)
from ..services.attendance_summary_service import (
    recompute_company_holiday,
    recompute_leave_range,
)
from ..services.holiday_service import (
    SOURCE_CSV,
    SOURCE_ICAL,
    SOURCE_MANUAL,
    SOURCE_THAI_PRESET,
    list_active_holidays,
    parse_holiday_csv,
    parse_holiday_ical,
    serialize_holiday,
    thai_public_holidays,
    upsert_holidays,
)
from ..services.notification_service import emit_company_webhook_event
from ..services import pdpa_service
from ..services.payroll_period_service import (
    assert_date_not_locked,
    assert_range_not_locked,
    close_and_lock_period,
    serialize_period,
)

router = APIRouter()


def _leave_days(start_d: date, end_d: date) -> int:
    return (end_d - start_d).days + 1


async def _assert_no_leave_overlap(
    db: AsyncSession,
    company_id: UUID,
    emp_id: UUID,
    start_d: date,
    end_d: date,
    *,
    exclude_leave_id: Optional[UUID] = None,
) -> None:
    stmt = select(LeaveRequest).where(
        LeaveRequest.companyId == company_id,
        LeaveRequest.company_employeeId == emp_id,
        LeaveRequest.status.in_(("PENDING", "APPROVED")),
        LeaveRequest.startDate <= end_d,
        LeaveRequest.endDate >= start_d,
    )
    if exclude_leave_id:
        stmt = stmt.where(LeaveRequest.leaveId != exclude_leave_id)
    overlap = (await db.execute(stmt.limit(1))).scalar_one_or_none()
    if overlap is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Leave request overlaps an existing PENDING or APPROVED leave",
        )


async def _get_or_create_leave_balance(
    db: AsyncSession,
    company_id: UUID,
    emp_id: UUID,
    leave_type: str,
    year: int,
) -> LeaveBalance:
    row = (
        await db.execute(
            select(LeaveBalance).where(
                LeaveBalance.companyId == company_id,
                LeaveBalance.company_employeeId == emp_id,
                LeaveBalance.leaveType == leave_type,
                LeaveBalance.year == year,
            )
        )
    ).scalar_one_or_none()
    if row:
        return row
    row = LeaveBalance(
        companyId=company_id,
        company_employeeId=emp_id,
        leaveType=leave_type,
        year=year,
        entitledDays=0,
        usedDays=0,
    )
    db.add(row)
    await db.flush()
    return row


async def _assert_leave_balance_available(
    db: AsyncSession,
    company_id: UUID,
    emp_id: UUID,
    leave_type: str,
    start_d: date,
    end_d: date,
) -> None:
    days = float(_leave_days(start_d, end_d))
    bal = await _get_or_create_leave_balance(db, company_id, emp_id, leave_type, start_d.year)
    # If never configured (entitled=0), allow request but still track usage on approve.
    if float(bal.entitledDays or 0) <= 0:
        return
    if bal.remainingDays < days:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Insufficient leave balance: remaining {bal.remainingDays}, requested {days}",
        )


@router.get("/company/{companyId}/shifts")
async def list_company_shifts(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, "hr.shifts", companyId)
    return await hr_controller.list_shifts(companyId, db)


@router.post("/company/{companyId}/shifts")
async def create_company_shift(
    companyId: UUID,
    body: WorkShiftCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, "hr.shifts", companyId)
    return await hr_controller.create_shift(companyId, body, db)


@router.put("/company/{companyId}/shifts/{shiftId}")
async def update_company_shift(
    companyId: UUID,
    shiftId: UUID,
    body: WorkShiftUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, "hr.shifts", companyId)
    return await hr_controller.update_shift(companyId, shiftId, body, db)


@router.delete("/company/{companyId}/shifts/{shiftId}")
async def delete_company_shift(
    companyId: UUID,
    shiftId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, "hr.shifts", companyId)
    return await hr_controller.delete_shift(companyId, shiftId, db)


@router.put("/company/{companyId}/assign-shift")
async def assign_shift(
    companyId: UUID,
    body: AssignShiftBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Assign a shiftId (or None to clear) to a department or an employee."""
    await assert_request_company_access(request, db, companyId)
    return await hr_controller.assign_shift(companyId, body, db)


# ---------------------------------------------------------------------------
# Company Holidays
# ---------------------------------------------------------------------------
@router.get("/company/{companyId}/holidays")
async def list_company_holidays(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    start: Optional[date] = None,
    end: Optional[date] = None,
):
    """List active holidays. Optional ``start``/``end`` (YYYY-MM-DD) for metrics consumers (C2)."""
    await assert_request_permission(request, db, "hr.holidays", companyId)
    rows = await list_active_holidays(db, companyId, start=start, end=end)
    return [serialize_holiday(r) for r in rows]


@router.post("/company/{companyId}/holidays")
async def create_company_holiday(
    companyId: UUID,
    body: CompanyHolidayCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    raw_date = str(body.holidayDate or "").strip()[:10]
    try:
        parsed_date = date.fromisoformat(raw_date)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid holidayDate format") from None

    name = str(body.name or "").strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name is required")

    result = await upsert_holidays(
        db, companyId, [(parsed_date, name)], source=SOURCE_MANUAL
    )
    rows = await list_active_holidays(db, companyId, start=parsed_date, end=parsed_date)
    row = rows[0] if rows else None
    if not row:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Holiday save failed")
    try:
        await recompute_company_holiday(companyId, parsed_date, db)
    except Exception:
        pass
    payload = serialize_holiday(row)
    payload["upsert"] = result
    return payload


@router.post("/company/{companyId}/holidays/import")
async def import_company_holidays(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Import holidays from CSV or iCal (``.ics``).

    Accepts multipart (``file`` + optional ``format``) or JSON
    ``{"format":"csv"|"ical","content":"..."}``.
    """
    await assert_request_company_access(request, db, companyId)
    raw = ""
    filename = ""
    fmt = ""
    content_type = (request.headers.get("content-type") or "").lower()

    if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        upload = form.get("file")
        fmt = str(form.get("format") or "").strip().lower()
        text_val = form.get("text") or form.get("content")
        if upload is not None and hasattr(upload, "read"):
            filename = (getattr(upload, "filename", None) or "").lower()
            raw_bytes = await upload.read()
            raw = raw_bytes.decode("utf-8", errors="replace") if isinstance(raw_bytes, (bytes, bytearray)) else str(raw_bytes)
        elif text_val:
            raw = str(text_val)
    else:
        try:
            body = await request.json()
        except Exception:
            body = None
        if isinstance(body, dict):
            raw = str(body.get("content") or body.get("text") or "")
            fmt = str(body.get("format") or "").strip().lower()

    if not raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide file upload or text/content body",
        )

    if not fmt:
        if filename.endswith(".ics") or filename.endswith(".ical") or "BEGIN:VCALENDAR" in raw.upper():
            fmt = "ical"
        else:
            fmt = "csv"

    if fmt in ("ical", "ics"):
        items = parse_holiday_ical(raw)
        source = SOURCE_ICAL
    elif fmt == "csv":
        items = parse_holiday_csv(raw)
        source = SOURCE_CSV
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="format must be csv or ical",
        )

    if not items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No holiday rows found in import payload",
        )

    result = await upsert_holidays(db, companyId, items, source=source)
    for d, _name in items:
        try:
            await recompute_company_holiday(companyId, d, db)
        except Exception:
            pass
    return {"imported": len(items), **result}


@router.post("/company/{companyId}/holidays/thai-preset")
async def apply_thai_holiday_preset(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    year: Optional[int] = None,
):
    """Seed Thai public holidays for a year (default: current Asia/Bangkok year)."""
    await assert_request_company_access(request, db, companyId)
    year_val = year
    if year_val is None:
        try:
            body = await request.json()
            if isinstance(body, dict) and body.get("year") is not None:
                year_val = body.get("year")
        except Exception:
            year_val = None
    if year_val is None:
        try:
            from zoneinfo import ZoneInfo

            year_val = datetime.now(ZoneInfo("Asia/Bangkok")).year
        except Exception:
            year_val = datetime.now(timezone.utc).year
    try:
        year_i = int(year_val)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid year") from None
    if year_i < 2000 or year_i > 2100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="year out of range")

    items = thai_public_holidays(year_i)
    result = await upsert_holidays(db, companyId, items, source=SOURCE_THAI_PRESET)
    for d, _name in items:
        try:
            await recompute_company_holiday(companyId, d, db)
        except Exception:
            pass
    return {"year": year_i, "imported": len(items), **result}


@router.delete("/company/{companyId}/holidays/{holidayId}")
async def delete_company_holiday(
    companyId: UUID,
    holidayId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    row = await db.get(CompanyHoliday, holidayId)
    if not row or row.companyId != companyId or row.deletedAt is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Holiday not found")
    holiday_date = row.holidayDate
    row.deletedAt = datetime.now(timezone.utc)
    await db.commit()
    try:
        await recompute_company_holiday(companyId, holiday_date, db)
    except Exception:
        pass
    return {"deleted": True, "holidayId": str(holidayId)}


# ---------------------------------------------------------------------------
# Leave Requests & Approval Workflow
# ---------------------------------------------------------------------------
def _status_code_from_str(status_str: str) -> int:
    s = (status_str or "PENDING").upper()
    if s in ("APPROVED", "1"):
        return 1
    if s in ("REJECTED", "2"):
        return 2
    return 0


def _serialize_leave(lr: LeaveRequest, emp: Optional[CompanyEmployee]) -> dict:
    member = emp.member if emp else None
    dept = emp.department if emp else None
    full_name = (
        f"{getattr(member, 'firstName', '') or ''} {getattr(member, 'lastName', '') or ''}".strip()
        if member
        else ""
    ) or (getattr(member, "username", "") if member else "ไม่ทราบชื่อ")
    code = (emp.employeeId if emp else "") or ""
    return {
        "leaveId": str(lr.leaveId),
        "companyId": str(lr.companyId),
        "company_employeeId": str(lr.company_employeeId),
        "employeeId": code,
        "employeeCode": code,
        "employeeName": full_name,
        "department": (dept.thName if dept else "") or "",
        "leaveType": lr.leaveType,
        "leaveUnit": getattr(lr, "leaveUnit", "FULL_DAY") or "FULL_DAY",
        "leaveHours": getattr(lr, "leaveHours", None),
        "attachmentUrl": getattr(lr, "attachmentUrl", None),
        "startDate": lr.startDate.isoformat() if lr.startDate else None,
        "endDate": lr.endDate.isoformat() if lr.endDate else None,
        "reason": lr.reason or "",
        "status": _status_code_from_str(lr.status),
        "statusText": lr.status,
        "approvedBy": str(lr.approvedBy) if lr.approvedBy else None,
        "approvedAt": lr.approvedAt,
        "rejectReason": lr.rejectReason or "",
        "approvalLevel": int(getattr(lr, "approvalLevel", 1) or 1),
        "maxApprovalLevel": int(getattr(lr, "maxApprovalLevel", 1) or 1),
        "approvalHistory": list(getattr(lr, "approvalHistory", None) or []),
        "createdAt": lr.createdAt,
    }


@router.get("/company/{companyId}/leaves")
async def list_leave_requests(
    companyId: UUID,
    request: Request,
    status_filter: Optional[str] = None,
    company_employeeId: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    stmt = select(LeaveRequest).where(LeaveRequest.companyId == companyId)
    if status_filter:
        stmt = stmt.where(LeaveRequest.status == status_filter.upper())
    if company_employeeId:
        stmt = stmt.where(LeaveRequest.company_employeeId == company_employeeId)
    stmt = stmt.order_by(LeaveRequest.startDate.desc(), LeaveRequest.createdAt.desc()).limit(500)
    leaves = (await db.execute(stmt)).scalars().all()

    emp_ids = list({lr.company_employeeId for lr in leaves})
    emps_by_id: dict[UUID, CompanyEmployee] = {}
    if emp_ids:
        emp_rows = (
            await db.execute(
                select(CompanyEmployee)
                .where(CompanyEmployee.company_employeeId.in_(emp_ids))
                .options(
                    selectinload(CompanyEmployee.member),
                    selectinload(CompanyEmployee.department),
                )
            )
        ).scalars().all()
        emps_by_id = {e.company_employeeId: e for e in emp_rows}

    items = [_serialize_leave(lr, emps_by_id.get(lr.company_employeeId)) for lr in leaves]
    return {"items": items, "total": len(items)}


@router.post("/company/{companyId}/leaves")
async def create_leave_request(
    companyId: UUID,
    body: LeaveRequestCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    emp_id = body.company_employeeId
    emp = (
        await db.execute(
            select(CompanyEmployee)
            .where(
                CompanyEmployee.company_employeeId == emp_id,
                CompanyEmployee.companyId == companyId,
                CompanyEmployee.deletedAt.is_(None),
            )
            .options(
                selectinload(CompanyEmployee.member),
                selectinload(CompanyEmployee.department),
            )
        )
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found in company")

    try:
        start_d = date.fromisoformat(str(body.startDate or "")[:10])
        end_d = date.fromisoformat(str(body.endDate or "")[:10])
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Valid startDate and endDate are required") from None
    if end_d < start_d:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="endDate must be >= startDate")

    leave_type = str(body.leaveType or "ANNUAL").strip().upper()
    leave_unit = str(getattr(body, "leaveUnit", "FULL_DAY") or "FULL_DAY").strip().upper()
    leave_hours = getattr(body, "leaveHours", None)
    attachment_url = (getattr(body, "attachmentUrl", None) or "").strip() or None
    reason = str(body.reason or "").strip()
    auto_approve = bool(body.autoApprove)

    from ..services.ot_leave_engine_service import compute_leave_units

    days_equiv, hours_equiv = compute_leave_units(start_d, end_d, leave_unit, leave_hours)

    pol = (
        await db.execute(
            select(LeavePolicy).where(
                LeavePolicy.companyId == companyId,
                LeavePolicy.leaveType == leave_type,
                LeavePolicy.isActive.is_(True),
            )
        )
    ).scalar_one_or_none()
    if pol is not None:
        if leave_unit == "HALF_DAY" and not pol.allowHalfDay:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Half-day leave is not allowed for this leave type")
        if leave_unit == "HOURLY" and not pol.allowHourly:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Hourly leave is not allowed for this leave type")
        if pol.requireMedicalCert and days_equiv >= float(pol.medicalCertMinDays or 3.0) and not attachment_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Medical certificate attachment required for >= {pol.medicalCertMinDays} days",
            )

    await assert_range_not_locked(db, companyId, start_d, end_d)
    await _assert_no_leave_overlap(db, companyId, emp_id, start_d, end_d)
    await _assert_leave_balance_available(db, companyId, emp_id, leave_type, start_d, end_d)

    levels = await get_company_approval_levels(db, companyId, "LEAVE")
    lr = LeaveRequest(
        companyId=companyId,
        company_employeeId=emp_id,
        leaveType=leave_type,
        leaveUnit=leave_unit,
        leaveHours=hours_equiv if leave_unit in ("HALF_DAY", "HOURLY") else None,
        attachmentUrl=attachment_url,
        startDate=start_d,
        endDate=end_d,
        reason=reason,
        status="APPROVED" if auto_approve else "PENDING",
        approvalLevel=len(levels) if auto_approve else 1,
        maxApprovalLevel=len(levels),
        approvedAt=datetime.now(timezone.utc) if auto_approve else None,
    )
    db.add(lr)
    if auto_approve:
        bal = await _get_or_create_leave_balance(db, companyId, emp_id, leave_type, start_d.year)
        bal.usedDays = float(bal.usedDays or 0) + float(days_equiv)
    await db.commit()
    await db.refresh(lr)
    if auto_approve:
        try:
            await recompute_leave_range(companyId, emp_id, start_d, end_d, db)
        except Exception:
            pass
    return _serialize_leave(lr, emp)


@router.post("/company/{companyId}/leaves/{leaveId}/approval")
async def approve_or_reject_leave(
    companyId: UUID,
    leaveId: UUID,
    body: LeaveApprovalBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    caller = await assert_request_company_membership(request, db, companyId)
    lr = await db.get(LeaveRequest, leaveId)
    if not lr or lr.companyId != companyId:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave request not found")

    emp = (
        await db.execute(
            select(CompanyEmployee)
            .where(CompanyEmployee.company_employeeId == lr.company_employeeId)
            .options(
                selectinload(CompanyEmployee.member),
                selectinload(CompanyEmployee.department),
            )
        )
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    await assert_can_approve_for_employee(db, caller, companyId, emp)
    await assert_range_not_locked(db, companyId, lr.startDate, lr.endDate)

    if body.status is not None:
        st = body.status
        approve = st in (1, "1", "APPROVED", True)
    else:
        approve = bool(body.approve if body.approve is not None else True)

    prev = (lr.status or "").upper()
    is_final_approved = await advance_approval_step(
        db,
        lr,
        companyId,
        emp,
        caller,
        approve,
        body.rejectReason,
        "LEAVE",
    )
    if is_final_approved and prev != "APPROVED":
        from ..services.ot_leave_engine_service import compute_leave_units

        bal = await _get_or_create_leave_balance(
            db, companyId, lr.company_employeeId, lr.leaveType, lr.startDate.year
        )
        days, _ = compute_leave_units(
            lr.startDate,
            lr.endDate,
            getattr(lr, "leaveUnit", "FULL_DAY"),
            getattr(lr, "leaveHours", None),
        )
        if float(bal.entitledDays or 0) > 0 and bal.remainingDays < days:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Insufficient leave balance: remaining {bal.remainingDays}, requested {days}",
            )
        bal.usedDays = float(bal.usedDays or 0) + days
    await db.commit()
    await db.refresh(lr)

    if is_final_approved:
        try:
            await recompute_leave_range(
                companyId, lr.company_employeeId, lr.startDate, lr.endDate, db
            )
        except Exception:
            pass
    return _serialize_leave(lr, emp)


# ---------------------------------------------------------------------------
# PDPA Biometric Consent & Retention Compliance
# ---------------------------------------------------------------------------
@router.get("/company/{companyId}/pdpa-summary")
async def get_pdpa_summary(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    emps = (
        await db.execute(
            select(CompanyEmployee)
            .where(
                CompanyEmployee.companyId == companyId,
                CompanyEmployee.deletedAt.is_(None),
            )
            .options(
                selectinload(CompanyEmployee.member),
                selectinload(CompanyEmployee.department),
            )
        )
    ).scalars().all()

    member_ids = [e.memberId for e in emps if e.memberId]
    face_counts: dict[UUID, int] = {}
    if member_ids:
        fc_rows = (
            await db.execute(
                select(FaceEncoding.memberId, func.count(FaceEncoding.faceEncodingId))
                .where(FaceEncoding.memberId.in_(member_ids))
                .group_by(FaceEncoding.memberId)
            )
        ).all()
        face_counts = {row[0]: int(row[1] or 0) for row in fc_rows}

    records = []
    consented_count = 0
    enrolled_count = 0
    for e in emps:
        m = e.member
        if not m or getattr(m, "deletedAt", None) is not None:
            continue
        f_count = face_counts.get(m.memberId, 0)
        consent_at = getattr(m, "biometricConsentAt", None)
        if consent_at:
            consented_count += 1
        if f_count > 0:
            enrolled_count += 1
        records.append(
            {
                "company_employeeId": str(e.company_employeeId),
                "memberId": str(m.memberId),
                "employeeId": e.employeeId or "",
                "fullName": f"{m.firstName or ''} {m.lastName or ''}".strip() or m.username,
                "department": (e.department.thName if e.department else "") or "",
                "faceCount": f_count,
                "biometricConsentAt": consent_at,
                "hasConsent": consent_at is not None,
            }
        )

    retention = await pdpa_service.get_retention_settings(db, companyId)
    consent_policy = await pdpa_service.get_consent_policy(db, companyId)
    return {
        "totalEmployees": len(records),
        "consentedEmployees": consented_count,
        "enrolledEmployees": enrolled_count,
        "consentPolicy": consent_policy,
        "retentionPolicy": {
            "imageRetentionDays": int(retention["punchPhotoDays"]),
            "tempRetentionHours": int(retention["tempHours"]),
            "biometricDays": int(retention["biometricDays"]),
            "punchPhotoDays": int(retention["punchPhotoDays"]),
            "incidentSnapshotDays": int(retention["incidentSnapshotDays"]),
            "storageBackend": settings.STORAGE_BACKEND,
        },
        "summary": {
            "totalEmployees": len(records),
            "consentedCount": consented_count,
            "enrolledCount": enrolled_count,
        },
        "employees": records,
    }


@router.get("/company/{companyId}/pdpa/consent-policy")
async def get_consent_policy(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Public-to-tenant consent version/text for kiosk + enroll screens."""
    await assert_request_company_membership(request, db, companyId)
    return await pdpa_service.get_consent_policy(db, companyId)


@router.put("/company/{companyId}/pdpa/consent-policy")
async def put_consent_policy(
    companyId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await pdpa_service.put_consent_policy(db, companyId, body or {})


@router.get("/company/{companyId}/pdpa/retention")
async def get_pdpa_retention(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await pdpa_service.get_retention_settings(db, companyId)


@router.put("/company/{companyId}/pdpa/retention")
async def put_pdpa_retention(
    companyId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await pdpa_service.put_retention_settings(db, companyId, body or {})


@router.get("/company/{companyId}/members/{memberId}/dsar-export")
async def dsar_export(
    companyId: UUID,
    memberId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """PDPA subject-access request: export personal data for one member (no raw embeddings)."""
    await assert_request_company_access(request, db, companyId)
    await assert_member_company_access(request, db, memberId)
    payload = await pdpa_service.build_dsar_export(db, companyId, memberId)
    if payload.get("error") == "member_not_found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    return payload


@router.post("/company/{companyId}/members/{memberId}/erasure")
async def erase_member_data(
    companyId: UUID,
    memberId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """PDPA right-to-erasure: punch photos, encodings, incident snapshots + clear consent."""
    await assert_request_company_access(request, db, companyId)
    await assert_member_company_access(request, db, memberId)
    return await pdpa_service.erase_member_personal_data(db, companyId, memberId)


@router.post("/company/{companyId}/members/{memberId}/biometric-consent")
async def grant_biometric_consent(
    companyId: UUID,
    memberId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    await assert_member_company_access(request, db, memberId)
    member = await db.get(Member, memberId)
    if not member or getattr(member, "deletedAt", None) is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    body = {}
    try:
        body = await request.json()
    except Exception:
        body = {}
    locale = str((body or {}).get("locale") or "th")
    return await pdpa_service.record_biometric_consent(
        db, member, companyId, locale=locale
    )


@router.delete("/company/{companyId}/members/{memberId}/biometric-consent")
async def revoke_biometric_consent(
    companyId: UUID,
    memberId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Revoke PDPA biometric consent and erase biometric + punch/incident media."""
    await assert_request_company_access(request, db, companyId)
    await assert_member_company_access(request, db, memberId)
    member = await db.get(Member, memberId)
    if not member or getattr(member, "deletedAt", None) is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    result = await pdpa_service.erase_member_personal_data(
        db, companyId, memberId, clear_consent=True
    )
    return {
        "memberId": str(memberId),
        "biometricConsentAt": None,
        "hasConsent": False,
        **result,
    }


# ---------------------------------------------------------------------------
# Kiosk Device Provisioning — thin legacy aliases → device_service (D2)
# Prefer /devices/company/{companyId}/devices going forward.
# ---------------------------------------------------------------------------
from ..services import device_service as _device_svc  # noqa: E402


@router.get("/company/{companyId}/kiosk-devices")
async def list_kiosk_devices(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, "devices.manage", companyId)
    return await _device_svc.list_devices(db, companyId)


@router.post("/company/{companyId}/kiosk-devices")
async def register_kiosk_device(
    companyId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Create a device and return its one-time pairing code (shown once, never stored in clear)."""
    await assert_request_permission(request, db, "devices.manage", companyId)
    return await _device_svc.create_device(db, companyId, body or {})


@router.post("/company/{companyId}/kiosk-devices/{deviceId}/pairing-code")
async def reissue_kiosk_pairing_code(
    companyId: UUID,
    deviceId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Re-pair an existing device: invalidates its current token family and issues a new code."""
    await assert_request_permission(request, db, "devices.manage", companyId)
    return await _device_svc.reissue_pairing_code(db, companyId, deviceId)


@router.delete("/company/{companyId}/kiosk-devices/{deviceId}")
async def revoke_kiosk_device(
    companyId: UUID,
    deviceId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Revoke the device: its token family is denied immediately and no pairing code remains."""
    await assert_request_permission(request, db, "devices.manage", companyId)
    return await _device_svc.revoke_device(db, companyId, deviceId)


# ---------------------------------------------------------------------------
# C4 Approval Inbox + Regularization + Leave Balance + OT
# ---------------------------------------------------------------------------
def _serialize_regularization(row: RegularizationRequest, emp: Optional[CompanyEmployee]) -> dict:
    member = emp.member if emp else None
    full_name = (
        f"{getattr(member, 'firstName', '') or ''} {getattr(member, 'lastName', '') or ''}".strip()
        if member
        else ""
    ) or (getattr(member, "username", "") if member else "")
    return {
        "kind": "REGULARIZATION",
        "requestId": str(row.requestId),
        "companyId": str(row.companyId),
        "company_employeeId": str(row.company_employeeId),
        "employeeName": full_name,
        "employeeId": (emp.employeeId if emp else "") or "",
        "workDate": row.workDate.isoformat() if row.workDate else None,
        "requestedTimestamp": row.requestedTimestamp,
        "requestedType": row.requestedType,
        "reason": row.reason or "",
        "status": getattr(row.status, "value", row.status),
        "approvedBy": str(row.approvedBy) if row.approvedBy else None,
        "approvedAt": row.approvedAt,
        "rejectReason": row.rejectReason or "",
        "approvalLevel": int(getattr(row, "approvalLevel", 1) or 1),
        "maxApprovalLevel": int(getattr(row, "maxApprovalLevel", 1) or 1),
        "approvalHistory": list(getattr(row, "approvalHistory", None) or []),
        "createdAt": row.createdAt,
    }


def _serialize_ot(row: OtApprovalRequest, emp: Optional[CompanyEmployee]) -> dict:
    member = emp.member if emp else None
    full_name = (
        f"{getattr(member, 'firstName', '') or ''} {getattr(member, 'lastName', '') or ''}".strip()
        if member
        else ""
    ) or (getattr(member, "username", "") if member else "")
    return {
        "kind": "OT",
        "requestId": str(row.requestId),
        "companyId": str(row.companyId),
        "company_employeeId": str(row.company_employeeId),
        "employeeName": full_name,
        "employeeId": (emp.employeeId if emp else "") or "",
        "workDate": row.workDate.isoformat() if row.workDate else None,
        "otMinutes": int(row.otMinutes or 0),
        "thresholdMinutes": row.thresholdMinutes,
        "reason": row.reason or "",
        "status": getattr(row.status, "value", row.status),
        "requiresApproval": bool(row.requiresApproval),
        "approvedBy": str(row.approvedBy) if row.approvedBy else None,
        "approvedAt": row.approvedAt,
        "rejectReason": row.rejectReason or "",
        "approvalLevel": int(getattr(row, "approvalLevel", 1) or 1),
        "maxApprovalLevel": int(getattr(row, "maxApprovalLevel", 1) or 1),
        "approvalHistory": list(getattr(row, "approvalHistory", None) or []),
        "createdAt": row.createdAt,
    }


async def _emps_map(db: AsyncSession, emp_ids: list[UUID]) -> dict[UUID, CompanyEmployee]:
    if not emp_ids:
        return {}
    rows = (
        await db.execute(
            select(CompanyEmployee)
            .where(CompanyEmployee.company_employeeId.in_(emp_ids))
            .options(
                selectinload(CompanyEmployee.member),
                selectinload(CompanyEmployee.department),
            )
        )
    ).scalars().all()
    return {e.company_employeeId: e for e in rows}


@router.get("/company/{companyId}/approvals")
async def approval_inbox(
    companyId: UUID,
    request: Request,
    status_filter: Optional[str] = "PENDING",
    db: AsyncSession = Depends(get_db),
):
    """Mobile-first approval inbox: warning punches, leave, regularization, OT."""
    caller = await assert_request_company_membership(request, db, companyId)
    st = (status_filter or "PENDING").upper()

    leaves = (
        await db.execute(
            select(LeaveRequest)
            .where(LeaveRequest.companyId == companyId, LeaveRequest.status == st)
            .order_by(LeaveRequest.createdAt.desc())
            .limit(200)
        )
    ).scalars().all()
    regs = (
        await db.execute(
            select(RegularizationRequest)
            .where(RegularizationRequest.companyId == companyId, RegularizationRequest.status == st)
            .order_by(RegularizationRequest.createdAt.desc())
            .limit(200)
        )
    ).scalars().all()
    ots = (
        await db.execute(
            select(OtApprovalRequest)
            .where(OtApprovalRequest.companyId == companyId, OtApprovalRequest.status == st)
            .order_by(OtApprovalRequest.createdAt.desc())
            .limit(200)
        )
    ).scalars().all()
    punches = (
        await db.execute(
            select(EmployeeTimestamp)
            .where(
                EmployeeTimestamp.companyId == companyId,
                EmployeeTimestamp.approvalStatus == (ApprovalStatus.PENDING.value if st == "PENDING" else st),
            )
            .order_by(EmployeeTimestamp.timestamp.desc())
            .limit(200)
        )
    ).scalars().all()

    emp_ids = (
        [lr.company_employeeId for lr in leaves]
        + [r.company_employeeId for r in regs]
        + [o.company_employeeId for o in ots]
        + [p.company_employeeId for p in punches]
    )
    emps = await _emps_map(db, emp_ids)

    levels_leave = await get_company_approval_levels(db, companyId, "LEAVE")
    levels_reg = await get_company_approval_levels(db, companyId, "REGULARIZATION")
    levels_ot = await get_company_approval_levels(db, companyId, "OT")

    items: list[dict] = []
    for lr in leaves:
        emp = emps.get(lr.company_employeeId)
        if emp and caller and not await can_approve_for_employee(db, caller, companyId, emp):
            continue
        payload = _serialize_leave(lr, emp)
        payload["kind"] = "LEAVE"
        payload["currentLevelLabel"] = level_label_for(levels_leave, payload["approvalLevel"])
        items.append(payload)
    for r in regs:
        emp = emps.get(r.company_employeeId)
        if emp and caller and not await can_approve_for_employee(db, caller, companyId, emp):
            continue
        payload = _serialize_regularization(r, emp)
        payload["currentLevelLabel"] = level_label_for(levels_reg, payload["approvalLevel"])
        items.append(payload)
    for o in ots:
        emp = emps.get(o.company_employeeId)
        if emp and caller and not await can_approve_for_employee(db, caller, companyId, emp):
            continue
        payload = _serialize_ot(o, emp)
        payload["currentLevelLabel"] = level_label_for(levels_ot, payload["approvalLevel"])
        items.append(payload)
    for p in punches:
        emp = emps.get(p.company_employeeId)
        if emp and caller and not await can_approve_for_employee(db, caller, companyId, emp):
            continue
        member = emp.member if emp else None
        full_name = (
            f"{getattr(member, 'firstName', '') or ''} {getattr(member, 'lastName', '') or ''}".strip()
            if member
            else ""
        ) or (getattr(member, "username", "") if member else "")
        items.append(
            {
                "kind": "TIMESTAMP",
                "timestampId": str(p.timestampId),
                "companyId": str(p.companyId),
                "company_employeeId": str(p.company_employeeId),
                "employeeName": full_name,
                "employeeId": (emp.employeeId if emp else "") or "",
                "timestamp": p.timestamp,
                "locationName": p.locationName or "",
                "note": p.note or "",
                "approvalStatus": p.approvalStatus,
                "status": p.approvalStatus,
            }
        )

    items.sort(key=lambda x: str(x.get("createdAt") or x.get("timestamp") or ""), reverse=True)
    return {"items": items, "total": len(items)}


@router.get("/company/{companyId}/leave-balances")
async def list_leave_balances(
    companyId: UUID,
    request: Request,
    company_employeeId: Optional[UUID] = None,
    year: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_membership(request, db, companyId)
    stmt = select(LeaveBalance).where(LeaveBalance.companyId == companyId)
    if company_employeeId:
        stmt = stmt.where(LeaveBalance.company_employeeId == company_employeeId)
    if year:
        stmt = stmt.where(LeaveBalance.year == year)
    rows = (await db.execute(stmt.order_by(LeaveBalance.year.desc()).limit(500))).scalars().all()
    return {
        "items": [
            {
                "balanceId": str(b.balanceId),
                "company_employeeId": str(b.company_employeeId),
                "leaveType": b.leaveType,
                "year": b.year,
                "entitledDays": float(b.entitledDays or 0),
                "usedDays": float(b.usedDays or 0),
                "remainingDays": b.remainingDays,
            }
            for b in rows
        ]
    }


@router.put("/company/{companyId}/leave-balances")
async def upsert_leave_balance(
    companyId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    emp_id = UUID(str(body.get("company_employeeId") or ""))
    leave_type = str(body.get("leaveType") or "ANNUAL").strip().upper()
    year = int(body.get("year") or date.today().year)
    bal = await _get_or_create_leave_balance(db, companyId, emp_id, leave_type, year)
    if "entitledDays" in body:
        bal.entitledDays = float(body["entitledDays"])
    if "usedDays" in body:
        bal.usedDays = float(body["usedDays"])
    await db.commit()
    await db.refresh(bal)
    return {
        "balanceId": str(bal.balanceId),
        "company_employeeId": str(bal.company_employeeId),
        "leaveType": bal.leaveType,
        "year": bal.year,
        "entitledDays": float(bal.entitledDays or 0),
        "usedDays": float(bal.usedDays or 0),
        "remainingDays": bal.remainingDays,
    }


@router.get("/company/{companyId}/regularizations")
async def list_regularizations(
    companyId: UUID,
    request: Request,
    company_employeeId: Optional[UUID] = None,
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_membership(request, db, companyId)
    stmt = select(RegularizationRequest).where(RegularizationRequest.companyId == companyId)
    if company_employeeId:
        stmt = stmt.where(RegularizationRequest.company_employeeId == company_employeeId)
    if status_filter:
        stmt = stmt.where(RegularizationRequest.status == status_filter.upper())
    rows = (
        await db.execute(
            stmt.order_by(RegularizationRequest.workDate.desc(), RegularizationRequest.createdAt.desc()).limit(200)
        )
    ).scalars().all()
    emps = await _emps_map(db, [r.company_employeeId for r in rows])
    items = [_serialize_regularization(r, emps.get(r.company_employeeId)) for r in rows]
    return {"items": items, "total": len(items)}


@router.post("/company/{companyId}/regularizations")
async def create_regularization(
    companyId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_membership(request, db, companyId)
    emp_id = UUID(str(body.get("company_employeeId") or ""))
    emp = (
        await db.execute(
            select(CompanyEmployee)
            .where(
                CompanyEmployee.company_employeeId == emp_id,
                CompanyEmployee.companyId == companyId,
                CompanyEmployee.deletedAt.is_(None),
            )
            .options(selectinload(CompanyEmployee.member))
        )
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    try:
        work_d = date.fromisoformat(str(body.get("workDate") or "")[:10])
        req_ts = datetime.fromisoformat(str(body.get("requestedTimestamp") or "").replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="workDate and requestedTimestamp required") from None
    await assert_date_not_locked(db, companyId, work_d)
    levels = await get_company_approval_levels(db, companyId, "REGULARIZATION")
    row = RegularizationRequest(
        companyId=companyId,
        company_employeeId=emp_id,
        workDate=work_d,
        requestedTimestamp=req_ts,
        requestedType=int(body.get("requestedType") or 1),
        reason=str(body.get("reason") or "").strip(),
        status=ApprovalRequestStatus.PENDING.value,
        approvalLevel=1,
        maxApprovalLevel=len(levels),
        originalTimestampId=UUID(str(body["originalTimestampId"])) if body.get("originalTimestampId") else None,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _serialize_regularization(row, emp)


@router.post("/company/{companyId}/regularizations/{requestId}/approval")
async def decide_regularization(
    companyId: UUID,
    requestId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    caller = await assert_request_company_membership(request, db, companyId)
    row = await db.get(RegularizationRequest, requestId)
    if not row or row.companyId != companyId:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Regularization request not found")
    emp = (
        await db.execute(
            select(CompanyEmployee)
            .where(CompanyEmployee.company_employeeId == row.company_employeeId)
            .options(selectinload(CompanyEmployee.member))
        )
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    await assert_can_approve_for_employee(db, caller, companyId, emp)
    await assert_date_not_locked(db, companyId, row.workDate)
    approve = bool(body.get("approve", True))
    await advance_approval_step(
        db,
        row,
        companyId,
        emp,
        caller,
        approve,
        body.get("rejectReason"),
        "REGULARIZATION",
    )
    await db.commit()
    await db.refresh(row)
    return _serialize_regularization(row, emp)


@router.get("/company/{companyId}/ot-approvals")
async def list_ot_approvals(
    companyId: UUID,
    request: Request,
    company_employeeId: Optional[UUID] = None,
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_membership(request, db, companyId)
    stmt = select(OtApprovalRequest).where(OtApprovalRequest.companyId == companyId)
    if company_employeeId:
        stmt = stmt.where(OtApprovalRequest.company_employeeId == company_employeeId)
    if status_filter:
        stmt = stmt.where(OtApprovalRequest.status == status_filter.upper())
    rows = (
        await db.execute(
            stmt.order_by(OtApprovalRequest.workDate.desc(), OtApprovalRequest.createdAt.desc()).limit(200)
        )
    ).scalars().all()
    emps = await _emps_map(db, [r.company_employeeId for r in rows])
    items = [_serialize_ot(r, emps.get(r.company_employeeId)) for r in rows]
    return {"items": items, "total": len(items)}


@router.post("/company/{companyId}/ot-approvals")
async def create_ot_approval(
    companyId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_membership(request, db, companyId)
    emp_id = UUID(str(body.get("company_employeeId") or ""))
    emp = (
        await db.execute(
            select(CompanyEmployee)
            .where(
                CompanyEmployee.company_employeeId == emp_id,
                CompanyEmployee.companyId == companyId,
                CompanyEmployee.deletedAt.is_(None),
            )
            .options(selectinload(CompanyEmployee.member))
        )
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    try:
        work_d = date.fromisoformat(str(body.get("workDate") or "")[:10])
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="workDate required") from None
    await assert_date_not_locked(db, companyId, work_d)
    ot_minutes = int(body.get("otMinutes") or 0)
    threshold = body.get("thresholdMinutes")
    if threshold is None and emp.shiftId:
        shift = await db.get(WorkShift, emp.shiftId)
        if shift is not None:
            threshold = getattr(shift, "otThresholdMinutes", None)
    requires = True
    if threshold is not None and ot_minutes <= int(threshold):
        requires = False
    levels = await get_company_approval_levels(db, companyId, "OT")
    row = OtApprovalRequest(
        companyId=companyId,
        company_employeeId=emp_id,
        workDate=work_d,
        otMinutes=ot_minutes,
        thresholdMinutes=int(threshold) if threshold is not None else None,
        reason=str(body.get("reason") or "").strip(),
        status=(
            ApprovalRequestStatus.APPROVED.value
            if not requires
            else ApprovalRequestStatus.PENDING.value
        ),
        requiresApproval=requires,
        approvalLevel=len(levels) if not requires else 1,
        maxApprovalLevel=len(levels),
        approvedAt=datetime.now(timezone.utc) if not requires else None,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _serialize_ot(row, emp)


@router.post("/company/{companyId}/ot-approvals/{requestId}/approval")
async def decide_ot_approval(
    companyId: UUID,
    requestId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    caller = await assert_request_company_membership(request, db, companyId)
    row = await db.get(OtApprovalRequest, requestId)
    if not row or row.companyId != companyId:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OT approval request not found")
    emp = (
        await db.execute(
            select(CompanyEmployee)
            .where(CompanyEmployee.company_employeeId == row.company_employeeId)
            .options(selectinload(CompanyEmployee.member))
        )
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    await assert_can_approve_for_employee(db, caller, companyId, emp)
    await assert_date_not_locked(db, companyId, row.workDate)
    approve = bool(body.get("approve", True))
    await advance_approval_step(
        db,
        row,
        companyId,
        emp,
        caller,
        approve,
        body.get("rejectReason"),
        "OT",
    )
    await db.commit()
    await db.refresh(row)
    return _serialize_ot(row, emp)


# ---------------------------------------------------------------------------
# C5 Payroll periods
# ---------------------------------------------------------------------------
@router.get("/company/{companyId}/payroll-periods")
async def list_payroll_periods(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    rows = (
        await db.execute(
            select(PayrollPeriod)
            .where(PayrollPeriod.companyId == companyId)
            .order_by(PayrollPeriod.startDate.desc())
            .limit(100)
        )
    ).scalars().all()
    return {"items": [serialize_period(p) for p in rows]}


@router.post("/company/{companyId}/payroll-periods")
async def create_payroll_period(
    companyId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    try:
        start_d = date.fromisoformat(str(body.get("startDate") or "")[:10])
        end_d = date.fromisoformat(str(body.get("endDate") or "")[:10])
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Valid startDate and endDate required") from None
    if end_d < start_d:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="endDate must be >= startDate")
    period = PayrollPeriod(
        companyId=companyId,
        name=str(body.get("name") or "").strip() or None,
        startDate=start_d,
        endDate=end_d,
        status=PayrollPeriodStatus.OPEN.value,
    )
    db.add(period)
    await db.commit()
    await db.refresh(period)
    return serialize_period(period)


@router.post("/company/{companyId}/payroll-periods/{periodId}/close")
async def close_payroll_period(
    companyId: UUID,
    periodId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    caller = await assert_request_company_access(request, db, companyId)
    period = await db.get(PayrollPeriod, periodId)
    if not period or period.companyId != companyId:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payroll period not found")
    if caller is None or caller.memberId is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization required")
    period = await close_and_lock_period(db, period, caller.memberId)
    try:
        import asyncio

        asyncio.create_task(
            emit_company_webhook_event(
                companyId,
                "payroll.period.closed",
                {
                    "periodId": str(period.periodId),
                    "companyId": str(companyId),
                    "startDate": period.startDate.isoformat(),
                    "endDate": period.endDate.isoformat(),
                    "status": period.status,
                    "lockedBy": str(period.lockedBy) if period.lockedBy else None,
                    "lockedAt": period.lockedAt.isoformat() if period.lockedAt else None,
                },
            )
        )
    except Exception:
        pass
    return serialize_period(period)


# ---------------------------------------------------------------------------
# BL-07 Multi-level Approval Policy & Delegate Approver
# ---------------------------------------------------------------------------
@router.get("/company/{companyId}/approval-policy")
async def get_approval_policy(
    companyId: UUID,
    request: Request,
    request_type: str = "ALL",
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_membership(request, db, companyId)
    levels = await get_company_approval_levels(db, companyId, request_type)
    return {
        "companyId": str(companyId),
        "requestType": (request_type or "ALL").upper(),
        "levels": levels,
    }


@router.put("/company/{companyId}/approval-policy")
async def upsert_approval_policy(
    companyId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    from ..services import rbac_service

    caller = await assert_request_company_membership(request, db, companyId)
    await rbac_service.assert_permission(db, caller, rbac_service.PERM_COMPANY_SETTINGS, companyId)

    req_type = str(body.get("requestType") or "ALL").strip().upper()
    raw_levels = body.get("levels")
    if not isinstance(raw_levels, list) or not raw_levels:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="levels list is required")
    if len(raw_levels) > 5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Maximum 5 approval levels supported")

    normalized_levels = []
    for idx, lvl in enumerate(raw_levels, start=1):
        if not isinstance(lvl, dict):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid level item")
        normalized_levels.append(
            {
                "level": idx,
                "role": str(lvl.get("role") or "MANAGER").strip().upper(),
                "label": str(lvl.get("label") or f"Level {idx}").strip(),
            }
        )

    existing = (
        await db.execute(
            select(ApprovalPolicy).where(
                ApprovalPolicy.companyId == companyId,
                ApprovalPolicy.requestType == req_type,
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        existing = ApprovalPolicy(
            companyId=companyId,
            requestType=req_type,
            levels=normalized_levels,
            isActive=True,
        )
        db.add(existing)
    else:
        existing.levels = normalized_levels
        existing.isActive = True
    await db.commit()
    await db.refresh(existing)
    return {
        "policyId": str(existing.policyId),
        "companyId": str(existing.companyId),
        "requestType": existing.requestType,
        "levels": existing.levels,
    }


@router.get("/company/{companyId}/approval-delegations")
async def list_approval_delegations(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    from ..models.member import Member

    await assert_request_company_membership(request, db, companyId)
    rows = (
        await db.execute(
            select(ApprovalDelegation)
            .where(ApprovalDelegation.companyId == companyId)
            .order_by(ApprovalDelegation.createdAt.desc())
            .limit(100)
        )
    ).scalars().all()

    member_ids = list({r.delegatorMemberId for r in rows} | {r.delegateMemberId for r in rows})
    members = (
        {
            m.memberId: m
            for m in (
                await db.execute(select(Member).where(Member.memberId.in_(member_ids)))
            ).scalars().all()
        }
        if member_ids
        else {}
    )

    def _name(mid: UUID) -> str:
        m = members.get(mid)
        if not m:
            return ""
        return f"{getattr(m, 'firstName', '') or ''} {getattr(m, 'lastName', '') or ''}".strip() or getattr(
            m, "username", ""
        )

    items = [
        {
            "delegationId": str(r.delegationId),
            "companyId": str(r.companyId),
            "delegatorMemberId": str(r.delegatorMemberId),
            "delegatorName": _name(r.delegatorMemberId),
            "delegateMemberId": str(r.delegateMemberId),
            "delegateName": _name(r.delegateMemberId),
            "startDate": r.startDate.isoformat() if r.startDate else None,
            "endDate": r.endDate.isoformat() if r.endDate else None,
            "reason": r.reason or "",
            "isActive": bool(r.isActive),
            "createdAt": r.createdAt,
        }
        for r in rows
    ]
    return {"items": items, "total": len(items)}


@router.post("/company/{companyId}/approval-delegations")
async def create_approval_delegation(
    companyId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    from ..models.member import Member
    from ..services import rbac_service

    caller = await assert_request_company_membership(request, db, companyId)
    if caller is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization required")

    delegator_raw = body.get("delegatorMemberId")
    delegator_id = UUID(str(delegator_raw)) if delegator_raw else caller.memberId
    if delegator_id != caller.memberId:
        await rbac_service.assert_permission(db, caller, rbac_service.PERM_COMPANY_SETTINGS, companyId)

    try:
        delegate_id = UUID(str(body.get("delegateMemberId") or ""))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="delegateMemberId required") from None

    if delegate_id == delegator_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delegate to self")

    delegate_member = await db.get(Member, delegate_id)
    if delegate_member is None or delegate_member.deletedAt is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delegate member not found")

    try:
        start_d = date.fromisoformat(str(body.get("startDate") or "")[:10])
        end_d = date.fromisoformat(str(body.get("endDate") or "")[:10])
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Valid startDate and endDate required") from None
    if end_d < start_d:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="endDate must be >= startDate")

    row = ApprovalDelegation(
        companyId=companyId,
        delegatorMemberId=delegator_id,
        delegateMemberId=delegate_id,
        startDate=start_d,
        endDate=end_d,
        reason=str(body.get("reason") or "").strip() or None,
        isActive=True,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {
        "delegationId": str(row.delegationId),
        "companyId": str(row.companyId),
        "delegatorMemberId": str(row.delegatorMemberId),
        "delegateMemberId": str(row.delegateMemberId),
        "startDate": row.startDate.isoformat(),
        "endDate": row.endDate.isoformat(),
        "reason": row.reason or "",
        "isActive": bool(row.isActive),
    }


@router.delete("/company/{companyId}/approval-delegations/{delegationId}")
async def delete_approval_delegation(
    companyId: UUID,
    delegationId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    from ..services import rbac_service

    caller = await assert_request_company_membership(request, db, companyId)
    row = await db.get(ApprovalDelegation, delegationId)
    if row is None or row.companyId != companyId:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delegation not found")
    if caller is None or (
        row.delegatorMemberId != caller.memberId
        and not await rbac_service.has_permission(db, caller, rbac_service.PERM_COMPANY_SETTINGS, companyId)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted to remove this delegation")

    await db.delete(row)
    await db.commit()
    return {"status": "deleted", "delegationId": str(delegationId)}


# ---------------------------------------------------------------------------
# BL-08 Leave Policy & OT Rate Engine (1.0x / 1.5x / 2.0x / 3.0x)
# ---------------------------------------------------------------------------
@router.get("/company/{companyId}/leave-policies")
async def list_leave_policies(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_membership(request, db, companyId)
    rows = (
        await db.execute(
            select(LeavePolicy)
            .where(LeavePolicy.companyId == companyId)
            .order_by(LeavePolicy.leaveType.asc())
        )
    ).scalars().all()
    items = [
        {
            "policyId": str(r.policyId),
            "companyId": str(r.companyId),
            "leaveType": r.leaveType,
            "displayName": r.displayName or r.leaveType,
            "annualQuotaDays": float(r.annualQuotaDays),
            "seniorityTiers": list(r.seniorityTiers or []),
            "allowCarryOver": bool(r.allowCarryOver),
            "maxCarryOverDays": float(r.maxCarryOverDays or 0),
            "allowHalfDay": bool(r.allowHalfDay),
            "allowHourly": bool(r.allowHourly),
            "requireMedicalCert": bool(r.requireMedicalCert),
            "medicalCertMinDays": float(r.medicalCertMinDays or 3.0),
            "isActive": bool(r.isActive),
        }
        for r in rows
    ]
    return {"items": items, "total": len(items)}


@router.put("/company/{companyId}/leave-policies/{leaveType}")
async def upsert_leave_policy(
    companyId: UUID,
    leaveType: str,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    from ..services import rbac_service

    caller = await assert_request_company_membership(request, db, companyId)
    await rbac_service.assert_permission(db, caller, rbac_service.PERM_HR_LEAVES, companyId)

    lt = leaveType.strip().upper()
    row = (
        await db.execute(
            select(LeavePolicy).where(
                LeavePolicy.companyId == companyId,
                LeavePolicy.leaveType == lt,
            )
        )
    ).scalar_one_or_none()
    tiers = body.get("seniorityTiers")
    norm_tiers = tiers if isinstance(tiers, list) else []

    if row is None:
        row = LeavePolicy(
            companyId=companyId,
            leaveType=lt,
            displayName=str(body.get("displayName") or lt).strip(),
            annualQuotaDays=float(body.get("annualQuotaDays", 6.0)),
            seniorityTiers=norm_tiers,
            allowCarryOver=bool(body.get("allowCarryOver", False)),
            maxCarryOverDays=float(body.get("maxCarryOverDays", 0.0)),
            allowHalfDay=bool(body.get("allowHalfDay", True)),
            allowHourly=bool(body.get("allowHourly", True)),
            requireMedicalCert=bool(body.get("requireMedicalCert", False)),
            medicalCertMinDays=float(body.get("medicalCertMinDays", 3.0)),
            isActive=bool(body.get("isActive", True)),
        )
        db.add(row)
    else:
        if "displayName" in body:
            row.displayName = str(body["displayName"] or lt).strip()
        if "annualQuotaDays" in body:
            row.annualQuotaDays = float(body["annualQuotaDays"])
        if "seniorityTiers" in body:
            row.seniorityTiers = norm_tiers
        if "allowCarryOver" in body:
            row.allowCarryOver = bool(body["allowCarryOver"])
        if "maxCarryOverDays" in body:
            row.maxCarryOverDays = float(body["maxCarryOverDays"])
        if "allowHalfDay" in body:
            row.allowHalfDay = bool(body["allowHalfDay"])
        if "allowHourly" in body:
            row.allowHourly = bool(body["allowHourly"])
        if "requireMedicalCert" in body:
            row.requireMedicalCert = bool(body["requireMedicalCert"])
        if "medicalCertMinDays" in body:
            row.medicalCertMinDays = float(body["medicalCertMinDays"])
        if "isActive" in body:
            row.isActive = bool(body["isActive"])

    await db.commit()
    await db.refresh(row)
    return {
        "policyId": str(row.policyId),
        "companyId": str(row.companyId),
        "leaveType": row.leaveType,
        "displayName": row.displayName,
        "annualQuotaDays": float(row.annualQuotaDays),
        "seniorityTiers": list(row.seniorityTiers or []),
        "allowCarryOver": bool(row.allowCarryOver),
        "maxCarryOverDays": float(row.maxCarryOverDays),
        "allowHalfDay": bool(row.allowHalfDay),
        "allowHourly": bool(row.allowHourly),
        "requireMedicalCert": bool(row.requireMedicalCert),
        "medicalCertMinDays": float(row.medicalCertMinDays),
        "isActive": bool(row.isActive),
    }


@router.get("/company/{companyId}/ot-policy")
async def get_ot_rate_policy(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    from ..services.ot_leave_engine_service import get_or_default_ot_policy

    await assert_request_company_membership(request, db, companyId)
    return await get_or_default_ot_policy(db, companyId)


@router.put("/company/{companyId}/ot-policy")
async def upsert_ot_rate_policy(
    companyId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    from ..services import rbac_service

    caller = await assert_request_company_membership(request, db, companyId)
    await rbac_service.assert_permission(db, caller, rbac_service.PERM_COMPANY_SETTINGS, companyId)

    row = (
        await db.execute(select(OtRatePolicy).where(OtRatePolicy.companyId == companyId))
    ).scalar_one_or_none()
    if row is None:
        row = OtRatePolicy(
            companyId=companyId,
            normalOtRate=float(body.get("normalOtRate", 1.0)),
            workdayOtRate=float(body.get("workdayOtRate", 1.5)),
            holidayWorkRate=float(body.get("holidayWorkRate", 2.0)),
            holidayOtRate=float(body.get("holidayOtRate", 3.0)),
            dailyWorkMinutes=int(body.get("dailyWorkMinutes", 480)),
            roundingMinutes=int(body.get("roundingMinutes", 15)),
        )
        db.add(row)
    else:
        if "normalOtRate" in body:
            row.normalOtRate = float(body["normalOtRate"])
        if "workdayOtRate" in body:
            row.workdayOtRate = float(body["workdayOtRate"])
        if "holidayWorkRate" in body:
            row.holidayWorkRate = float(body["holidayWorkRate"])
        if "holidayOtRate" in body:
            row.holidayOtRate = float(body["holidayOtRate"])
        if "dailyWorkMinutes" in body:
            row.dailyWorkMinutes = int(body["dailyWorkMinutes"])
        if "roundingMinutes" in body:
            row.roundingMinutes = int(body["roundingMinutes"])

    await db.commit()
    await db.refresh(row)
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


@router.get("/company/{companyId}/payroll-summary")
async def get_payroll_summary(
    companyId: UUID,
    request: Request,
    startDate: str,
    endDate: str,
    company_employeeId: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    from ..services.ot_leave_engine_service import build_payroll_summary

    await assert_request_company_access(request, db, companyId)
    try:
        start_d = date.fromisoformat(startDate[:10])
        end_d = date.fromisoformat(endDate[:10])
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Valid startDate and endDate required") from None
    return await build_payroll_summary(db, companyId, start_d, end_d, company_employeeId)


@router.get("/company/{companyId}/payroll-connectors/{connector}")
async def export_payroll_connector(
    companyId: UUID,
    connector: str,
    request: Request,
    startDate: str,
    endDate: str,
    company_employeeId: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    from ..services.hris_connector_service import format_payroll_for_connector
    from ..services.ot_leave_engine_service import build_payroll_summary

    await assert_request_company_access(request, db, companyId)
    try:
        start_d = date.fromisoformat(startDate[:10])
        end_d = date.fromisoformat(endDate[:10])
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Valid startDate and endDate required") from None
    summary = await build_payroll_summary(db, companyId, start_d, end_d, company_employeeId)
    return format_payroll_for_connector(summary, connector)


def _serialize_roster_entry(row: ShiftRosterEntry, shift_map: dict[UUID, WorkShift]) -> dict:
    shift = shift_map.get(row.shiftId) if row.shiftId else None
    return {
        "rosterId": str(row.rosterId),
        "companyId": str(row.companyId),
        "company_employeeId": str(row.company_employeeId),
        "workDate": row.workDate.isoformat(),
        "shiftId": str(row.shiftId) if row.shiftId else None,
        "shiftName": shift.name if shift else None,
        "startTime": shift.startTime if shift else None,
        "endTime": shift.endTime if shift else None,
        "isDayOff": bool(row.isDayOff),
        "isFlexible": bool(row.isFlexible),
        "note": row.note,
    }


def _serialize_shift_swap(row: ShiftSwapRequest) -> dict:
    return {
        "swapId": str(row.swapId),
        "companyId": str(row.companyId),
        "requesterEmployeeId": str(row.requesterEmployeeId),
        "targetEmployeeId": str(row.targetEmployeeId),
        "workDate": row.workDate.isoformat(),
        "requesterShiftId": str(row.requesterShiftId) if row.requesterShiftId else None,
        "targetShiftId": str(row.targetShiftId) if row.targetShiftId else None,
        "reason": row.reason,
        "status": row.status,
        "approvedBy": str(row.approvedBy) if row.approvedBy else None,
        "approvedAt": row.approvedAt.isoformat() if row.approvedAt else None,
        "rejectReason": row.rejectReason,
        "createdAt": row.createdAt.isoformat() if row.createdAt else None,
    }


@router.get("/company/{companyId}/roster")
async def get_company_roster(
    companyId: UUID,
    request: Request,
    startDate: str,
    endDate: str,
    company_employeeId: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    try:
        start_d = date.fromisoformat(startDate[:10])
        end_d = date.fromisoformat(endDate[:10])
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Valid startDate and endDate required") from None

    stmt = (
        select(ShiftRosterEntry)
        .where(
            ShiftRosterEntry.companyId == companyId,
            ShiftRosterEntry.workDate >= start_d,
            ShiftRosterEntry.workDate <= end_d,
        )
        .order_by(ShiftRosterEntry.workDate.asc())
    )
    if company_employeeId:
        stmt = stmt.where(ShiftRosterEntry.company_employeeId == company_employeeId)
    rows = (await db.execute(stmt)).scalars().all()
    shifts = (
        await db.execute(
            select(WorkShift).where(WorkShift.companyId == companyId, WorkShift.deletedAt.is_(None))
        )
    ).scalars().all()
    shift_map = {s.shiftId: s for s in shifts}
    return [_serialize_roster_entry(r, shift_map) for r in rows]


@router.put("/company/{companyId}/roster")
async def upsert_company_roster(
    companyId: UUID,
    request: Request,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    from datetime import timedelta

    await assert_request_company_access(request, db, companyId)
    await assert_request_permission(request, db, "hr.shifts", companyId)

    entries = list(body.get("entries") or [])
    generate = body.get("generate")
    if isinstance(generate, dict):
        try:
            g_start = date.fromisoformat(str(generate["startDate"])[:10])
            g_end = date.fromisoformat(str(generate["endDate"])[:10])
        except (KeyError, ValueError):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Valid generate startDate/endDate required") from None
        emp_ids = generate.get("employeeIds") or []
        pattern_ids = generate.get("patternShiftIds") or []
        work_days = max(1, int(generate.get("workDays") or 5))
        off_days = max(0, int(generate.get("offDays") or 2))
        is_flexible = bool(generate.get("isFlexible", False))
        cycle_len = work_days + off_days
        cur = g_start
        day_idx = 0
        while cur <= g_end:
            for e_idx, emp_id in enumerate(emp_ids):
                pos = (day_idx + e_idx) % cycle_len if cycle_len > 0 else 0
                is_off = pos >= work_days
                shift_id = None
                if not is_off and pattern_ids:
                    cycle_num = (day_idx + e_idx) // cycle_len if cycle_len > 0 else 0
                    shift_id = pattern_ids[cycle_num % len(pattern_ids)]
                entries.append(
                    {
                        "company_employeeId": emp_id,
                        "workDate": cur.isoformat(),
                        "shiftId": shift_id,
                        "isDayOff": is_off,
                        "isFlexible": is_flexible,
                    }
                )
            cur += timedelta(days=1)
            day_idx += 1

    if not entries:
        return {"updated": 0}

    updated = 0
    for item in entries:
        try:
            emp_uuid = UUID(str(item["company_employeeId"]))
            w_date = date.fromisoformat(str(item["workDate"])[:10])
        except (KeyError, ValueError):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid roster entry") from None
        emp = (
            await db.execute(
                select(CompanyEmployee).where(
                    CompanyEmployee.company_employeeId == emp_uuid,
                    CompanyEmployee.companyId == companyId,
                    CompanyEmployee.deletedAt.is_(None),
                )
            )
        ).scalar_one_or_none()
        if not emp:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Employee {emp_uuid} not found")

        shift_uuid = UUID(str(item["shiftId"])) if item.get("shiftId") else None
        is_off = bool(item.get("isDayOff", False))
        is_flex = bool(item.get("isFlexible", False))
        note = item.get("note")

        existing = (
            await db.execute(
                select(ShiftRosterEntry).where(
                    ShiftRosterEntry.companyId == companyId,
                    ShiftRosterEntry.company_employeeId == emp_uuid,
                    ShiftRosterEntry.workDate == w_date,
                )
            )
        ).scalar_one_or_none()
        if existing:
            existing.shiftId = None if is_off else shift_uuid
            existing.isDayOff = is_off
            existing.isFlexible = is_flex
            if "note" in item:
                existing.note = note
        else:
            db.add(
                ShiftRosterEntry(
                    companyId=companyId,
                    company_employeeId=emp_uuid,
                    workDate=w_date,
                    shiftId=None if is_off else shift_uuid,
                    isDayOff=is_off,
                    isFlexible=is_flex,
                    note=note,
                )
            )
        updated += 1

    await db.commit()
    return {"updated": updated}


@router.get("/company/{companyId}/shift-swaps")
async def list_shift_swaps(
    companyId: UUID,
    request: Request,
    company_employeeId: Optional[UUID] = None,
    swapStatus: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    stmt = (
        select(ShiftSwapRequest)
        .where(ShiftSwapRequest.companyId == companyId)
        .order_by(ShiftSwapRequest.createdAt.desc())
    )
    if company_employeeId:
        stmt = stmt.where(
            (ShiftSwapRequest.requesterEmployeeId == company_employeeId)
            | (ShiftSwapRequest.targetEmployeeId == company_employeeId)
        )
    if swapStatus:
        stmt = stmt.where(ShiftSwapRequest.status == swapStatus.upper())
    rows = (await db.execute(stmt)).scalars().all()
    return [_serialize_shift_swap(r) for r in rows]


@router.post("/company/{companyId}/shift-swaps", status_code=status.HTTP_201_CREATED)
async def create_shift_swap(
    companyId: UUID,
    request: Request,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_membership(request, db, companyId)
    try:
        req_emp_id = UUID(str(body["requesterEmployeeId"]))
        tgt_emp_id = UUID(str(body["targetEmployeeId"]))
        w_date = date.fromisoformat(str(body["workDate"])[:10])
    except (KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="requesterEmployeeId, targetEmployeeId, and workDate are required",
        ) from None

    if req_emp_id == tgt_emp_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot swap shift with yourself")

    emps = (
        await db.execute(
            select(CompanyEmployee).where(
                CompanyEmployee.companyId == companyId,
                CompanyEmployee.deletedAt.is_(None),
                CompanyEmployee.company_employeeId.in_([req_emp_id, tgt_emp_id]),
            )
        )
    ).scalars().all()
    emp_map = {e.company_employeeId: e for e in emps}
    if req_emp_id not in emp_map or tgt_emp_id not in emp_map:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found in company")

    roster_rows = (
        await db.execute(
            select(ShiftRosterEntry).where(
                ShiftRosterEntry.companyId == companyId,
                ShiftRosterEntry.workDate == w_date,
                ShiftRosterEntry.company_employeeId.in_([req_emp_id, tgt_emp_id]),
            )
        )
    ).scalars().all()
    roster_map = {r.company_employeeId: r for r in roster_rows}

    req_shift = (
        UUID(str(body["requesterShiftId"]))
        if body.get("requesterShiftId")
        else (roster_map[req_emp_id].shiftId if req_emp_id in roster_map else emp_map[req_emp_id].shiftId)
    )
    tgt_shift = (
        UUID(str(body["targetShiftId"]))
        if body.get("targetShiftId")
        else (roster_map[tgt_emp_id].shiftId if tgt_emp_id in roster_map else emp_map[tgt_emp_id].shiftId)
    )

    swap = ShiftSwapRequest(
        companyId=companyId,
        requesterEmployeeId=req_emp_id,
        targetEmployeeId=tgt_emp_id,
        workDate=w_date,
        requesterShiftId=req_shift,
        targetShiftId=tgt_shift,
        reason=body.get("reason"),
        status=ApprovalRequestStatus.PENDING.value,
    )
    db.add(swap)
    await db.commit()
    await db.refresh(swap)
    return _serialize_shift_swap(swap)


@router.post("/company/{companyId}/shift-swaps/{swapId}/approval")
async def decide_shift_swap(
    companyId: UUID,
    swapId: UUID,
    request: Request,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    await assert_request_permission(request, db, "hr.shifts", companyId)
    swap = (
        await db.execute(
            select(ShiftSwapRequest).where(
                ShiftSwapRequest.swapId == swapId,
                ShiftSwapRequest.companyId == companyId,
            )
        )
    ).scalar_one_or_none()
    if not swap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift swap request not found")

    decision = str(body.get("status") or "").upper()
    if decision not in {ApprovalRequestStatus.APPROVED.value, ApprovalRequestStatus.REJECTED.value}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="status must be APPROVED or REJECTED")

    actor = getattr(request.state, "user", None)
    actor_id = getattr(actor, "memberId", None)
    swap.status = decision
    swap.approvedBy = actor_id
    swap.approvedAt = datetime.now(timezone.utc)
    if decision == ApprovalRequestStatus.REJECTED.value:
        swap.rejectReason = body.get("rejectReason")
    else:
        # Swap roster entries on workDate (creating entries if missing)
        existing_rows = (
            await db.execute(
                select(ShiftRosterEntry).where(
                    ShiftRosterEntry.companyId == companyId,
                    ShiftRosterEntry.workDate == swap.workDate,
                    ShiftRosterEntry.company_employeeId.in_(
                        [swap.requesterEmployeeId, swap.targetEmployeeId]
                    ),
                )
            )
        ).scalars().all()
        by_emp = {r.company_employeeId: r for r in existing_rows}
        req_entry = by_emp.get(swap.requesterEmployeeId)
        tgt_entry = by_emp.get(swap.targetEmployeeId)

        if req_entry:
            req_entry.shiftId = swap.targetShiftId
            req_entry.isDayOff = swap.targetShiftId is None
        else:
            db.add(
                ShiftRosterEntry(
                    companyId=companyId,
                    company_employeeId=swap.requesterEmployeeId,
                    workDate=swap.workDate,
                    shiftId=swap.targetShiftId,
                    isDayOff=swap.targetShiftId is None,
                    note=f"Swapped with {swap.targetEmployeeId}",
                )
            )

        if tgt_entry:
            tgt_entry.shiftId = swap.requesterShiftId
            tgt_entry.isDayOff = swap.requesterShiftId is None
        else:
            db.add(
                ShiftRosterEntry(
                    companyId=companyId,
                    company_employeeId=swap.targetEmployeeId,
                    workDate=swap.workDate,
                    shiftId=swap.requesterShiftId,
                    isDayOff=swap.requesterShiftId is None,
                    note=f"Swapped with {swap.requesterEmployeeId}",
                )
            )

    await db.commit()
    await db.refresh(swap)
    return _serialize_shift_swap(swap)
