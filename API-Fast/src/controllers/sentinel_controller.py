"""SentinelVision orchestration — overview, identities, zones, events, scan, edge-sync."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import shutil
from typing import Optional
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.company_employee import CompanyEmployee
from ..models.face_encoding import FaceEncoding
from ..models.sentinel import (
    SentinelAccessZone,
    SentinelEvent,
    SentinelIdentity,
    SentinelIncidentLog,
)
from ..security.deps import current_member_var
from ..services.company_module_service import get_company_module_config
from ..services.outbox_crypto import seal_relay_secret
from ..services.sentinel_muster_service import build_muster_roll
from ..services.sentinel_identity_service import (
    VALID_IDENTITY_TYPES,
    VALID_SEVERITIES,
    VALID_STATION_MODES,
    bangkok_tz,
    parse_iso_dt,
    serialize_event,
    serialize_identity,
    serialize_zone,
)
from ..services.sentinel_incident_service import (
    dispatch_relay_webhook_async,
    evaluate_unified_scan_decision,
    record_incident,
    serialize_incident,
    store_incident_snapshot,
)
from ..services.storage_service import store_image_file
from ..utils.face_gpu_queue import run_on_face_gpu


async def get_overview(db: AsyncSession, company_id: UUID) -> dict:
    identities = (
        await db.execute(
            select(SentinelIdentity).where(
                SentinelIdentity.companyId == company_id,
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
                SentinelAccessZone.companyId == company_id,
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
                SentinelEvent.companyId == company_id,
                SentinelEvent.deletedAt.is_(None),
                SentinelEvent.status.in_(["LIVE", "UPCOMING"]),
            )
        )
    ).scalar() or 0

    recent_incidents = (
        await db.execute(
            select(SentinelIncidentLog)
            .where(SentinelIncidentLog.companyId == company_id)
            .order_by(SentinelIncidentLog.occurredAt.desc())
            .limit(15)
        )
    ).scalars().all()

    unack_alerts = (
        await db.execute(
            select(func.count())
            .select_from(SentinelIncidentLog)
            .where(
                SentinelIncidentLog.companyId == company_id,
                SentinelIncidentLog.severity.in_(["WARNING", "CRITICAL"]),
                SentinelIncidentLog.acknowledgedAt.is_(None),
            )
        )
    ).scalar() or 0

    # F4: muster from C1 attendance_daily PRESENT + open presence + visitor incidents
    muster = await build_muster_roll(db, company_id, limit=100, offset=0)

    return {
        "summary": {
            "blacklistAndPoiCount": blacklist_count,
            "vipCount": vip_count,
            "activeVisitorCount": visitor_count,
            "eventAttendeeCount": event_attendee_count,
            "activeZonesCount": int(zones_count),
            "liveEventsCount": int(live_events_count),
            "unacknowledgedAlerts": int(unack_alerts),
            "buildingOccupancyCount": int(muster.get("total") or 0),
        },
        "musterRoll": muster.get("items") or [],
        "musterMeta": {
            "total": muster.get("total"),
            "limit": muster.get("limit"),
            "offset": muster.get("offset"),
            "workDate": muster.get("workDate"),
        },
        "recentIncidents": [serialize_incident(inc) for inc in recent_incidents],
    }


async def list_identities(
    db: AsyncSession,
    company_id: UUID,
    *,
    identity_type: Optional[str] = None,
    event_id: Optional[UUID] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    stmt = select(SentinelIdentity).where(
        SentinelIdentity.companyId == company_id,
        SentinelIdentity.deletedAt.is_(None),
    )
    if identity_type:
        types = [t.strip().upper() for t in identity_type.split(",") if t.strip()]
        if types:
            stmt = stmt.where(SentinelIdentity.identityType.in_(types))
    if event_id:
        stmt = stmt.where(SentinelIdentity.eventId == event_id)
    stmt = stmt.order_by(SentinelIdentity.createdAt.desc()).limit(limit).offset(offset)
    rows = (await db.execute(stmt)).scalars().all()
    return [serialize_identity(r) for r in rows]


async def create_identity(db: AsyncSession, company_id: UUID, body: dict) -> dict:
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

    expires_at = parse_iso_dt(body.get("expiresAt"))
    if expires_at is None and identity_type == "VISITOR":
        expires_at = datetime.now(timezone.utc) + timedelta(hours=12)

    allowed_zones = body.get("allowedZoneIds")
    if not isinstance(allowed_zones, list):
        allowed_zones = []

    identity = SentinelIdentity(
        companyId=company_id,
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
    return serialize_identity(identity)


async def update_identity(
    db: AsyncSession, company_id: UUID, identity_id: UUID, body: dict
) -> dict:
    ident = await db.get(SentinelIdentity, identity_id)
    if not ident or ident.companyId != company_id or ident.deletedAt is not None:
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
        ident.expiresAt = parse_iso_dt(body.get("expiresAt"))
    if "allowedZoneIds" in body and isinstance(body["allowedZoneIds"], list):
        ident.allowedZoneIds = [str(z) for z in body["allowedZoneIds"] if z]

    await db.commit()
    await db.refresh(ident)
    return serialize_identity(ident)


async def delete_identity(db: AsyncSession, company_id: UUID, identity_id: UUID) -> dict:
    ident = await db.get(SentinelIdentity, identity_id)
    if not ident or ident.companyId != company_id or ident.deletedAt is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Identity not found")
    ident.deletedAt = datetime.now(timezone.utc)
    ident.status = "REVOKED"
    ident.embedding = None
    await db.commit()
    return {"deleted": True, "identityId": str(identity_id)}


async def enroll_identity_face(
    db: AsyncSession, company_id: UUID, identity_id: UUID, file: UploadFile
) -> dict:
    ident = await db.get(SentinelIdentity, identity_id)
    if not ident or ident.companyId != company_id or ident.deletedAt is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Identity not found")

    temp_dir = Path("temp_images")
    temp_dir.mkdir(exist_ok=True)
    temp_path = temp_dir / f"sentinel_{uuid4()}.jpg"
    moved = False

    try:
        from ..utils.face_engine import generate_face_encoding

        with temp_path.open("wb") as buf:
            shutil.copyfileobj(file.file, buf)

        path_str = str(temp_path)

        def _encode_enroll(p: str = path_str):
            return generate_face_encoding(p)

        encoding = await run_on_face_gpu(
            _encode_enroll,
            kind="other",
            company_id=company_id,
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
            "identity": serialize_identity(ident),
        }
    finally:
        if not moved and temp_path.exists():
            temp_path.unlink(missing_ok=True)


async def list_zones(db: AsyncSession, company_id: UUID) -> list[dict]:
    rows = (
        await db.execute(
            select(SentinelAccessZone)
            .where(
                SentinelAccessZone.companyId == company_id,
                SentinelAccessZone.deletedAt.is_(None),
            )
            .order_by(SentinelAccessZone.createdAt.asc())
        )
    ).scalars().all()
    return [serialize_zone(z) for z in rows]


async def create_zone(db: AsyncSession, company_id: UUID, body: dict) -> dict:
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

    floor_raw = body.get("siteFloorId")
    floor_id = UUID(str(floor_raw)) if floor_raw else None
    map_x = body.get("mapPosX")
    map_y = body.get("mapPosY")

    zone = SentinelAccessZone(
        companyId=company_id,
        name=name,
        code=str(body.get("code") or "GATE-01").strip().upper(),
        locationId=loc_id,
        siteFloorId=floor_id,
        mapPosX=None if map_x in (None, "") else float(map_x),
        mapPosY=None if map_y in (None, "") else float(map_y),
        stationMode=station_mode,
        allowedDepartments=[str(d) for d in allowed_depts if d],
        allowedIdentityTypes=[str(t).upper() for t in allowed_types if t],
        scheduleStart=str(body.get("scheduleStart") or "00:00").strip(),
        scheduleEnd=str(body.get("scheduleEnd") or "23:59").strip(),
        require2FA=bool(body.get("require2FA", False)),
        relayWebhookUrl=str(body.get("relayWebhookUrl") or "").strip() or None,
        relaySecret=seal_relay_secret(str(body.get("relaySecret") or "").strip() or None),
        isActive=bool(body.get("isActive", True)),
    )
    db.add(zone)
    await db.commit()
    await db.refresh(zone)
    return serialize_zone(zone)


async def update_zone(db: AsyncSession, company_id: UUID, zone_id: UUID, body: dict) -> dict:
    zone = await db.get(SentinelAccessZone, zone_id)
    if not zone or zone.companyId != company_id or zone.deletedAt is not None:
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
        zone.relaySecret = seal_relay_secret(str(body.get("relaySecret") or "").strip() or None)
    if "isActive" in body:
        zone.isActive = bool(body["isActive"])
    if "locationId" in body:
        loc_raw = body.get("locationId")
        zone.locationId = UUID(str(loc_raw)) if loc_raw else None
    if "siteFloorId" in body:
        floor_raw = body.get("siteFloorId")
        zone.siteFloorId = UUID(str(floor_raw)) if floor_raw else None
    if "mapPosX" in body:
        zone.mapPosX = None if body.get("mapPosX") in (None, "") else float(body["mapPosX"])
    if "mapPosY" in body:
        zone.mapPosY = None if body.get("mapPosY") in (None, "") else float(body["mapPosY"])

    await db.commit()
    await db.refresh(zone)
    return serialize_zone(zone)


async def delete_zone(db: AsyncSession, company_id: UUID, zone_id: UUID) -> dict:
    zone = await db.get(SentinelAccessZone, zone_id)
    if not zone or zone.companyId != company_id or zone.deletedAt is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access zone not found")
    zone.deletedAt = datetime.now(timezone.utc)
    zone.isActive = False
    await db.commit()
    return {"deleted": True, "zoneId": str(zone_id)}


async def trigger_zone(
    db: AsyncSession, company_id: UUID, zone_id: UUID, body: Optional[dict] = None
) -> dict:
    zone = await db.get(SentinelAccessZone, zone_id)
    if not zone or zone.companyId != company_id or zone.deletedAt is not None:
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
        relay_ok = await dispatch_relay_webhook_async(
            zone.relayWebhookUrl,
            zone.relaySecret,
            {
                "event": "door.remote_unlock",
                "companyId": str(company_id),
                "zoneId": str(zone.zoneId),
                "zoneCode": zone.code,
                "zoneName": zone.name,
                "triggeredBy": actor_name,
                "reason": reason,
            },
        )

    inc, _ = await record_incident(
        db,
        company_id=company_id,
        event_type="ACCESS_GRANTED",
        severity="INFO",
        member_id=actor.memberId if actor else None,
        subject_name=actor_name,
        identity_type="ADMIN_REMOTE",
        zone_id=zone.zoneId,
        zone_name=zone.name,
        action_taken=(
            f"Remote unlock pulse sent ({reason})"
            + (" [Relay OK]" if relay_ok else " [Simulated Relay]")
        ),
    )
    return {
        "unlocked": True,
        "relayDispatched": relay_ok,
        "zone": serialize_zone(zone),
        "incident": serialize_incident(inc),
    }


async def list_events(db: AsyncSession, company_id: UUID) -> list[dict]:
    events = (
        await db.execute(
            select(SentinelEvent)
            .where(
                SentinelEvent.companyId == company_id,
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
                    SentinelIdentity.companyId == company_id,
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
                    SentinelIncidentLog.companyId == company_id,
                    SentinelIncidentLog.eventId == ev.eventId,
                    SentinelIncidentLog.eventType == "EVENT_CHECKIN",
                )
            )
        ).scalar() or 0
        result.append(serialize_event(ev, int(attendee_cnt), int(checkin_cnt)))
    return result


async def create_event(db: AsyncSession, company_id: UUID, body: dict) -> dict:
    name = str(body.get("name") or "").strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Event name is required"
        )
    now = datetime.now(bangkok_tz())
    start_at = parse_iso_dt(body.get("startAt")) or now
    end_at = parse_iso_dt(body.get("endAt")) or (start_at + timedelta(hours=8))

    ev = SentinelEvent(
        companyId=company_id,
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
    return serialize_event(ev, 0, 0)


async def delete_event(db: AsyncSession, company_id: UUID, event_id: UUID) -> dict:
    ev = await db.get(SentinelEvent, event_id)
    if not ev or ev.companyId != company_id or ev.deletedAt is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    ev.deletedAt = datetime.now(timezone.utc)
    ev.status = "CLOSED"
    await db.commit()
    return {"deleted": True, "eventId": str(event_id)}


async def unified_scan(
    db: AsyncSession,
    company_id: UUID,
    file: UploadFile,
    *,
    zone_id: Optional[str] = None,
    event_id: Optional[str] = None,
    station_mode: str = "ACCESS_CONTROL",
    totp_or_pin: Optional[str] = None,
) -> dict:
    module_cfg = await get_company_module_config(db, company_id)

    temp_dir = Path("temp_images")
    temp_dir.mkdir(exist_ok=True)
    temp_path = temp_dir / f"scan_{uuid4()}.jpg"
    snapshot_saved = False

    try:
        from ..utils.face_engine import generate_face_encoding

        with temp_path.open("wb") as buf:
            shutil.copyfileobj(file.file, buf)

        path_str = str(temp_path)

        def _encode_scan(p: str = path_str):
            return generate_face_encoding(p)

        encoding = await run_on_face_gpu(
            _encode_scan,
            kind="checkin",
            company_id=company_id,
        )
        if encoding is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ไม่พบใบหน้าในภาพ กรุณาหันหน้าเข้าหากล้อง",
            )

        snap_name = f"incident_{uuid4()}.jpg"
        store_incident_snapshot(snap_name, temp_path)
        snapshot_saved = True
        snapshot_url = f"/images/{snap_name}"

        return await evaluate_unified_scan_decision(
            db,
            company_id,
            encoding,
            station_mode=station_mode,
            zone_id=zone_id,
            event_id=event_id,
            totp_or_pin=totp_or_pin,
            snapshot_url=snapshot_url,
            scan_action_rules=module_cfg.get("scanActionRules"),
        )
    finally:
        if not snapshot_saved and temp_path.exists():
            temp_path.unlink(missing_ok=True)


async def edge_sync_manifest(db: AsyncSession, company_id: UUID) -> dict:
    emp_vectors = (
        await db.execute(
            select(func.count())
            .select_from(FaceEncoding)
            .join(CompanyEmployee, CompanyEmployee.memberId == FaceEncoding.memberId)
            .where(
                CompanyEmployee.companyId == company_id,
                CompanyEmployee.deletedAt.is_(None),
            )
        )
    ).scalar() or 0

    sentinel_vectors = (
        await db.execute(
            select(func.count())
            .select_from(SentinelIdentity)
            .where(
                SentinelIdentity.companyId == company_id,
                SentinelIdentity.deletedAt.is_(None),
                SentinelIdentity.status == "ACTIVE",
                SentinelIdentity.embedding.is_not(None),
            )
        )
    ).scalar() or 0

    zones = (
        await db.execute(
            select(SentinelAccessZone).where(
                SentinelAccessZone.companyId == company_id,
                SentinelAccessZone.deletedAt.is_(None),
                SentinelAccessZone.isActive.is_(True),
            )
        )
    ).scalars().all()

    return {
        "companyId": str(company_id),
        "manifestVersion": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
        "embeddingModel": "insightface-buffalo_l-512d",
        "employeeVectorsCount": int(emp_vectors),
        "sentinelVectorsCount": int(sentinel_vectors),
        "totalActiveVectors": int(emp_vectors) + int(sentinel_vectors),
        "activeZones": [serialize_zone(z) for z in zones],
        "generatedAt": datetime.now(timezone.utc),
    }
