from datetime import date, datetime
import io
from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any
from uuid import UUID

from ..config.database import get_db
from ..controllers.employee_timestamp_controller import (
    get_all_timestamps,
    get_timestamp_by_id,
    create_timestamp,
    update_timestamp,
    delete_timestamp,
    search_timestamps,
    approve_or_reject_timestamp,
    get_company_shift_settings,
    update_company_shift_settings,
    build_timestamps_csv,
    build_timestamps_xlsx,
)
from ..schemas.employee_timestamp_schema import (
    EmployeeTimestampCreate,
    EmployeeTimestampUpdate,
    EmployeeTimestampResponse,
    EmployeeTimestampBase,
    TimestampApprovalAction,
)
from ..security.deps import (
    assert_request_company_access,
    assert_request_company_membership,
    assert_request_permission,
    require_permission,
)
from ..models.member import Member
from ..services.idempotency_service import idempotent_json
from ..services.payroll_export_service import (
    build_payroll_xlsx_bytes,
    iter_payroll_csv_chunks,
)

router = APIRouter()


def _blank(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    v = v.strip()
    return v or None


def _parse_dt(v: Optional[str]) -> Optional[datetime]:
    v = _blank(v)
    if not v:
        return None
    try:
        if len(v) == 10 and v[4] == "-" and v[7] == "-":
            return datetime.fromisoformat(v)
        return datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid datetime: {v}",
        ) from exc


def _parse_date(v: Optional[str]) -> Optional[date]:
    dt = _parse_dt(v)
    if dt is None:
        return None
    return dt.date() if hasattr(dt, "date") else dt


def _parse_int(v: Optional[str]) -> Optional[int]:
    v = _blank(v)
    if v is None:
        return None
    try:
        return int(v)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid timestampType: {v}",
        ) from exc


@router.get("/company/{companyId}/shift-settings")
async def get_shift_settings_route(
    companyId: UUID,
    db: AsyncSession = Depends(get_db),
    _: Member = Depends(require_permission("hr.shifts")),
):
    return await get_company_shift_settings(companyId, db)


@router.put("/company/{companyId}/shift-settings")
async def put_shift_settings_route(
    companyId: UUID,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    _: Member = Depends(require_permission("hr.shifts")),
):
    return await update_company_shift_settings(companyId, payload, db)


@router.get("/export/company/{companyId}")
async def export_timestamps_route(
    companyId: str,
    request: Request,
    format: str = Query("xlsx"),
    mode: str = Query("raw"),
    company_employeeId: Optional[str] = Query(None),
    startDate: Optional[str] = Query(None),
    endDate: Optional[str] = Query(None),
    timestampType: Optional[str] = Query(None),
    approvalStatus: Optional[str] = Query(None),
    limit: int = Query(5000, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    fmt = (format or "xlsx").strip().lower()
    export_mode = (mode or "raw").strip().lower()
    emp_id = _blank(company_employeeId)
    emp_uuid = UUID(emp_id) if emp_id else None
    start_d = _parse_date(startDate)
    end_d = _parse_date(endDate)

    # C5 payroll path: stream summary + detail, no 5000 in-memory cap.
    if export_mode in ("payroll", "summary", "full"):
        await assert_request_permission(request, db, "payroll.export", companyId)
        if fmt == "csv":
            return StreamingResponse(
                iter_payroll_csv_chunks(db, UUID(str(companyId)), start_d, end_d, emp_uuid),
                media_type="text/csv; charset=utf-8",
                headers={
                    "Content-Disposition": 'attachment; filename="payroll-attendance.csv"'
                },
            )
        data = await build_payroll_xlsx_bytes(db, UUID(str(companyId)), start_d, end_d, emp_uuid)
        return StreamingResponse(
            io.BytesIO(data),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": 'attachment; filename="payroll-attendance.xlsx"'
            },
        )

    await assert_request_permission(request, db, "attendance.export", companyId)
    items = await search_timestamps(
        companyId,
        emp_id,
        _parse_dt(startDate),
        _parse_dt(endDate),
        _parse_int(timestampType),
        _blank(approvalStatus),
        db,
        limit=limit,
        offset=0,
    )
    if fmt == "csv":
        data = build_timestamps_csv(items)
        return Response(
            content=data,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": 'attachment; filename="attendance-report.csv"'
            },
        )
    data = build_timestamps_xlsx(items)
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="attendance-report.xlsx"'
        },
    )


