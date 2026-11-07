"""SentinelVision Unified Routes: Watchlist/Blacklist/VIP, Smart Access Control, Visitor Pass, Smart Events, Muster Roll & Edge Sync."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import json
import logging
from pathlib import Path
import shutil
from typing import List, Optional
import urllib.request
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config.database import get_db
from ..config.settings import settings
from ..models.company_employee import CompanyEmployee
from ..models.employee_timestamp import EmployeeTimestamp
from ..models.face_encoding import FaceEncoding
from ..models.member import Member
from ..models.sentinel import (
    SentinelAccessZone,
    SentinelEvent,
    SentinelIdentity,
    SentinelIncidentLog,
)
from ..security.deps import assert_request_company_access, current_member_var
from ..services.company_module_service import (
    VALID_STATION_MODES as MODULE_STATION_MODES,
    get_company_module_config,
    save_company_module_config,
)
from ..services.face_match_service import (
    search_face_pgvector,
    search_sentinel_identity_pgvector,
)
from ..services.notification_service import NotificationOutbox, compute_webhook_signature
from ..services.storage_service import store_image_file
from ..utils.face_gpu_queue import run_on_face_gpu

router = APIRouter()
logger = logging.getLogger("dpu.sentinel")

VALID_IDENTITY_TYPES = {"BLACKLIST", "POI", "VIP", "VISITOR", "EVENT_ATTENDEE"}
VALID_SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
VALID_STATION_MODES = set(MODULE_STATION_MODES)


def _bangkok_tz():
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo("Asia/Bangkok")
    except Exception:
        return timezone(timedelta(hours=7))


def _parse_iso_dt(raw: Optional[str]) -> Optional[datetime]:
    if not raw or not str(raw).strip():
        return None
    val = str(raw).strip()
    try:
        if val.endswith("Z"):
            val = val[:-1] + "+00:00"
        dt = datetime.fromisoformat(val)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_bangkok_tz())
        return dt
    except Exception:
        return None


def _serialize_identity(item: SentinelIdentity) -> dict:
    return {
        "identityId": str(item.identityId),
        "companyId": str(item.companyId),
        "identityType": item.identityType,
        "fullName": item.fullName,
        "documentRef": item.documentRef,
        "phoneNumber": item.phoneNumber,
        "email": item.email,
        "organization": item.organization,
        "severity": item.severity,
        "alertNote": item.alertNote,
        "visitPurpose": item.visitPurpose,
        "hostMemberId": str(item.hostMemberId) if item.hostMemberId else None,
        "seatNumber": item.seatNumber,
        "eventId": str(item.eventId) if item.eventId else None,
        "allowedZoneIds": list(item.allowedZoneIds or []),
        "pictureUrl": item.pictureUrl,
        "hasFaceEnrolled": item.embedding is not None,
        "validFrom": item.validFrom,
        "expiresAt": item.expiresAt,
        "consentAcceptedAt": item.consentAcceptedAt,
        "status": item.status,
        "createdAt": item.createdAt,
    }


def _serialize_zone(zone: SentinelAccessZone) -> dict:
    return {
        "zoneId": str(zone.zoneId),
        "companyId": str(zone.companyId),
        "name": zone.name,
        "code": zone.code,
        "locationId": str(zone.locationId) if zone.locationId else None,
        "stationMode": zone.stationMode,
        "allowedDepartments": list(zone.allowedDepartments or []),
        "allowedIdentityTypes": list(zone.allowedIdentityTypes or ["EMPLOYEE", "VIP", "VISITOR"]),
        "scheduleStart": zone.scheduleStart or "00:00",
        "scheduleEnd": zone.scheduleEnd or "23:59",
        "require2FA": bool(zone.require2FA),
        "relayWebhookUrl": zone.relayWebhookUrl,
        "hasRelaySecret": bool(zone.relaySecret),
        "isActive": bool(zone.isActive),
        "createdAt": zone.createdAt,
    }


def _serialize_event(ev: SentinelEvent, attendee_count: int = 0, checked_in_count: int = 0) -> dict:
    return {
        "eventId": str(ev.eventId),
        "companyId": str(ev.companyId),
        "name": ev.name,
        "locationName": ev.locationName,
        "startAt": ev.startAt,
        "endAt": ev.endAt,
        "welcomeMessage": ev.welcomeMessage,
        "capacity": int(ev.capacity or 0),
        "autoExpireDays": int(ev.autoExpireDays or 7),
        "status": ev.status,
        "attendeeCount": attendee_count,
        "checkedInCount": checked_in_count,
        "createdAt": ev.createdAt,
    }


def _serialize_incident(inc: SentinelIncidentLog) -> dict:
    return {
        "incidentId": str(inc.incidentId),
        "companyId": str(inc.companyId),
        "eventType": inc.eventType,
        "severity": inc.severity,
        "identityId": str(inc.identityId) if inc.identityId else None,
        "memberId": str(inc.memberId) if inc.memberId else None,
        "subjectName": inc.subjectName,
        "identityType": inc.identityType,
        "zoneId": str(inc.zoneId) if inc.zoneId else None,
        "zoneName": inc.zoneName,
        "eventId": str(inc.eventId) if inc.eventId else None,
        "confidencePercent": inc.confidencePercent,
        "distance": inc.distance,
        "snapshotUrl": inc.snapshotUrl,
        "actionTaken": inc.actionTaken,
        "acknowledgedBy": str(inc.acknowledgedBy) if inc.acknowledgedBy else None,
        "acknowledgedAt": inc.acknowledgedAt,
        "occurredAt": inc.occurredAt,
    }


async def _dispatch_relay_webhook_async(
    webhook_url: str,
    secret: Optional[str],
    payload: dict,
) -> bool:
    """Non-blocking IoT Door / Turnstile relay trigger executed in thread executor."""
    if not webhook_url or not webhook_url.startswith(("http://", "https://")):
        return False

    def _send_sync() -> bool:
        body_bytes = json.dumps(payload).encode("utf-8")
        ts_str = str(int(datetime.now(timezone.utc).timestamp()))
        headers = {
            "Content-Type": "application/json",
            "X-Sentinel-Timestamp": ts_str,
        }
        if secret:
            headers["X-DPU-Signature-256"] = compute_webhook_signature(secret, ts_str, body_bytes)
        req = urllib.request.Request(webhook_url, data=body_bytes, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=4) as resp:
            return 200 <= resp.status < 300

    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, _send_sync)
    except Exception:
        logger.warning("IoT relay webhook failed for %s", webhook_url)
        return False


def _is_within_schedule(start_hhmm: str, end_hhmm: str, now_local: datetime) -> bool:
    try:
        sh, sm = [int(x) for x in (start_hhmm or "00:00").split(":")[:2]]
        eh, em = [int(x) for x in (end_hhmm or "23:59").split(":")[:2]]
        cur_m = now_local.hour * 60 + now_local.minute
        start_m = sh * 60 + sm
        end_m = eh * 60 + em
        if start_m <= end_m:
            return start_m <= cur_m <= end_m
        return cur_m >= start_m or cur_m <= end_m
    except Exception:
        return True


@router.get("/company/{companyId}/module-config")
async def get_company_module_config_route(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Per-company enabled modules, default station mode, and scanActionRules."""
    await assert_request_company_access(request, db, companyId)
    return await get_company_module_config(db, companyId)


