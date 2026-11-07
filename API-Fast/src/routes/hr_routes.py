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
from ..controllers.employee_timestamp_controller import (
    get_company_shift_settings,
    update_company_shift_settings,
)
from ..controllers.face_controller import clear_member_face_encodings
from ..models.company_employee import CompanyEmployee
from ..models.department import Department
from ..models.face_encoding import FaceEncoding
from ..models.hr_schedule import CompanyHoliday, KioskDevice, LeaveRequest, WorkShift
from ..models.member import Member
from ..security.deps import assert_member_company_access, assert_request_company_access
from ..security.jwt import kiosk_refresh_ttl
from ..security.kiosk_pairing import generate_pairing_code, hash_pairing_code, pairing_code_expiry
from ..services import token_revocation_service as revocation

router = APIRouter()


def _serialize_shift(ws: WorkShift) -> dict:
    return {
        "shiftId": str(ws.shiftId),
        "companyId": str(ws.companyId),
        "name": ws.name,
        "startTime": ws.startTime,
        "endTime": ws.endTime,
        "graceMinutes": int(ws.graceMinutes or 0),
        "isCrossMidnight": bool(ws.isCrossMidnight),
        "isDefault": bool(ws.isDefault),
        "createdAt": ws.createdAt,
    }


@router.get("/company/{companyId}/shifts")
async def list_company_shifts(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    rows = (
        await db.execute(
            select(WorkShift)
            .where(WorkShift.companyId == companyId, WorkShift.deletedAt.is_(None))
            .order_by(WorkShift.isDefault.desc(), WorkShift.createdAt.asc())
        )
    ).scalars().all()
    default_cfg = await get_company_shift_settings(companyId, db)
    return {
        "defaultSetting": default_cfg,
        "shifts": [_serialize_shift(r) for r in rows],
    }


@router.post("/company/{companyId}/shifts")
async def create_company_shift(
    companyId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    name = str(body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Shift name is required")
    start_time = str(body.get("startTime") or "09:00").strip()
    end_time = str(body.get("endTime") or "18:00").strip()
    grace = max(0, int(body.get("graceMinutes", 15) or 0))
    is_cross = bool(body.get("isCrossMidnight", False))
    is_default = bool(body.get("isDefault", False))

    if is_default:
        existing_defaults = (
            await db.execute(
                select(WorkShift).where(
                    WorkShift.companyId == companyId,
                    WorkShift.isDefault.is_(True),
                    WorkShift.deletedAt.is_(None),
                )
            )
        ).scalars().all()
        for ed in existing_defaults:
            ed.isDefault = False

    ws = WorkShift(
        companyId=companyId,
        name=name,
        startTime=start_time,
        endTime=end_time,
        graceMinutes=grace,
        isCrossMidnight=is_cross,
        isDefault=is_default,
    )
    db.add(ws)
    await db.commit()
    await db.refresh(ws)
    if is_default:
        await update_company_shift_settings(
            companyId,
            {
                "name": name,
                "startTime": start_time,
                "endTime": end_time,
                "graceMinutes": grace,
                "isCrossMidnight": is_cross,
            },
            db,
        )
    return _serialize_shift(ws)


@router.put("/company/{companyId}/shifts/{shiftId}")
async def update_company_shift(
    companyId: UUID,
    shiftId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    ws = await db.get(WorkShift, shiftId)
    if not ws or ws.companyId != companyId or ws.deletedAt is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found")

    if "name" in body and str(body["name"]).strip():
        ws.name = str(body["name"]).strip()
    if "startTime" in body:
        ws.startTime = str(body["startTime"]).strip()
    if "endTime" in body:
        ws.endTime = str(body["endTime"]).strip()
    if "graceMinutes" in body:
        ws.graceMinutes = max(0, int(body["graceMinutes"] or 0))
    if "isCrossMidnight" in body:
        ws.isCrossMidnight = bool(body["isCrossMidnight"])
    if "isDefault" in body:
        new_def = bool(body["isDefault"])
        if new_def:
            others = (
                await db.execute(
                    select(WorkShift).where(
                        WorkShift.companyId == companyId,
                        WorkShift.shiftId != shiftId,
                        WorkShift.deletedAt.is_(None),
                    )
                )
            ).scalars().all()
            for o in others:
                o.isDefault = False
        ws.isDefault = new_def

    await db.commit()
    await db.refresh(ws)
    return _serialize_shift(ws)


@router.delete("/company/{companyId}/shifts/{shiftId}")
async def delete_company_shift(
    companyId: UUID,
    shiftId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    ws = await db.get(WorkShift, shiftId)
    if not ws or ws.companyId != companyId or ws.deletedAt is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found")
    ws.deletedAt = datetime.now(timezone.utc)
    await db.commit()
    return {"deleted": True, "shiftId": str(shiftId)}


@router.put("/company/{companyId}/assign-shift")
async def assign_shift(
    companyId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Assign a shiftId (or None to clear) to a department or an employee."""
    await assert_request_company_access(request, db, companyId)
    raw_shift_id = body.get("shiftId")
    shift_uuid = UUID(str(raw_shift_id)) if raw_shift_id else None
    if shift_uuid:
        ws = await db.get(WorkShift, shift_uuid)
        if not ws or ws.companyId != companyId or ws.deletedAt is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found")

    if body.get("departmentId"):
        dept_id = UUID(str(body["departmentId"]))
        dept = await db.get(Department, dept_id)
        if not dept or dept.companyId != companyId or dept.deletedAt is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
        dept.shiftId = shift_uuid
        await db.commit()
        return {"assigned": "department", "departmentId": str(dept_id), "shiftId": str(shift_uuid) if shift_uuid else None}

    if body.get("company_employeeId"):
        emp_id = UUID(str(body["company_employeeId"]))
        emp = await db.get(CompanyEmployee, emp_id)
        if not emp or emp.companyId != companyId or emp.deletedAt is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
        emp.shiftId = shift_uuid
        await db.commit()
        return {"assigned": "employee", "company_employeeId": str(emp_id), "shiftId": str(shift_uuid) if shift_uuid else None}

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Provide departmentId or company_employeeId",
    )


# ---------------------------------------------------------------------------
# Company Holidays
# ---------------------------------------------------------------------------
@router.get("/company/{companyId}/holidays")
async def list_company_holidays(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    rows = (
        await db.execute(
            select(CompanyHoliday)
            .where(CompanyHoliday.companyId == companyId, CompanyHoliday.deletedAt.is_(None))
            .order_by(CompanyHoliday.holidayDate.asc())
        )
    ).scalars().all()
    return [
        {
            "holidayId": str(r.holidayId),
            "companyId": str(r.companyId),
            "holidayDate": r.holidayDate.isoformat() if r.holidayDate else None,
            "name": r.name,
            "createdAt": r.createdAt,
        }
        for r in rows
    ]


@router.post("/company/{companyId}/holidays")
async def create_company_holiday(
    companyId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    name = str(body.get("name") or "").strip()
    raw_date = str(body.get("holidayDate") or "").strip()[:10]
    if not name or not raw_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="holidayDate (YYYY-MM-DD) and name are required",
        )
    try:
        parsed_date = date.fromisoformat(raw_date)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid holidayDate format")

    row = CompanyHoliday(companyId=companyId, holidayDate=parsed_date, name=name)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {
        "holidayId": str(row.holidayId),
        "companyId": str(row.companyId),
        "holidayDate": row.holidayDate.isoformat(),
        "name": row.name,
    }


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
    row.deletedAt = datetime.now(timezone.utc)
    await db.commit()
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
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    raw_emp = body.get("company_employeeId")
    if not raw_emp:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="company_employeeId is required")
    emp_id = UUID(str(raw_emp))
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
        start_d = date.fromisoformat(str(body.get("startDate") or "")[:10])
        end_d = date.fromisoformat(str(body.get("endDate") or "")[:10])
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Valid startDate and endDate are required")
    if end_d < start_d:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="endDate must be >= startDate")

    leave_type = str(body.get("leaveType") or "ANNUAL").strip().upper()
    reason = str(body.get("reason") or "").strip()
    auto_approve = bool(body.get("autoApprove", False))

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
    await db.commit()
    await db.refresh(lr)
    return _serialize_leave(lr, emp)


@router.post("/company/{companyId}/leaves/{leaveId}/approval")
async def approve_or_reject_leave(
    companyId: UUID,
    leaveId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    caller = await assert_request_company_access(request, db, companyId)
    lr = await db.get(LeaveRequest, leaveId)
    if not lr or lr.companyId != companyId:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave request not found")

    if "status" in body:
        st = body["status"]
        approve = st in (1, "1", "APPROVED", True)
    else:
        approve = bool(body.get("approve", True))

    if approve:
        lr.status = "APPROVED"
        lr.rejectReason = None
    else:
        lr.status = "REJECTED"
        lr.rejectReason = str(body.get("rejectReason") or "ไม่อนุมัติ").strip()
    lr.approvedBy = caller.memberId if caller else None
    lr.approvedAt = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(lr)

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

    return {
        "totalEmployees": len(records),
        "consentedEmployees": consented_count,
        "enrolledEmployees": enrolled_count,
        "retentionPolicy": {
            "imageRetentionDays": int(settings.IMAGE_RETENTION_DAYS),
            "tempRetentionHours": int(settings.TEMP_RETENTION_HOURS),
            "storageBackend": settings.STORAGE_BACKEND,
        },
        "summary": {
            "totalEmployees": len(records),
            "consentedCount": consented_count,
            "enrolledCount": enrolled_count,
        },
        "employees": records,
    }


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
    member.biometricConsentAt = datetime.now(timezone.utc)
    await db.commit()
    return {
        "memberId": str(memberId),
        "biometricConsentAt": member.biometricConsentAt,
        "hasConsent": True,
    }


@router.delete("/company/{companyId}/members/{memberId}/biometric-consent")
async def revoke_biometric_consent(
    companyId: UUID,
    memberId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Revoke PDPA biometric consent and immediately purge all enrolled face encodings."""
    await assert_request_company_access(request, db, companyId)
    await assert_member_company_access(request, db, memberId)
    member = await db.get(Member, memberId)
    if not member or getattr(member, "deletedAt", None) is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    cleared = await clear_member_face_encodings(memberId, db)
    member.biometricConsentAt = None
    await db.commit()
    return {
        "memberId": str(memberId),
        "biometricConsentAt": None,
        "hasConsent": False,
        "deletedEncodings": cleared.get("deleted", 0),
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