# ดึงข้อมูลการลงเวลาทั้งหมดของพนักงานในบริษัท
# When paged=1 returns {items,total,limit,offset}; otherwise a bare list (legacy callers).
@router.get("/company/{companyId}")
async def get_all_timestamps_route(
    companyId: UUID,
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    q: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_dir: str = Query("desc"),
    paged: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _: Member = Depends(require_permission("attendance.read")),
):
    return await get_all_timestamps(
        companyId,
        db,
        limit=limit,
        offset=offset,
        q=q,
        sort_by=sort_by,
        sort_dir=sort_dir,
        paged=paged,
    )


def _company_offline_hmac_key(company_id: UUID) -> str:
    import hashlib
    import hmac
    from ..config.settings import settings

    secret = (settings.SECRET_KEY or "sentinel-dev-secret").encode("utf-8")
    return hmac.new(secret, f"kiosk-offline:{company_id}".encode("utf-8"), hashlib.sha256).hexdigest()


@router.get("/company/{companyId}/offline-sync-key")
async def get_offline_sync_key_route(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """BL-12: Return company-scoped HMAC-SHA256 key for Kiosk offline IndexedDB queue signing."""
    await assert_request_company_membership(request, db, companyId)
    return {
        "hmacKey": _company_offline_hmac_key(companyId),
        "maxSkewMinutes": 5,
        "maxAgeHours": 72,
    }


# ดึงข้อมูลการลงเวลาของพนักงานจาก timestampId
@router.get("/company/{companyId}/{timestampId}", response_model=EmployeeTimestampResponse)
async def get_timestamp_by_id_route(
    companyId: UUID,
    timestampId: UUID,
    db: AsyncSession = Depends(get_db),
    _: Member = Depends(require_permission("attendance.read")),
):
    return await get_timestamp_by_id(timestampId, companyId, db)


# สร้างข้อมูลการลงเวลาของพนักงานใหม่ (Idempotency-Key supported)
@router.post("/company/{companyId}", response_model=EmployeeTimestampResponse)
async def create_timestamp_route(
    request: Request,
    companyId: UUID,
    timestamp: EmployeeTimestampCreate,
    db: AsyncSession = Depends(get_db),
    _: Member = Depends(require_permission("attendance.write")),
):
    async def _run():
        return await create_timestamp(timestamp.dict(), companyId, db)

    return await idempotent_json(
        request, scope="timestamp.punch", company_id=str(companyId), compute=_run
    )


# อัปเดตข้อมูลการลงเวลาของพนักงาน
@router.put("/company/{companyId}/{timestampId}", response_model=EmployeeTimestampBase)
async def update_timestamp_route(
    companyId: UUID,
    timestampId: UUID,
    timestamp: EmployeeTimestampUpdate,
    db: AsyncSession = Depends(get_db),
    _: Member = Depends(require_permission("attendance.write")),
):
    return await update_timestamp(timestampId, companyId, timestamp, db)


# ลบข้อมูลการลงเวลาของพนักงาน
@router.delete("/company/{companyId}/{timestampId}")
async def delete_timestamp_route(
    companyId: UUID,
    timestampId: UUID,
    db: AsyncSession = Depends(get_db),
    _: Member = Depends(require_permission("attendance.write")),
):
    await delete_timestamp(timestampId, companyId, db)
    return {"detail": "Timestamp deleted successfully"}


# ค้นหา timestamps ทั้งหมดของพนักงานจาก employeeId และเงื่อนไขอื่น ๆ
# When paged=1 returns {items,total,limit,offset}; otherwise a bare list (legacy callers).
@router.get("/search/company/{companyId}")
async def search_timestamps_route(
    request: Request,
    companyId: str,
    company_employeeId: Optional[str] = Query(None),
    startDate: Optional[str] = Query(None),
    endDate: Optional[str] = Query(None),
    timestampType: Optional[str] = Query(None),
    approvalStatus: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    q: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_dir: str = Query("desc"),
    paged: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """Empty query strings (from Angular) are treated as omitted filters."""
    from sqlalchemy import select
    from ..models.company_employee import CompanyEmployee
    from ..security.deps import assert_request_company_membership, assert_request_permission

    caller = await assert_request_company_membership(request, db, companyId)
    emp_filter = _blank(company_employeeId)
    is_self_query = False
    if emp_filter and caller is not None:
        own_emp = (
            await db.execute(
                select(CompanyEmployee).where(
                    CompanyEmployee.company_employeeId == emp_filter,
                    CompanyEmployee.companyId == companyId,
                    CompanyEmployee.memberId == caller.memberId,
                    CompanyEmployee.deletedAt.is_(None),
                )
            )
        ).scalar_one_or_none()
        is_self_query = own_emp is not None
    if not is_self_query:
        await assert_request_permission(request, db, "attendance.read", companyId)
    return await search_timestamps(
        companyId,
        _blank(company_employeeId),
        _parse_dt(startDate),
        _parse_dt(endDate),
        _parse_int(timestampType),
        _blank(approvalStatus),
        db,
        limit=limit,
        offset=offset,
        q=_blank(q),
        sort_by=_blank(sort_by),
        sort_dir=sort_dir or "desc",
        paged=paged,
    )


@router.post("/company/{companyId}/{timestampId}/approval", response_model=EmployeeTimestampResponse)
async def approve_timestamp_route(
    companyId: UUID,
    timestampId: UUID,
    action: TimestampApprovalAction,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    caller = await assert_request_company_membership(request, db, companyId)
    approved_by = caller.memberId if caller else None
    return await approve_or_reject_timestamp(
        timestampId, companyId, action, db, approved_by=approved_by
    )


@router.post("/company/{companyId}/pin-checkin")
async def pin_fallback_checkin_route(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """BL-03: PDPA non-consenting employee fallback check-in via Employee Code + Timestamp Type."""
    from fastapi import HTTPException
    from sqlalchemy import select
    from ..models.company_employee import CompanyEmployee
    from ..models.member import Member, StatusType

    await assert_request_company_membership(request, db, companyId)
    body = await request.json()
    emp_code = str(body.get("employeeCode") or "").strip()
    if not emp_code:
        raise HTTPException(status_code=400, detail="employeeCode is required")

    row = (
        await db.execute(
            select(CompanyEmployee, Member)
            .join(Member, Member.memberId == CompanyEmployee.memberId)
            .where(
                CompanyEmployee.companyId == companyId,
                CompanyEmployee.employeeId == emp_code,
                CompanyEmployee.deletedAt.is_(None),
                Member.deletedAt.is_(None),
                Member.status == StatusType.ENABLE,
            )
            .limit(1)
        )
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Active employee not found for employeeCode")

    ce, member = row
    ts_type = int(body.get("timestampType") or 1)
    note = str(body.get("note") or "PIN_FALLBACK").strip()[:200]
    payload = {
        "company_employeeId": ce.company_employeeId,
        "timestampType": ts_type,
        "latitude": float(body.get("latitude") or 0.0),
        "longitude": float(body.get("longitude") or 0.0),
        "note": note,
    }
    created = await create_timestamp(payload, companyId, db)
    return {
        "status": "OK",
        "method": "PIN_FALLBACK",
        "employeeName": f"{member.firstName} {member.lastName}".strip(),
        "employeeCode": ce.employeeId,
        "timestampId": str(getattr(created, "timestampId", "")),
    }


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    import math

    r_km = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r_km * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@router.post("/company/{companyId}/mobile-checkin")
async def mobile_field_checkin_route(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """BL-11: Mobile field check-in with photo, GPS accuracy, Anti-Mock GPS, and Wi-Fi SSID/BSSID."""
    from datetime import timedelta, timezone
    from sqlalchemy import select
    from ..models.company_employee import CompanyEmployee
    from ..models.employee_timestamp import ApprovalStatus, EmployeeTimestamp, TimestampType
    from ..models.member import Member, StatusType

    caller = await assert_request_company_membership(request, db, companyId)
    body = await request.json()

    emp_id_raw = body.get("company_employeeId")
    stmt = (
        select(CompanyEmployee, Member)
        .join(Member, Member.memberId == CompanyEmployee.memberId)
        .where(
            CompanyEmployee.companyId == companyId,
            CompanyEmployee.deletedAt.is_(None),
            Member.deletedAt.is_(None),
            Member.status == StatusType.ENABLE,
        )
    )
    if emp_id_raw:
        try:
            emp_uuid = UUID(str(emp_id_raw))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid company_employeeId") from None
        stmt = stmt.where(CompanyEmployee.company_employeeId == emp_uuid)
    elif caller:
        stmt = stmt.where(CompanyEmployee.memberId == caller.memberId)
    else:
        raise HTTPException(status_code=400, detail="company_employeeId is required")

    row = (await db.execute(stmt.limit(1))).first()
    if not row:
        raise HTTPException(status_code=404, detail="Active employee not found")

    ce, member = row
    lat = float(body.get("latitude") or 0.0)
    lon = float(body.get("longitude") or 0.0)
    gps_accuracy = float(body["gpsAccuracy"]) if body.get("gpsAccuracy") is not None else None
    is_mock_input = bool(body.get("isMockLocation") or body.get("isMockGps"))
    wifi_ssid = str(body.get("wifiSsid") or "").strip()[:120] or None
    wifi_bssid = str(body.get("wifiBssid") or "").strip()[:64] or None
    location_name = str(body.get("locationName") or "Mobile Field Check-In").strip()[:200]
    ts_type = int(body.get("timestampType") or 1)
    note = str(body.get("note") or "").strip()[:500]
    photo = body.get("photoTimestamp")

    flags: list[str] = []
    if is_mock_input:
        flags.append("MOCK_LOCATION")
    if gps_accuracy is not None and (gps_accuracy <= 0 or gps_accuracy > 500):
        flags.append("LOW_ACCURACY")

    now_utc = datetime.now(timezone.utc)
    if lat != 0.0 or lon != 0.0:
        cutoff = now_utc - timedelta(hours=2)
        prev_ts = (
            await db.execute(
                select(EmployeeTimestamp)
                .where(
                    EmployeeTimestamp.companyId == companyId,
                    EmployeeTimestamp.company_employeeId == ce.company_employeeId,
                    EmployeeTimestamp.timestamp >= cutoff,
                )
                .order_by(EmployeeTimestamp.timestamp.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if (
            prev_ts
            and prev_ts.latitude is not None
            and prev_ts.longitude is not None
            and (prev_ts.latitude != 0.0 or prev_ts.longitude != 0.0)
        ):
            dist_km = _haversine_km(float(prev_ts.latitude), float(prev_ts.longitude), lat, lon)
            prev_time = prev_ts.timestamp
            if prev_time.tzinfo is None:
                prev_time = prev_time.replace(tzinfo=timezone.utc)
            dt_hours = max((now_utc - prev_time).total_seconds() / 3600.0, 1e-4)
            speed_kmh = dist_km / dt_hours
            if speed_kmh > 250.0 and dist_km > 5.0:
                flags.append("IMPOSSIBLE_TRAVEL")

    is_anomalous = len(flags) > 0
    integrity_flag = ",".join(flags) if is_anomalous else None
    if is_anomalous:
        flag_note = f"[GPS ANOMALY: {integrity_flag}]"
        note = f"{flag_note} {note}".strip() if note else flag_note

    payload = {
        "company_employeeId": ce.company_employeeId,
        "timestampType": TimestampType.WARNING.value if is_anomalous else ts_type,
        "locationName": location_name,
        "latitude": lat,
        "longitude": lon,
        "photoTimestamp": photo,
        "note": note or None,
    }
    created = await create_timestamp(payload, companyId, db)
    ts_id = getattr(created, "timestampId", None)
    if ts_id:
        ts_row = (
            await db.execute(select(EmployeeTimestamp).where(EmployeeTimestamp.timestampId == ts_id))
        ).scalar_one_or_none()
        if ts_row:
            ts_row.gpsAccuracy = gps_accuracy
            ts_row.isMockGps = is_anomalous
            ts_row.gpsIntegrityFlag = integrity_flag
            ts_row.wifiSsid = wifi_ssid
            ts_row.wifiBssid = wifi_bssid
            if is_anomalous:
                ts_row.timestampType = TimestampType.WARNING
                ts_row.approvalStatus = ApprovalStatus.PENDING.value
            await db.commit()

    return {
        "status": "WARNING" if is_anomalous else "OK",
        "method": "MOBILE_FIELD",
        "timestampId": str(ts_id or ""),
        "employeeName": f"{member.firstName} {member.lastName}".strip(),
        "employeeCode": ce.employeeId,
        "isMockGps": is_anomalous,
        "gpsIntegrityFlag": integrity_flag,
        "gpsAccuracy": gps_accuracy,
        "wifiSsid": wifi_ssid,
        "wifiBssid": wifi_bssid,
    }


@router.post("/company/{companyId}/offline-sync")
async def offline_sync_punch_route(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """BL-12: Verify HMAC-SHA256 signed offline Kiosk punch and persist idempotently with original capturedAtMs."""
    import hashlib
    import hmac
    from datetime import timezone
    from sqlalchemy import select
    from ..models.company_employee import CompanyEmployee
    from ..models.employee_timestamp import EmployeeTimestamp, TimestampType
    from ..models.member import Member, StatusType

    caller = await assert_request_company_membership(request, db, companyId)
    body = await request.json()

    client_id = str(body.get("clientId") or "").strip()[:80]
    hmac_sig = str(body.get("hmacSignature") or "").strip().lower()
    punch_type_raw = str(body.get("punchType") or "CHECK_IN").strip().upper()
    try:
        captured_at_ms = int(body["capturedAtMs"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Valid capturedAtMs is required") from None

    if not client_id or not hmac_sig:
        raise HTTPException(status_code=400, detail="clientId and hmacSignature are required")

    key_hex = _company_offline_hmac_key(companyId)
    canonical = f"{companyId}|{client_id}|{captured_at_ms}|{punch_type_raw}".encode("utf-8")
    expected_sig = hmac.new(bytes.fromhex(key_hex), canonical, hashlib.sha256).hexdigest().lower()
    if not hmac.compare_digest(expected_sig, hmac_sig):
        raise HTTPException(status_code=403, detail="Invalid offline HMAC signature")

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    if captured_at_ms - now_ms > 5 * 60 * 1000:
        raise HTTPException(status_code=400, detail="Offline timestamp is too far in the future")
    if now_ms - captured_at_ms > 72 * 3600 * 1000:
        raise HTTPException(status_code=400, detail="Offline punch expired (>72h)")

    existing = (
        await db.execute(
            select(EmployeeTimestamp).where(
                EmployeeTimestamp.companyId == companyId,
                EmployeeTimestamp.clientEventId == client_id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        return {
            "status": "DUPLICATE",
            "timestampId": str(existing.timestampId),
            "clientId": client_id,
        }

    emp_stmt = (
        select(CompanyEmployee, Member)
        .join(Member, Member.memberId == CompanyEmployee.memberId)
        .where(
            CompanyEmployee.companyId == companyId,
            CompanyEmployee.deletedAt.is_(None),
            Member.deletedAt.is_(None),
            Member.status == StatusType.ENABLE,
        )
    )
    if body.get("company_employeeId"):
        emp_stmt = emp_stmt.where(CompanyEmployee.company_employeeId == UUID(str(body["company_employeeId"])))
    elif body.get("employeeCode"):
        emp_stmt = emp_stmt.where(CompanyEmployee.employeeId == str(body["employeeCode"]).strip())
    elif caller:
        emp_stmt = emp_stmt.where(CompanyEmployee.memberId == caller.memberId)

    row = (await db.execute(emp_stmt.limit(1))).first()
    if not row:
        raise HTTPException(status_code=404, detail="Active employee not found for offline sync")
    ce, member = row

    ts_map = {
        "CHECK_IN": TimestampType.CHECK_IN,
        "CHECK_OUT": TimestampType.CHECK_OUT,
        "BREAK_OUT": TimestampType.BREAK_OUT,
        "BREAK_IN": TimestampType.BREAK_IN,
    }
    ts_enum = ts_map.get(punch_type_raw, TimestampType.CHECK_IN)
    captured_dt = datetime.fromtimestamp(captured_at_ms / 1000.0, tz=timezone.utc).replace(tzinfo=None)

    ts_row = EmployeeTimestamp(
        company_employeeId=ce.company_employeeId,
        companyId=companyId,
        timestamp=captured_dt,
        timestampType=ts_enum,
        locationName=str(body.get("locationName") or "Offline Kiosk Sync").strip()[:200],
        latitude=float(body.get("latitude") or 0.0),
        longitude=float(body.get("longitude") or 0.0),
        note=str(body.get("note") or f"OFFLINE_SYNC:{client_id}").strip()[:500],
        clientEventId=client_id,
        isOfflineSync=True,
    )
    db.add(ts_row)
    await db.commit()
    await db.refresh(ts_row)
    return {
        "status": "SYNCED",
        "timestampId": str(ts_row.timestampId),
        "clientId": client_id,
        "employeeName": f"{member.firstName} {member.lastName}".strip(),
        "capturedAt": captured_dt.isoformat(),
        "isOfflineSync": True,
    }
