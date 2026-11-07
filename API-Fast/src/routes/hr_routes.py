"""Phase 3 & 4 Enterprise HR Routes: Multi-Shift, Leave, Holidays, PDPA & Kiosk Device Tokens."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config.database import get_db
from ..config.settings import settings
from ..controllers.face_controller import clear_member_face_encodings
from ..controllers import hr_controller
from ..models.company_employee import CompanyEmployee
from ..models.face_encoding import FaceEncoding
from ..models.approvals_payroll import (
    ApprovalRequestStatus,
    LeaveBalance,
    OtApprovalRequest,
    PayrollPeriod,
    PayrollPeriodStatus,
    RegularizationRequest,
)
from ..models.employee_timestamp import ApprovalStatus, EmployeeTimestamp
from ..models.hr_schedule import CompanyHoliday, KioskDevice, LeaveRequest, WorkShift
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
)
from ..security.jwt import kiosk_refresh_ttl
from ..security.kiosk_pairing import generate_pairing_code, hash_pairing_code, pairing_code_expiry
from ..services import token_revocation_service as revocation
from ..services.approval_gate import assert_can_approve_for_employee, can_approve_for_employee
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
    await assert_request_company_access(request, db, companyId)
    return await hr_controller.list_shifts(companyId, db)


@router.post("/company/{companyId}/shifts")
async def create_company_shift(
    companyId: UUID,
    body: WorkShiftCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await hr_controller.create_shift(companyId, body, db)


@router.put("/company/{companyId}/shifts/{shiftId}")
async def update_company_shift(
    companyId: UUID,
    shiftId: UUID,
    body: WorkShiftUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await hr_controller.update_shift(companyId, shiftId, body, db)


@router.delete("/company/{companyId}/shifts/{shiftId}")
async def delete_company_shift(
    companyId: UUID,
    shiftId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
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
    await assert_request_company_access(request, db, companyId)
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid holidayDate format")

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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid year")
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
        "startDate": lr.startDate.isoformat() if lr.startDate else None,
        "endDate": lr.endDate.isoformat() if lr.endDate else None,
        "reason": lr.reason or "",
        "status": _status_code_from_str(lr.status),
        "statusText": lr.status,
        "approvedBy": str(lr.approvedBy) if lr.approvedBy else None,
        "approvedAt": lr.approvedAt,
        "rejectReason": lr.rejectReason or "",
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Valid startDate and endDate are required")
    if end_d < start_d:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="endDate must be >= startDate")

    leave_type = str(body.leaveType or "ANNUAL").strip().upper()
    reason = str(body.reason or "").strip()
    auto_approve = bool(body.autoApprove)

    await assert_range_not_locked(db, companyId, start_d, end_d)
    await _assert_no_leave_overlap(db, companyId, emp_id, start_d, end_d)
    await _assert_leave_balance_available(db, companyId, emp_id, leave_type, start_d, end_d)

    lr = LeaveRequest(
        companyId=companyId,
        company_employeeId=emp_id,
        leaveType=leave_type,
        startDate=start_d,
        endDate=end_d,
        reason=reason,
        status="APPROVED" if auto_approve else "PENDING",
        approvedAt=datetime.now(timezone.utc) if auto_approve else None,
    )
    db.add(lr)
    if auto_approve:
        bal = await _get_or_create_leave_balance(db, companyId, emp_id, leave_type, start_d.year)
        bal.usedDays = float(bal.usedDays or 0) + float(_leave_days(start_d, end_d))
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
    if approve:
        lr.status = "APPROVED"
        lr.rejectReason = None
        if prev != "APPROVED":
            bal = await _get_or_create_leave_balance(
                db, companyId, lr.company_employeeId, lr.leaveType, lr.startDate.year
            )
            days = float(_leave_days(lr.startDate, lr.endDate))
            if float(bal.entitledDays or 0) > 0 and bal.remainingDays < days:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Insufficient leave balance: remaining {bal.remainingDays}, requested {days}",
                )
            bal.usedDays = float(bal.usedDays or 0) + days
    else:
        lr.status = "REJECTED"
        lr.rejectReason = str(body.rejectReason or "ไม่อนุมัติ").strip()
    # approvedBy from JWT only — ignore any client body field
    lr.approvedBy = caller.memberId if caller else None
    lr.approvedAt = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(lr)

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
# Kiosk Device Provisioning: one-time pairing code → device-scoped token (see /auth/kiosk/pair)
# ---------------------------------------------------------------------------
def _serialize_kiosk_device(r: KioskDevice) -> dict:
    now = datetime.now(timezone.utc)
    pairing_exp = r.pairingExpiresAt
    if pairing_exp is not None and pairing_exp.tzinfo is None:
        pairing_exp = pairing_exp.replace(tzinfo=timezone.utc)
    return {
        "deviceId": str(r.deviceId),
        "companyId": str(r.companyId),
        "locationId": str(r.locationId) if r.locationId else None,
        "name": r.name,
        "lastSeenAt": r.lastSeenAt,
        "pairedAt": r.pairedAt,
        "isPaired": r.tokenHash is not None and r.revokedAt is None,
        "pairingPending": bool(r.pairingCodeHash) and pairing_exp is not None and pairing_exp > now,
        "pairingExpiresAt": r.pairingExpiresAt if r.pairingCodeHash else None,
        "revokedAt": r.revokedAt,
        "isActive": r.revokedAt is None,
        "createdAt": r.createdAt,
    }


def _issue_pairing_code(device: KioskDevice) -> str:
    code = generate_pairing_code()
    device.pairingCodeHash = hash_pairing_code(code)
    device.pairingExpiresAt = pairing_code_expiry()
    return code


async def _get_company_device(db: AsyncSession, companyId: UUID, deviceId: UUID) -> KioskDevice:
    device = await db.get(KioskDevice, deviceId)
    if not device or device.companyId != companyId:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kiosk device not found")
    return device


async def _revoke_device_tokens(db: AsyncSession, device: KioskDevice, *, reason: str) -> None:
    if device.tokenFamily:
        await revocation.revoke_family(
            db, device.tokenFamily, datetime.now(timezone.utc) + kiosk_refresh_ttl(), reason=reason
        )
    device.tokenHash = None
    device.tokenFamily = None


@router.get("/company/{companyId}/kiosk-devices")
async def list_kiosk_devices(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    rows = (
        await db.execute(
            select(KioskDevice)
            .where(KioskDevice.companyId == companyId)
            .order_by(KioskDevice.createdAt.desc())
        )
    ).scalars().all()
    return [_serialize_kiosk_device(r) for r in rows]


@router.post("/company/{companyId}/kiosk-devices")
async def register_kiosk_device(
    companyId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Create a device and return its one-time pairing code (shown once, never stored in clear)."""
    await assert_request_company_access(request, db, companyId)
    name = str(body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Device name is required")
    loc_raw = body.get("locationId")
    loc_uuid = UUID(str(loc_raw)) if loc_raw else None

    device = KioskDevice(deviceId=uuid4(), companyId=companyId, locationId=loc_uuid, name=name)
    code = _issue_pairing_code(device)
    db.add(device)
    await db.commit()
    await db.refresh(device)
    return {
        **_serialize_kiosk_device(device),
        "pairingCode": code,
        "pairingCodeTtlMinutes": int(settings.KIOSK_PAIRING_CODE_TTL_MINUTES),
        "pairUrl": "/kiosk/pair",
    }


@router.post("/company/{companyId}/kiosk-devices/{deviceId}/pairing-code")
async def reissue_kiosk_pairing_code(
    companyId: UUID,
    deviceId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Re-pair an existing device: invalidates its current token family and issues a new code."""
    await assert_request_company_access(request, db, companyId)
    device = await _get_company_device(db, companyId, deviceId)
    if device.revokedAt is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Kiosk device is revoked; register a new device")
    await _revoke_device_tokens(db, device, reason=revocation.REASON_REPAIR)
    code = _issue_pairing_code(device)
    await db.commit()
    await db.refresh(device)
    return {
        **_serialize_kiosk_device(device),
        "pairingCode": code,
        "pairingCodeTtlMinutes": int(settings.KIOSK_PAIRING_CODE_TTL_MINUTES),
        "pairUrl": "/kiosk/pair",
    }


@router.delete("/company/{companyId}/kiosk-devices/{deviceId}")
async def revoke_kiosk_device(
    companyId: UUID,
    deviceId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Revoke the device: its token family is denied immediately and no pairing code remains."""
    await assert_request_company_access(request, db, companyId)
    device = await _get_company_device(db, companyId, deviceId)
    await _revoke_device_tokens(db, device, reason=revocation.REASON_DEVICE_REVOKED)
    device.pairingCodeHash = None
    device.pairingExpiresAt = None
    device.revokedAt = datetime.now(timezone.utc)
    await db.commit()
    return {
        "deviceId": str(deviceId),
        "revokedAt": device.revokedAt,
        "isActive": False,
    }


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

    items: list[dict] = []
    for lr in leaves:
        emp = emps.get(lr.company_employeeId)
        if emp and caller and not await can_approve_for_employee(db, caller, companyId, emp):
            continue
        payload = _serialize_leave(lr, emp)
        payload["kind"] = "LEAVE"
        items.append(payload)
    for r in regs:
        emp = emps.get(r.company_employeeId)
        if emp and caller and not await can_approve_for_employee(db, caller, companyId, emp):
            continue
        items.append(_serialize_regularization(r, emp))
    for o in ots:
        emp = emps.get(o.company_employeeId)
        if emp and caller and not await can_approve_for_employee(db, caller, companyId, emp):
            continue
        items.append(_serialize_ot(o, emp))
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


@router.post("/company/{companyId}/regularizations")
async def create_regularization(
    companyId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_membership(request, db, companyId)
    emp_id = UUID(str(body.get("company_employeeId") or ""))
    emp = await db.get(CompanyEmployee, emp_id)
    if not emp or emp.companyId != companyId or emp.deletedAt is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    try:
        work_d = date.fromisoformat(str(body.get("workDate") or "")[:10])
        req_ts = datetime.fromisoformat(str(body.get("requestedTimestamp") or "").replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="workDate and requestedTimestamp required")
    await assert_date_not_locked(db, companyId, work_d)
    row = RegularizationRequest(
        companyId=companyId,
        company_employeeId=emp_id,
        workDate=work_d,
        requestedTimestamp=req_ts,
        requestedType=int(body.get("requestedType") or 1),
        reason=str(body.get("reason") or "").strip(),
        status=ApprovalRequestStatus.PENDING.value,
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
    emp = await db.get(CompanyEmployee, row.company_employeeId)
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    await assert_can_approve_for_employee(db, caller, companyId, emp)
    await assert_date_not_locked(db, companyId, row.workDate)
    approve = bool(body.get("approve", True))
    if approve:
        row.status = ApprovalRequestStatus.APPROVED.value
        row.rejectReason = None
    else:
        row.status = ApprovalRequestStatus.REJECTED.value
        row.rejectReason = str(body.get("rejectReason") or "ไม่อนุมัติ").strip()
    row.approvedBy = caller.memberId if caller else None
    row.approvedAt = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(row)
    return _serialize_regularization(row, emp)


@router.post("/company/{companyId}/ot-approvals")
async def create_ot_approval(
    companyId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_membership(request, db, companyId)
    emp_id = UUID(str(body.get("company_employeeId") or ""))
    emp = await db.get(CompanyEmployee, emp_id)
    if not emp or emp.companyId != companyId or emp.deletedAt is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    try:
        work_d = date.fromisoformat(str(body.get("workDate") or "")[:10])
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="workDate required")
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
    emp = await db.get(CompanyEmployee, row.company_employeeId)
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    await assert_can_approve_for_employee(db, caller, companyId, emp)
    await assert_date_not_locked(db, companyId, row.workDate)
    approve = bool(body.get("approve", True))
    if approve:
        row.status = ApprovalRequestStatus.APPROVED.value
        row.rejectReason = None
    else:
        row.status = ApprovalRequestStatus.REJECTED.value
        row.rejectReason = str(body.get("rejectReason") or "ไม่อนุมัติ").strip()
    row.approvedBy = caller.memberId if caller else None
    row.approvedAt = datetime.now(timezone.utc)
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Valid startDate and endDate required")
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