@router.put("/company/{companyId}/module-config")
async def put_company_module_config_route(
    companyId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await save_company_module_config(db, companyId, body or {})


@router.get("/company/{companyId}/overview")
async def get_sentinel_overview(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Unified Command Center KPIs, Watchlist/Visitor counts, Active Zones, Recent Incidents & Live Muster Roll."""
    await assert_request_company_access(request, db, companyId)

    tz = _bangkok_tz()
    now_local = datetime.now(tz)
    day_start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    day_start_naive = day_start_local.astimezone(timezone.utc).replace(tzinfo=None)

    identities = (
        await db.execute(
            select(SentinelIdentity).where(
                SentinelIdentity.companyId == companyId,
                SentinelIdentity.deletedAt.is_(None),
            )
        )
    ).scalars().all()

    blacklist_count = sum(
        1 for i in identities if i.identityType in ("BLACKLIST", "POI") and i.status == "ACTIVE"
    )
    vip_count = sum(1 for i in identities if i.identityType == "VIP" and i.status == "ACTIVE")
    visitor_count = sum(1 for i in identities if i.identityType == "VISITOR" and i.status == "ACTIVE")
    event_attendee_count = sum(
        1 for i in identities if i.identityType == "EVENT_ATTENDEE" and i.status == "ACTIVE"
    )

    zones_count = (
        await db.execute(
            select(func.count())
            .select_from(SentinelAccessZone)
            .where(
                SentinelAccessZone.companyId == companyId,
                SentinelAccessZone.deletedAt.is_(None),
                SentinelAccessZone.isActive.is_(True),
            )
        )
    ).scalar() or 0

    live_events_count = (
        await db.execute(
            select(func.count())
            .select_from(SentinelEvent)
            .where(
                SentinelEvent.companyId == companyId,
                SentinelEvent.deletedAt.is_(None),
                SentinelEvent.status.in_(["LIVE", "UPCOMING"]),
            )
        )
    ).scalar() or 0

    recent_incidents = (
        await db.execute(
            select(SentinelIncidentLog)
            .where(SentinelIncidentLog.companyId == companyId)
            .order_by(SentinelIncidentLog.occurredAt.desc())
            .limit(15)
        )
    ).scalars().all()

    unack_alerts = (
        await db.execute(
            select(func.count())
            .select_from(SentinelIncidentLog)
            .where(
                SentinelIncidentLog.companyId == companyId,
                SentinelIncidentLog.severity.in_(["WARNING", "CRITICAL"]),
                SentinelIncidentLog.acknowledgedAt.is_(None),
            )
        )
    ).scalar() or 0

    # Live Building Occupancy / Emergency Muster Roll (Employees & Visitors checked in today)
    today_punches = (
        await db.execute(
            select(EmployeeTimestamp)
            .options(
                selectinload(EmployeeTimestamp.company_employee).selectinload(
                    CompanyEmployee.member
                )
            )
            .where(
                EmployeeTimestamp.companyId == companyId,
                EmployeeTimestamp.timestamp >= day_start_naive,
            )
            .order_by(EmployeeTimestamp.timestamp.desc())
            .limit(200)
        )
    ).scalars().all()

    seen_emp: set[str] = set()
    muster_roll: List[dict] = []
    for ts in today_punches:
        emp = ts.company_employee
        if not emp:
            continue
        emp_id_str = str(emp.company_employeeId)
        if emp_id_str in seen_emp:
            continue
        seen_emp.add(emp_id_str)
        m = emp.member
        full_name = (
            f"{m.firstName or ''} {m.lastName or ''}".strip() if m else emp.employeeId or "Employee"
        )
        muster_roll.append(
            {
                "subjectId": emp_id_str,
                "fullName": full_name,
                "badgeCode": emp.employeeId or "-",
                "category": "EMPLOYEE",
                "zoneOrLocation": ts.locationName or "Main Kiosk",
                "lastSeenAt": ts.timestamp,
            }
        )

    # Also include Visitors / VIPs who had ACCESS_GRANTED or VISITOR_CHECKIN today
    visitor_logs_today = (
        await db.execute(
            select(SentinelIncidentLog)
            .where(
                SentinelIncidentLog.companyId == companyId,
                SentinelIncidentLog.occurredAt >= day_start_local,
                SentinelIncidentLog.eventType.in_(
                    ["ACCESS_GRANTED", "VISITOR_CHECKIN", "VIP_ARRIVAL", "EVENT_CHECKIN"]
                ),
            )
            .order_by(SentinelIncidentLog.occurredAt.desc())
            .limit(100)
        )
    ).scalars().all()

    seen_ident: set[str] = set()
    for vlog in visitor_logs_today:
        key = str(vlog.identityId or vlog.memberId or vlog.incidentId)
        if key in seen_ident:
            continue
        seen_ident.add(key)
        muster_roll.append(
            {
                "subjectId": key,
                "fullName": vlog.subjectName or "Guest",
                "badgeCode": vlog.identityType or "VISITOR",
                "category": vlog.identityType or "VISITOR",
                "zoneOrLocation": vlog.zoneName or "Access Gate",
                "lastSeenAt": vlog.occurredAt,
            }
        )

    return {
        "summary": {
            "blacklistAndPoiCount": blacklist_count,
            "vipCount": vip_count,
            "activeVisitorCount": visitor_count,
            "eventAttendeeCount": event_attendee_count,
            "activeZonesCount": int(zones_count),
            "liveEventsCount": int(live_events_count),
            "unacknowledgedAlerts": int(unack_alerts),
            "buildingOccupancyCount": len(muster_roll),
        },
        "musterRoll": muster_roll[:100],
        "recentIncidents": [_serialize_incident(inc) for inc in recent_incidents],
    }


@router.get("/company/{companyId}/identities")
async def list_sentinel_identities(
    companyId: UUID,
    request: Request,
    identityType: Optional[str] = Query(None),
    eventId: Optional[UUID] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    stmt = select(SentinelIdentity).where(
        SentinelIdentity.companyId == companyId,
        SentinelIdentity.deletedAt.is_(None),
    )
    if identityType:
        types = [t.strip().upper() for t in identityType.split(",") if t.strip()]
        if types:
            stmt = stmt.where(SentinelIdentity.identityType.in_(types))
    if eventId:
        stmt = stmt.where(SentinelIdentity.eventId == eventId)

    stmt = stmt.order_by(SentinelIdentity.createdAt.desc()).limit(limit).offset(offset)
    rows = (await db.execute(stmt)).scalars().all()
    return [_serialize_identity(r) for r in rows]


@router.post("/company/{companyId}/identities")
async def create_sentinel_identity(
    companyId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    full_name = str(body.get("fullName") or "").strip()
    if not full_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="fullName is required",
        )
    identity_type = str(body.get("identityType") or "VISITOR").strip().upper()
    if identity_type not in VALID_IDENTITY_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"identityType must be one of {sorted(VALID_IDENTITY_TYPES)}",
        )
    severity = str(body.get("severity") or "LOW").strip().upper()
    if severity not in VALID_SEVERITIES:
        severity = "LOW"

    event_id_raw = body.get("eventId")
    event_id = UUID(str(event_id_raw)) if event_id_raw else None
    host_raw = body.get("hostMemberId")
    host_id = UUID(str(host_raw)) if host_raw else None

    expires_at = _parse_iso_dt(body.get("expiresAt"))
    if expires_at is None and identity_type == "VISITOR":
        expires_at = datetime.now(timezone.utc) + timedelta(hours=12)

    allowed_zones = body.get("allowedZoneIds")
    if not isinstance(allowed_zones, list):
        allowed_zones = []

    identity = SentinelIdentity(
        companyId=companyId,
        identityType=identity_type,
        fullName=full_name,
        documentRef=str(body.get("documentRef") or "").strip() or None,
        phoneNumber=str(body.get("phoneNumber") or "").strip() or None,
        email=str(body.get("email") or "").strip() or None,
        organization=str(body.get("organization") or "").strip() or None,
        severity=severity,
        alertNote=str(body.get("alertNote") or "").strip() or None,
        visitPurpose=str(body.get("visitPurpose") or "").strip() or None,
        hostMemberId=host_id,
        seatNumber=str(body.get("seatNumber") or "").strip() or None,
        eventId=event_id,
        allowedZoneIds=[str(z) for z in allowed_zones if z],
        expiresAt=expires_at,
        consentAcceptedAt=datetime.now(timezone.utc),
        status="ACTIVE",
    )
    db.add(identity)
    await db.commit()
    await db.refresh(identity)
    return _serialize_identity(identity)


@router.put("/company/{companyId}/identities/{identityId}")
async def update_sentinel_identity(
    companyId: UUID,
    identityId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    ident = await db.get(SentinelIdentity, identityId)
    if not ident or ident.companyId != companyId or ident.deletedAt is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Identity not found")

    if "fullName" in body and str(body["fullName"]).strip():
        ident.fullName = str(body["fullName"]).strip()
    if "identityType" in body:
        it = str(body["identityType"]).strip().upper()
        if it in VALID_IDENTITY_TYPES:
            ident.identityType = it
    if "severity" in body:
        sev = str(body["severity"]).strip().upper()
        if sev in VALID_SEVERITIES:
            ident.severity = sev
    if "documentRef" in body:
        ident.documentRef = str(body.get("documentRef") or "").strip() or None
    if "phoneNumber" in body:
        ident.phoneNumber = str(body.get("phoneNumber") or "").strip() or None
    if "email" in body:
        ident.email = str(body.get("email") or "").strip() or None
    if "organization" in body:
        ident.organization = str(body.get("organization") or "").strip() or None
    if "alertNote" in body:
        ident.alertNote = str(body.get("alertNote") or "").strip() or None
    if "visitPurpose" in body:
        ident.visitPurpose = str(body.get("visitPurpose") or "").strip() or None
    if "seatNumber" in body:
        ident.seatNumber = str(body.get("seatNumber") or "").strip() or None
    if "status" in body and str(body["status"]).strip():
        ident.status = str(body["status"]).strip().upper()
    if "expiresAt" in body:
        ident.expiresAt = _parse_iso_dt(body.get("expiresAt"))
    if "allowedZoneIds" in body and isinstance(body["allowedZoneIds"], list):
        ident.allowedZoneIds = [str(z) for z in body["allowedZoneIds"] if z]

    await db.commit()
    await db.refresh(ident)
    return _serialize_identity(ident)


@router.delete("/company/{companyId}/identities/{identityId}")
async def delete_sentinel_identity(
    companyId: UUID,
    identityId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    ident = await db.get(SentinelIdentity, identityId)
    if not ident or ident.companyId != companyId or ident.deletedAt is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Identity not found")
    ident.deletedAt = datetime.now(timezone.utc)
    ident.status = "REVOKED"
    ident.embedding = None
    await db.commit()
    return {"deleted": True, "identityId": str(identityId)}


@router.post("/company/{companyId}/identities/{identityId}/enroll-face")
async def enroll_sentinel_identity_face(
    companyId: UUID,
    identityId: UUID,
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Extract 512-d InsightFace buffalo_l embedding via GPU worker and attach to SentinelIdentity."""
    await assert_request_company_access(request, db, companyId)
    ident = await db.get(SentinelIdentity, identityId)
    if not ident or ident.companyId != companyId or ident.deletedAt is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Identity not found")

    temp_dir = Path("temp_images")
    temp_dir.mkdir(exist_ok=True)
    temp_path = temp_dir / f"sentinel_{uuid4()}.jpg"
    moved = False

    try:
        from ..utils.face_engine import generate_face_encoding

        with temp_path.open("wb") as buf:
            shutil.copyfileobj(file.file, buf)

        encoding = await run_on_face_gpu(
            lambda p=str(temp_path): generate_face_encoding(p),
            kind="other",
            company_id=companyId,
        )
        if encoding is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No clear face detected in the uploaded image.",
            )

        filename = f"sentinel_{ident.identityId}.jpg"
        store_image_file("enrolled_images", filename, temp_path, move=True)
        moved = True

        ident.embedding = encoding
        ident.pictureUrl = f"/enrolled_images/{filename}"
        ident.consentAcceptedAt = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(ident)
        return {
            "message": "Biometric face vector enrolled successfully",
            "identity": _serialize_identity(ident),
        }
    finally:
        if not moved and temp_path.exists():
            temp_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Smart Access Control Zones & Door Relay Endpoints
# ---------------------------------------------------------------------------


@router.get("/company/{companyId}/zones")
async def list_access_zones(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    rows = (
        await db.execute(
            select(SentinelAccessZone)
            .where(
                SentinelAccessZone.companyId == companyId,
                SentinelAccessZone.deletedAt.is_(None),
            )
            .order_by(SentinelAccessZone.createdAt.asc())
        )
    ).scalars().all()
    return [_serialize_zone(z) for z in rows]


@router.post("/company/{companyId}/zones")
async def create_access_zone(
    companyId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    name = str(body.get("name") or "").strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Zone name is required"
        )
    station_mode = str(body.get("stationMode") or "ACCESS_CONTROL").strip().upper()
    if station_mode not in VALID_STATION_MODES:
        station_mode = "ACCESS_CONTROL"

    allowed_types = body.get("allowedIdentityTypes")
    if not isinstance(allowed_types, list) or not allowed_types:
        allowed_types = ["EMPLOYEE", "VIP", "VISITOR"]

    allowed_depts = body.get("allowedDepartments")
    if not isinstance(allowed_depts, list):
        allowed_depts = []

    loc_raw = body.get("locationId")
    loc_id = UUID(str(loc_raw)) if loc_raw else None

    zone = SentinelAccessZone(
        companyId=companyId,
        name=name,
        code=str(body.get("code") or "GATE-01").strip().upper(),
        locationId=loc_id,
        stationMode=station_mode,
        allowedDepartments=[str(d) for d in allowed_depts if d],
        allowedIdentityTypes=[str(t).upper() for t in allowed_types if t],
        scheduleStart=str(body.get("scheduleStart") or "00:00").strip(),
        scheduleEnd=str(body.get("scheduleEnd") or "23:59").strip(),
        require2FA=bool(body.get("require2FA", False)),
        relayWebhookUrl=str(body.get("relayWebhookUrl") or "").strip() or None,
        relaySecret=str(body.get("relaySecret") or "").strip() or None,
        isActive=bool(body.get("isActive", True)),
    )
    db.add(zone)
    await db.commit()
    await db.refresh(zone)
    return _serialize_zone(zone)


@router.put("/company/{companyId}/zones/{zoneId}")
async def update_access_zone(
    companyId: UUID,
    zoneId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    zone = await db.get(SentinelAccessZone, zoneId)
    if not zone or zone.companyId != companyId or zone.deletedAt is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access zone not found")

    if "name" in body and str(body["name"]).strip():
        zone.name = str(body["name"]).strip()
    if "code" in body and str(body["code"]).strip():
        zone.code = str(body["code"]).strip().upper()
    if "stationMode" in body:
        sm = str(body["stationMode"]).strip().upper()
        if sm in VALID_STATION_MODES:
            zone.stationMode = sm
    if "allowedIdentityTypes" in body and isinstance(body["allowedIdentityTypes"], list):
        zone.allowedIdentityTypes = [str(t).upper() for t in body["allowedIdentityTypes"] if t]
    if "allowedDepartments" in body and isinstance(body["allowedDepartments"], list):
        zone.allowedDepartments = [str(d) for d in body["allowedDepartments"] if d]
    if "scheduleStart" in body:
        zone.scheduleStart = str(body["scheduleStart"] or "00:00").strip()
    if "scheduleEnd" in body:
        zone.scheduleEnd = str(body["scheduleEnd"] or "23:59").strip()
    if "require2FA" in body:
        zone.require2FA = bool(body["require2FA"])
    if "relayWebhookUrl" in body:
        zone.relayWebhookUrl = str(body.get("relayWebhookUrl") or "").strip() or None
    if "relaySecret" in body and body.get("relaySecret") is not None:
        zone.relaySecret = str(body.get("relaySecret") or "").strip() or None
    if "isActive" in body:
        zone.isActive = bool(body["isActive"])

    await db.commit()
    await db.refresh(zone)
    return _serialize_zone(zone)


@router.delete("/company/{companyId}/zones/{zoneId}")
async def delete_access_zone(
    companyId: UUID,
    zoneId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    zone = await db.get(SentinelAccessZone, zoneId)
    if not zone or zone.companyId != companyId or zone.deletedAt is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access zone not found")
    zone.deletedAt = datetime.now(timezone.utc)
    zone.isActive = False
    await db.commit()
    return {"deleted": True, "zoneId": str(zoneId)}


@router.post("/company/{companyId}/zones/{zoneId}/trigger")
async def trigger_zone_door_relay(
    companyId: UUID,
    zoneId: UUID,
    request: Request,
    body: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
):
    """Remote manual unlock / test pulse for an Access Control Door / Turnstile."""
    await assert_request_company_access(request, db, companyId)
    zone = await db.get(SentinelAccessZone, zoneId)
    if not zone or zone.companyId != companyId or zone.deletedAt is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access zone not found")

    actor = current_member_var.get()
    actor_name = (
        f"{actor.firstName or ''} {actor.lastName or ''}".strip() or actor.username
        if actor
        else "Admin Console"
    )
    reason = str((body or {}).get("reason") or "Remote console unlock")

    relay_ok = False
    if zone.relayWebhookUrl:
        relay_ok = await _dispatch_relay_webhook_async(
            zone.relayWebhookUrl,
            zone.relaySecret,
            {
                "event": "door.remote_unlock",
                "companyId": str(companyId),
                "zoneId": str(zone.zoneId),
                "zoneCode": zone.code,
                "zoneName": zone.name,
                "triggeredBy": actor_name,
                "reason": reason,
            },
        )

    inc = SentinelIncidentLog(
        companyId=companyId,
        eventType="ACCESS_GRANTED",
        severity="INFO",
        memberId=actor.memberId if actor else None,
        subjectName=actor_name,
        identityType="ADMIN_REMOTE",
        zoneId=zone.zoneId,
        zoneName=zone.name,
        actionTaken=(
            f"Remote unlock pulse sent ({reason})"
            + (" [Relay OK]" if relay_ok else " [Simulated Relay]")
        ),
    )
    db.add(inc)
    await db.commit()
    await db.refresh(inc)
    return {
        "unlocked": True,
        "relayDispatched": relay_ok,
        "zone": _serialize_zone(zone),
        "incident": _serialize_incident(inc),
    }


# ---------------------------------------------------------------------------
# Smart Events & Seminar Check-in Endpoints
# ---------------------------------------------------------------------------


@router.get("/company/{companyId}/events")
async def list_sentinel_events(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    events = (
        await db.execute(
            select(SentinelEvent)
            .where(
                SentinelEvent.companyId == companyId,
                SentinelEvent.deletedAt.is_(None),
            )
            .order_by(SentinelEvent.startAt.desc())
        )
    ).scalars().all()

    result = []
    for ev in events:
        attendee_cnt = (
            await db.execute(
                select(func.count())
                .select_from(SentinelIdentity)
                .where(
                    SentinelIdentity.companyId == companyId,
                    SentinelIdentity.eventId == ev.eventId,
                    SentinelIdentity.deletedAt.is_(None),
                )
            )
        ).scalar() or 0
        checkin_cnt = (
            await db.execute(
                select(func.count())
                .select_from(SentinelIncidentLog)
                .where(
                    SentinelIncidentLog.companyId == companyId,
                    SentinelIncidentLog.eventId == ev.eventId,
                    SentinelIncidentLog.eventType == "EVENT_CHECKIN",
                )
            )
        ).scalar() or 0
        result.append(_serialize_event(ev, int(attendee_cnt), int(checkin_cnt)))
    return result


@router.post("/company/{companyId}/events")
async def create_sentinel_event(
    companyId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    name = str(body.get("name") or "").strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Event name is required"
        )
    now = datetime.now(_bangkok_tz())
    start_at = _parse_iso_dt(body.get("startAt")) or now
    end_at = _parse_iso_dt(body.get("endAt")) or (start_at + timedelta(hours=8))

    ev = SentinelEvent(
        companyId=companyId,
        name=name,
        locationName=str(body.get("locationName") or "Main Auditorium").strip(),
        startAt=start_at,
        endAt=end_at,
        welcomeMessage=str(
            body.get("welcomeMessage") or f"ยินดีต้อนรับสู่งาน {name}"
        ).strip(),
        capacity=max(1, int(body.get("capacity") or 200)),
        autoExpireDays=max(1, int(body.get("autoExpireDays") or 7)),
        status=str(body.get("status") or "LIVE").strip().upper(),
    )
    db.add(ev)
    await db.commit()
    await db.refresh(ev)
    return _serialize_event(ev, 0, 0)


@router.delete("/company/{companyId}/events/{eventId}")
async def delete_sentinel_event(
    companyId: UUID,
    eventId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    ev = await db.get(SentinelEvent, eventId)
    if not ev or ev.companyId != companyId or ev.deletedAt is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    ev.deletedAt = datetime.now(timezone.utc)
    ev.status = "CLOSED"
    await db.commit()
    return {"deleted": True, "eventId": str(eventId)}


# ---------------------------------------------------------------------------
# Unified 1:N Face Scan & Decision Engine (Watchlist + Access + Event + Employee)
# ---------------------------------------------------------------------------


async def resolve_scan_zone(
    db: AsyncSession,
    company_id: UUID,
    zone_id: Optional[str],
    station_mode: str,
) -> tuple[Optional[SentinelAccessZone], str]:
    """Load an access zone owned by the company; may override stationMode from the zone."""
    mode = str(station_mode or "ACCESS_CONTROL").strip().upper() or "ACCESS_CONTROL"
    zone: Optional[SentinelAccessZone] = None
    if zone_id and str(zone_id).strip():
        try:
            z = await db.get(SentinelAccessZone, UUID(str(zone_id).strip()))
            if z and z.companyId == company_id and z.deletedAt is None:
                zone = z
                mode = z.stationMode or mode
        except Exception:
            pass
    return zone, mode


async def maybe_dispatch_zone_relay(
    zone: Optional[SentinelAccessZone],
    *,
    subject_name: str,
    identity_type: str = "EMPLOYEE",
) -> bool:
    if not zone or not zone.relayWebhookUrl:
        return False
    return await _dispatch_relay_webhook_async(
        zone.relayWebhookUrl,
        zone.relaySecret,
        {
            "event": "door.access_granted",
            "subjectName": subject_name,
            "identityType": identity_type,
            "zoneCode": zone.code,
        },
    )


async def evaluate_unified_scan_decision(
    db: AsyncSession,
    company_id: UUID,
    encoding: List[float],
    *,
    station_mode: str = "ACCESS_CONTROL",
    zone_id: Optional[str] = None,
    event_id: Optional[str] = None,
    totp_or_pin: Optional[str] = None,
    snapshot_url: Optional[str] = None,
    scan_action_rules: Optional[dict] = None,
) -> dict:
    """
    Shared Decision Engine for HTTP /scan and WS station modes other than plain ATTENDANCE.
    Returns a dict with matched/accessGranted/decision/… suitable for API or WS frames.
    """
    zone, station_mode = await resolve_scan_zone(db, company_id, zone_id, station_mode)
    rules = scan_action_rules or {}
    silent_alarm = bool(rules.get("enableBlacklistSilentAlarm", True))
    unknown_action = str(rules.get("unknownFaceAction") or "IGNORE").strip().upper()

    event_uuid: Optional[UUID] = None
    if event_id and str(event_id).strip():
        try:
            event_uuid = UUID(str(event_id).strip())
        except Exception:
            event_uuid = None

    threshold = float(settings.FACE_RECOGNITION_THRESHOLD)
    sentinel_match = await search_sentinel_identity_pgvector(
        db, encoding, threshold, companyId=company_id
    )
    emp_match = await search_face_pgvector(
        db, encoding, threshold, companyId=company_id
    )

    chosen_kind: Optional[str] = None
    matched_ident: Optional[SentinelIdentity] = None
    best_distance: float = 1.0

    if sentinel_match is not None:
        ident_obj, s_dist = sentinel_match
        if ident_obj.identityType in ("BLACKLIST", "POI"):
            chosen_kind = "SENTINEL"
            matched_ident = ident_obj
            best_distance = s_dist
        elif emp_match is not None:
            _, _, e_dist = emp_match
            if s_dist <= e_dist:
                chosen_kind = "SENTINEL"
                matched_ident = ident_obj
                best_distance = s_dist
            else:
                chosen_kind = "EMPLOYEE"
                best_distance = e_dist
        else:
            chosen_kind = "SENTINEL"
            matched_ident = ident_obj
            best_distance = s_dist
    elif emp_match is not None:
        chosen_kind = "EMPLOYEE"
        best_distance = emp_match[2]

    if chosen_kind is None:
        if unknown_action != "LOG_INCIDENT":
            return {
                "matched": False,
                "accessGranted": False,
                "decision": "UNKNOWN_FACE",
                "stationMode": station_mode,
                "message": "ไม่พบข้อมูลใบหน้าในระบบ (ไม่อนุญาตให้ผ่าน)",
                "incident": None,
            }
        inc = SentinelIncidentLog(
            companyId=company_id,
            eventType="ACCESS_DENIED",
            severity="WARNING",
            subjectName="Unknown Person",
            identityType="UNKNOWN",
            zoneId=zone.zoneId if zone else None,
            zoneName=zone.name if zone else station_mode,
            snapshotUrl=snapshot_url,
            actionTaken="Face not registered in company database",
        )
        db.add(inc)
        await db.commit()
        await db.refresh(inc)
        return {
            "matched": False,
            "accessGranted": False,
            "decision": "UNKNOWN_FACE",
            "stationMode": station_mode,
            "message": "ไม่พบข้อมูลใบหน้าในระบบ (ไม่อนุญาตให้ผ่าน)",
            "incident": _serialize_incident(inc),
        }

    confidence_pct = round(max(0.0, min(1.0, 1.0 - float(best_distance))) * 100.0, 2)

    if chosen_kind == "SENTINEL" and matched_ident is not None:
        itype = matched_ident.identityType

        if itype in ("BLACKLIST", "POI"):
            inc = SentinelIncidentLog(
                companyId=company_id,
                eventType="BLACKLIST_ALERT",
                severity="CRITICAL" if itype == "BLACKLIST" else "WARNING",
                identityId=matched_ident.identityId,
                subjectName=matched_ident.fullName,
                identityType=itype,
                zoneId=zone.zoneId if zone else None,
                zoneName=zone.name if zone else station_mode,
                confidencePercent=confidence_pct,
                distance=round(float(best_distance), 6),
                snapshotUrl=snapshot_url,
                actionTaken=f"Silent Security Alert Dispatched ({matched_ident.alertNote or 'Watchlist match'})",
            )
            db.add(inc)
            if silent_alarm:
                db.add(
                    NotificationOutbox(
                        companyId=company_id,
                        event="sentinel.blacklist_detected",
                        channel="webhook",
                        payload={
                            "subjectName": matched_ident.fullName,
                            "identityType": itype,
                            "severity": matched_ident.severity,
                            "alertNote": matched_ident.alertNote,
                            "zoneName": zone.name if zone else station_mode,
                            "confidencePercent": confidence_pct,
                            "snapshotUrl": snapshot_url,
                        },
                    )
                )
            await db.commit()
            await db.refresh(inc)
            return {
                "matched": True,
                "accessGranted": False,
                "decision": "BLACKLIST_BLOCKED",
                "stationMode": station_mode,
                "identityType": itype,
                "subjectName": matched_ident.fullName,
                "confidencePercent": confidence_pct,
                "alertNote": matched_ident.alertNote,
                "message": f"แจ้งเตือนความปลอดภัย: ตรวจพบบุคคลเฝ้าระวัง ({matched_ident.fullName})",
                "incident": _serialize_incident(inc),
            }

        if station_mode == "EVENT_CHECKIN" or itype == "EVENT_ATTENDEE":
            ev_obj = (
                await db.get(SentinelEvent, event_uuid or matched_ident.eventId)
                if (event_uuid or matched_ident.eventId)
                else None
            )
            welcome_msg = (
                ev_obj.welcomeMessage
                if ev_obj and ev_obj.welcomeMessage
                else f"ยินดีต้อนรับคุณ {matched_ident.fullName}"
            )
            inc = SentinelIncidentLog(
                companyId=company_id,
                eventType="EVENT_CHECKIN",
                severity="INFO",
                identityId=matched_ident.identityId,
                subjectName=matched_ident.fullName,
                identityType=itype,
                zoneId=zone.zoneId if zone else None,
                zoneName=zone.name if zone else (ev_obj.name if ev_obj else "Event Gate"),
                eventId=ev_obj.eventId if ev_obj else matched_ident.eventId,
                confidencePercent=confidence_pct,
                distance=round(float(best_distance), 6),
                snapshotUrl=snapshot_url,
                actionTaken=f"Checked in • Seat: {matched_ident.seatNumber or 'General'}",
            )
            db.add(inc)
            await db.commit()
            await db.refresh(inc)
            return {
                "matched": True,
                "accessGranted": True,
                "decision": "EVENT_WELCOME",
                "stationMode": station_mode,
                "identityType": itype,
                "subjectName": matched_ident.fullName,
                "seatNumber": matched_ident.seatNumber or "General Admission",
                "welcomeMessage": welcome_msg,
                "confidencePercent": confidence_pct,
                "message": f"{welcome_msg} (ที่นั่ง: {matched_ident.seatNumber or 'General'})",
                "incident": _serialize_incident(inc),
            }

        now_local = datetime.now(_bangkok_tz())
        allowed = True
        deny_reason = ""
        if zone is not None:
            if itype not in (zone.allowedIdentityTypes or ["EMPLOYEE", "VIP", "VISITOR"]):
                allowed = False
                deny_reason = f"ประเภทตัวตน {itype} ไม่ได้รับสิทธิ์เข้าโซน {zone.name}"
            elif not _is_within_schedule(zone.scheduleStart, zone.scheduleEnd, now_local):
                allowed = False
                deny_reason = f"อยู่นอกช่วงเวลาที่อนุญาตของโซน ({zone.scheduleStart}-{zone.scheduleEnd})"
            elif matched_ident.allowedZoneIds and str(zone.zoneId) not in [
                str(z) for z in matched_ident.allowedZoneIds
            ]:
                allowed = False
                deny_reason = f"บัตร Visitor นี้ไม่ได้รับอนุญาตสำหรับโซน {zone.name}"

        relay_ok = False
        if allowed:
            relay_ok = await maybe_dispatch_zone_relay(
                zone, subject_name=matched_ident.fullName, identity_type=itype
            )

        event_type = (
            "VIP_ARRIVAL"
            if (allowed and itype == "VIP")
            else ("VISITOR_CHECKIN" if allowed else "ACCESS_DENIED")
        )
        inc = SentinelIncidentLog(
            companyId=company_id,
            eventType=event_type,
            severity="INFO" if allowed else "WARNING",
            identityId=matched_ident.identityId,
            subjectName=matched_ident.fullName,
            identityType=itype,
            zoneId=zone.zoneId if zone else None,
            zoneName=zone.name if zone else station_mode,
            confidencePercent=confidence_pct,
            distance=round(float(best_distance), 6),
            snapshotUrl=snapshot_url,
            actionTaken=(
                f"Access Granted ({itype})"
                + (" + Door Unlocked" if relay_ok else "")
                if allowed
                else deny_reason
            ),
        )
        db.add(inc)
        await db.commit()
        await db.refresh(inc)
        return {
            "matched": True,
            "accessGranted": allowed,
            "decision": "ACCESS_GRANTED" if allowed else "ACCESS_DENIED",
            "stationMode": station_mode,
            "identityType": itype,
            "subjectName": matched_ident.fullName,
            "confidencePercent": confidence_pct,
            "message": (
                f"อนุญาตให้ผ่าน: {matched_ident.fullName} ({itype})"
                if allowed
                else deny_reason
            ),
            "incident": _serialize_incident(inc),
        }

    _, matched_member_id, _ = emp_match
    matched_member = await db.get(Member, matched_member_id)
    emp_name = (
        f"{matched_member.firstName or ''} {matched_member.lastName or ''}".strip()
        or matched_member.username
        if matched_member
        else "Employee"
    )

    now_local = datetime.now(_bangkok_tz())
    allowed = True
    deny_reason = ""
    if zone is not None:
        if "EMPLOYEE" not in (zone.allowedIdentityTypes or ["EMPLOYEE"]):
            allowed = False
            deny_reason = f"โซน {zone.name} ไม่อนุญาตสำหรับพนักงานทั่วไป"
        elif not _is_within_schedule(zone.scheduleStart, zone.scheduleEnd, now_local):
            allowed = False
            deny_reason = f"อยู่นอกช่วงเวลาเปิดทำการของโซน ({zone.scheduleStart}-{zone.scheduleEnd})"
        elif zone.require2FA and not (totp_or_pin and str(totp_or_pin).strip()):
            allowed = False
            deny_reason = "โซนความมั่นคงสูง: กรุณาระบุรหัส 2FA / PIN ร่วมกับการสแกนใบหน้า"

    relay_ok = False
    if allowed:
        relay_ok = await maybe_dispatch_zone_relay(
            zone, subject_name=emp_name, identity_type="EMPLOYEE"
        )

    inc = SentinelIncidentLog(
        companyId=company_id,
        eventType="ACCESS_GRANTED" if allowed else "ACCESS_DENIED",
        severity="INFO" if allowed else "WARNING",
        memberId=matched_member_id,
        subjectName=emp_name,
        identityType="EMPLOYEE",
        zoneId=zone.zoneId if zone else None,
        zoneName=zone.name if zone else station_mode,
        confidencePercent=confidence_pct,
        distance=round(float(best_distance), 6),
        snapshotUrl=snapshot_url,
        actionTaken=(
            "Employee Verified & Access Granted"
            + (" + Door Unlocked" if relay_ok else "")
            if allowed
            else deny_reason
        ),
    )
    db.add(inc)
    await db.commit()
    await db.refresh(inc)
    return {
        "matched": True,
        "accessGranted": allowed,
        "decision": "ACCESS_GRANTED" if allowed else "ACCESS_DENIED",
        "stationMode": station_mode,
        "identityType": "EMPLOYEE",
        "subjectName": emp_name,
        "confidencePercent": confidence_pct,
        "doorRelayTriggered": relay_ok,
        "message": (
            f"ยืนยันตัวตนสำเร็จ: {emp_name} (พนักงาน)"
            if allowed
            else deny_reason
        ),
        "incident": _serialize_incident(inc),
    }


@router.post("/company/{companyId}/scan")
async def unified_sentinel_scan(
    companyId: UUID,
    request: Request,
    file: UploadFile = File(...),
    zoneId: Optional[str] = Form(None),
    eventId: Optional[str] = Form(None),
    stationMode: str = Form("ACCESS_CONTROL"),
    totpOrPin: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Unified 1:N Biometric Scan:
    1. Extracts 512-d InsightFace embedding on GPU worker.
    2. Queries both `sentinel_identity` (BLACKLIST, POI, VIP, VISITOR, EVENT_ATTENDEE) and Employee `face_encoding`.
    3. Evaluates priority via ``evaluate_unified_scan_decision``.
    """
    await assert_request_company_access(request, db, companyId)
    module_cfg = await get_company_module_config(db, companyId)

    temp_dir = Path("temp_images")
    temp_dir.mkdir(exist_ok=True)
    temp_path = temp_dir / f"scan_{uuid4()}.jpg"
    snapshot_saved = False

    try:
        from ..utils.face_engine import generate_face_encoding

        with temp_path.open("wb") as buf:
            shutil.copyfileobj(file.file, buf)

        encoding = await run_on_face_gpu(
            lambda p=str(temp_path): generate_face_encoding(p),
            kind="checkin",
            company_id=companyId,
        )
        if encoding is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ไม่พบใบหน้าในภาพ กรุณาหันหน้าเข้าหากล้อง",
            )

        snap_name = f"incident_{uuid4()}.jpg"
        store_image_file("uploaded_images", snap_name, temp_path, move=True)
        snapshot_saved = True
        snapshot_url = f"/images/{snap_name}"

        return await evaluate_unified_scan_decision(
            db,
            companyId,
            encoding,
            station_mode=stationMode,
            zone_id=zoneId,
            event_id=eventId,
            totp_or_pin=totpOrPin,
            snapshot_url=snapshot_url,
            scan_action_rules=module_cfg.get("scanActionRules"),
        )
    finally:
        if not snapshot_saved and temp_path.exists():
            temp_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Security Incidents & Edge Fleet Sync
# ---------------------------------------------------------------------------


@router.get("/company/{companyId}/incidents")
async def list_sentinel_incidents(
    companyId: UUID,
    request: Request,
    eventType: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    stmt = select(SentinelIncidentLog).where(SentinelIncidentLog.companyId == companyId)
    if eventType:
        stmt = stmt.where(SentinelIncidentLog.eventType == eventType.strip().upper())
    if severity:
        stmt = stmt.where(SentinelIncidentLog.severity == severity.strip().upper())
    stmt = stmt.order_by(SentinelIncidentLog.occurredAt.desc()).limit(limit).offset(offset)
    rows = (await db.execute(stmt)).scalars().all()
    return [_serialize_incident(r) for r in rows]


@router.post("/company/{companyId}/incidents/{incidentId}/acknowledge")
async def acknowledge_sentinel_incident(
    companyId: UUID,
    incidentId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    inc = await db.get(SentinelIncidentLog, incidentId)
    if not inc or inc.companyId != companyId:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    actor = current_member_var.get()
    inc.acknowledgedBy = actor.memberId if actor else None
    inc.acknowledgedAt = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(inc)
    return _serialize_incident(inc)


@router.get("/company/{companyId}/edge-sync")
async def get_edge_sync_manifest(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Phase 6 Offline-First Edge Kiosk Sync Manifest (Employee + Sentinel vector counts & version)."""
    await assert_request_company_access(request, db, companyId)

    emp_vectors = (
        await db.execute(
            select(func.count())
            .select_from(FaceEncoding)
            .join(CompanyEmployee, CompanyEmployee.memberId == FaceEncoding.memberId)
            .where(
                CompanyEmployee.companyId == companyId,
                CompanyEmployee.deletedAt.is_(None),
            )
        )
    ).scalar() or 0

    sentinel_vectors = (
        await db.execute(
            select(func.count())
            .select_from(SentinelIdentity)
            .where(
                SentinelIdentity.companyId == companyId,
                SentinelIdentity.deletedAt.is_(None),
                SentinelIdentity.status == "ACTIVE",
                SentinelIdentity.embedding.is_not(None),
            )
        )
    ).scalar() or 0

    zones = (
        await db.execute(
            select(SentinelAccessZone).where(
                SentinelAccessZone.companyId == companyId,
                SentinelAccessZone.deletedAt.is_(None),
                SentinelAccessZone.isActive.is_(True),
            )
        )
    ).scalars().all()

    return {
        "companyId": str(companyId),
        "manifestVersion": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
        "embeddingModel": "insightface-buffalo_l-512d",
        "employeeVectorsCount": int(emp_vectors),
        "sentinelVectorsCount": int(sentinel_vectors),
        "totalActiveVectors": int(emp_vectors) + int(sentinel_vectors),
        "activeZones": [_serialize_zone(z) for z in zones],
        "generatedAt": datetime.now(timezone.utc),
    }



async def expire_sentinel_identities_tick() -> dict:
    """
    PDPA Automated Biometric Expiry Sweeper:
    Finds active SentinelIdentity rows whose `expiresAt < now()`, marks them `EXPIRED`,
    and purges their 512-d `embedding` vector from pgvector.
    """
    from ..config.database import async_session

    now = datetime.now(timezone.utc)
    expired_count = 0
    async with async_session() as db:
        rows = (
            await db.execute(
                select(SentinelIdentity).where(
                    SentinelIdentity.deletedAt.is_(None),
                    SentinelIdentity.status == "ACTIVE",
                    SentinelIdentity.expiresAt.is_not(None),
                    SentinelIdentity.expiresAt < now,
                )
            )
        ).scalars().all()
        for ident in rows:
            ident.status = "EXPIRED"
            ident.embedding = None
            expired_count += 1
        if expired_count > 0:
            await db.commit()
    return {"expiredIdentitiesPurged": expired_count}


async def evaluate_kiosk_sentinel_match(
    db: AsyncSession,
    company_id: UUID,
    target_encoding: List[float],
    threshold: float,
) -> Optional[dict]:
    """
    Evaluates a live Kiosk face embedding against `sentinel_identity`.
    Logs an incident and dispatches a silent webhook if `BLACKLIST`/`POI` is detected,
    or returns enriched `sentinelMatch` metadata for `VIP`/`VISITOR`/`EVENT_ATTENDEE`.
    """
    match = await search_sentinel_identity_pgvector(
        db, target_encoding, threshold, companyId=company_id
    )
    if match is None:
        return None
    ident, distance = match
    confidence_pct = round(max(0.0, min(1.0, 1.0 - float(distance))) * 100.0, 2)
    itype = ident.identityType

    event_type = (
        "BLACKLIST_ALERT"
        if itype in ("BLACKLIST", "POI")
        else ("VIP_ARRIVAL" if itype == "VIP" else ("EVENT_CHECKIN" if itype == "EVENT_ATTENDEE" else "VISITOR_CHECKIN"))
    )
    severity = "CRITICAL" if itype == "BLACKLIST" else ("WARNING" if itype == "POI" else "INFO")
    action_taken = (
        f"Kiosk Silent Alert ({ident.alertNote or 'Watchlist match'})"
        if itype in ("BLACKLIST", "POI")
        else (f"Kiosk Seat: {ident.seatNumber}" if ident.seatNumber else f"Kiosk Verified ({itype})")
    )

    inc = SentinelIncidentLog(
        companyId=company_id,
        eventType=event_type,
        severity=severity,
        identityId=ident.identityId,
        subjectName=ident.fullName,
        identityType=itype,
        zoneName="Live Face Kiosk",
        eventId=ident.eventId,
        confidencePercent=confidence_pct,
        distance=round(float(distance), 6),
        snapshotUrl=ident.pictureUrl,
        actionTaken=action_taken,
    )
    db.add(inc)
    if itype in ("BLACKLIST", "POI"):
        # Staff-only channel: carries the full who/where/when/snapshot that the kiosk
        # response deliberately omits (see face_controller.kiosk_access_denied).
        db.add(
            NotificationOutbox(
                companyId=company_id,
                event="sentinel.blacklist_detected",
                channel="webhook",
                payload={
                    "companyId": str(company_id),
                    "identityId": str(ident.identityId),
                    "subjectName": ident.fullName,
                    "identityType": itype,
                    "severity": ident.severity,
                    "alertNote": ident.alertNote,
                    "zoneName": "Live Face Kiosk",
                    "detectedAt": datetime.now(timezone.utc).isoformat(),
                    "confidencePercent": confidence_pct,
                    "distance": round(float(distance), 6),
                    "snapshotUrl": ident.pictureUrl,
                },
            )
        )
    await db.commit()
    return {
        "identityId": str(ident.identityId),
        "identityType": itype,
        "fullName": ident.fullName,
        "severity": ident.severity,
        "alertNote": ident.alertNote,
        "seatNumber": ident.seatNumber,
        "pictureUrl": ident.pictureUrl,
        "distance": round(float(distance), 6),
        "confidencePercent": confidence_pct,
        "accessGranted": itype not in ("BLACKLIST", "POI"),
    }
