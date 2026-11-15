"""SentinelVision orchestration — overview, identities, zones, events, scan, edge-sync."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math
from pathlib import Path
import shutil
import time
from typing import Any, Optional
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status
import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.camera import Camera
from ..models.company_employee import CompanyEmployee
from ..models.face_encoding import FaceEncoding
from ..models.sentinel import (
    SentinelAccessZone,
    SentinelEvent,
    SentinelIdentity,
    SentinelIncidentLog,
)
from ..services.notification_service import NotificationOutbox
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
        mapPosX=float(str(map_x)) if map_x not in (None, "") else None,
        mapPosY=float(str(map_y)) if map_y not in (None, "") else None,
        stationMode=station_mode,
        allowedDepartments=[str(d) for d in allowed_depts if d],
        allowedIdentityTypes=[str(t).upper() for t in allowed_types if t],
        scheduleStart=str(body.get("scheduleStart") or "00:00").strip(),
        scheduleEnd=str(body.get("scheduleEnd") or "23:59").strip(),
        require2FA=bool(body.get("require2FA", False)),
        relayWebhookUrl=str(body.get("relayWebhookUrl") or "").strip() or None,
        relaySecret=seal_relay_secret(str(body.get("relaySecret") or "").strip() or None),
        direction=(
            str(body.get("direction") or "BIDIRECTIONAL").strip().upper()
            if str(body.get("direction") or "BIDIRECTIONAL").strip().upper()
            in {"ENTRY", "EXIT", "BIDIRECTIONAL"}
            else "BIDIRECTIONAL"
        ),
        antiPassbackEnabled=bool(body.get("antiPassbackEnabled", False)),
        antiPassbackMinutes=max(1, int(body.get("antiPassbackMinutes") or 5)),
        doorHeldMaxSeconds=max(5, int(body.get("doorHeldMaxSeconds") or 30)),
        doorOpenSince=parse_iso_dt(body.get("doorOpenSince")),
        edgeProtocol=(
            str(body.get("edgeProtocol") or "WEBHOOK").strip().upper()
            if str(body.get("edgeProtocol") or "WEBHOOK").strip().upper()
            in {"WEBHOOK", "WIEGAND", "OSDP"}
            else "WEBHOOK"
        ),
        edgeBridgeUrl=str(body.get("edgeBridgeUrl") or "").strip() or None,
        osdpAddress=max(0, min(126, int(body.get("osdpAddress") or 0))),
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
    if "direction" in body:
        d_val = str(body.get("direction") or "BIDIRECTIONAL").strip().upper()
        if d_val in {"ENTRY", "EXIT", "BIDIRECTIONAL"}:
            zone.direction = d_val
    if "antiPassbackEnabled" in body:
        zone.antiPassbackEnabled = bool(body["antiPassbackEnabled"])
    if "antiPassbackMinutes" in body and body.get("antiPassbackMinutes") is not None:
        zone.antiPassbackMinutes = max(1, int(body["antiPassbackMinutes"]))
    if "doorHeldMaxSeconds" in body and body.get("doorHeldMaxSeconds") is not None:
        zone.doorHeldMaxSeconds = max(5, int(body["doorHeldMaxSeconds"]))
    if "doorOpenSince" in body:
        zone.doorOpenSince = parse_iso_dt(body.get("doorOpenSince"))
    if "edgeProtocol" in body:
        proto = str(body.get("edgeProtocol") or "WEBHOOK").strip().upper()
        if proto in {"WEBHOOK", "WIEGAND", "OSDP"}:
            zone.edgeProtocol = proto
    if "edgeBridgeUrl" in body:
        zone.edgeBridgeUrl = str(body.get("edgeBridgeUrl") or "").strip() or None
    if "osdpAddress" in body and body.get("osdpAddress") is not None:
        zone.osdpAddress = max(0, min(126, int(body["osdpAddress"])))
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


async def trigger_fire_alarm(
    db: AsyncSession, company_id: UUID, body: Optional[dict] = None
) -> dict:
    """BL-13: Unlock all active access zones simultaneously on Fire Alarm signal."""
    import asyncio

    zones = (
        await db.execute(
            select(SentinelAccessZone).where(
                SentinelAccessZone.companyId == company_id,
                SentinelAccessZone.deletedAt.is_(None),
                SentinelAccessZone.isActive.is_(True),
            )
        )
    ).scalars().all()

    actor = current_member_var.get()
    actor_name = (
        f"{actor.firstName or ''} {actor.lastName or ''}".strip() or actor.username
        if actor
        else str((body or {}).get("source") or "Fire Alarm Panel")
    )
    reason = str((body or {}).get("reason") or "Emergency Fire Alarm Fail-Safe")

    async def _unlock_one(z: SentinelAccessZone) -> dict:
        dispatched = False
        if z.relayWebhookUrl:
            dispatched = await dispatch_relay_webhook_async(
                z.relayWebhookUrl,
                z.relaySecret,
                {
                    "event": "door.fire_alarm_unlock",
                    "companyId": str(company_id),
                    "zoneId": str(z.zoneId),
                    "zoneCode": z.code,
                    "zoneName": z.name,
                    "triggeredBy": actor_name,
                    "reason": reason,
                },
            )
        return {
            "zoneId": str(z.zoneId),
            "zoneCode": z.code,
            "zoneName": z.name,
            "unlocked": True,
            "relayDispatched": dispatched,
        }

    results = await asyncio.gather(*[_unlock_one(z) for z in zones]) if zones else []
    inc, _ = await record_incident(
        db,
        company_id=company_id,
        event_type="FIRE_ALARM_TRIGGERED",
        severity="CRITICAL",
        member_id=actor.memberId if actor else None,
        subject_name=actor_name,
        identity_type="EMERGENCY_SYSTEM",
        action_taken=f"ALL_DOORS_UNLOCKED ({len(results)} zones) — {reason}",
    )
    return {
        "status": "FIRE_ALARM_ACTIVE",
        "totalZones": len(results),
        "unlockedCount": len(results),
        "results": list(results),
        "incident": serialize_incident(inc),
    }


async def reset_fire_alarm(
    db: AsyncSession, company_id: UUID, body: Optional[dict] = None
) -> dict:
    """BL-13: Log Fire Alarm reset and restore normal access control."""
    actor = current_member_var.get()
    actor_name = (
        f"{actor.firstName or ''} {actor.lastName or ''}".strip() or actor.username
        if actor
        else "Security Console"
    )
    reason = str((body or {}).get("reason") or "All clear — normal operation restored")
    inc, _ = await record_incident(
        db,
        company_id=company_id,
        event_type="FIRE_ALARM_RESET",
        severity="INFO",
        member_id=actor.memberId if actor else None,
        subject_name=actor_name,
        identity_type="EMERGENCY_SYSTEM",
        action_taken=f"NORMAL_OPERATION_RESTORED — {reason}",
    )
    return {
        "status": "NORMAL",
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


_REINDEX_STATUS_BY_COMPANY: dict[str, dict[str, Any]] = {}


def _l2_normalize_vector(raw: Any) -> Optional[list[float]]:
    if raw is None:
        return None
    vec = [float(x) for x in raw]
    if not vec:
        return None
    norm = math.sqrt(sum(v * v for v in vec))
    if norm <= 0.0:
        return vec
    return [v / norm for v in vec]


async def evaluate_zone_access(
    db: AsyncSession,
    company_id: UUID,
    zone_id: UUID,
    body: Optional[dict] = None,
) -> dict:
    """BL-14: Tailgating AI detection (peopleCount > 1) & Anti-Passback enforcement."""
    zone = await db.get(SentinelAccessZone, zone_id)
    if not zone or zone.companyId != company_id or zone.deletedAt is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access zone not found")

    payload = body or {}
    direction = str(payload.get("direction") or getattr(zone, "direction", None) or "ENTRY").strip().upper()
    if direction not in {"ENTRY", "EXIT", "BIDIRECTIONAL"}:
        direction = "ENTRY"
    people_count = max(1, int(payload.get("peopleCount") or 1))
    subject_name = str(payload.get("subjectName") or "Unknown").strip() or "Unknown"
    member_raw = payload.get("memberId")
    identity_raw = payload.get("identityId")
    member_id = UUID(str(member_raw)) if member_raw else None
    identity_id = UUID(str(identity_raw)) if identity_raw else None
    now = datetime.now(timezone.utc)

    incidents: list[dict] = []
    tailgating_detected = people_count > 1
    if tailgating_detected:
        inc, _ = await record_incident(
            db,
            company_id=company_id,
            event_type="TAILGATING_DETECTED",
            severity="HIGH",
            identity_id=identity_id,
            member_id=member_id,
            subject_name=subject_name,
            zone_id=zone.zoneId,
            zone_name=zone.name,
            direction=direction,
            action_taken=f"Detected {people_count} people in single badge/face scan",
            commit=False,
        )
        incidents.append(serialize_incident(inc))

    apb_violation = False
    apb_enabled = bool(getattr(zone, "antiPassbackEnabled", False))
    apb_minutes = max(1, int(getattr(zone, "antiPassbackMinutes", 5) or 5))
    if apb_enabled and direction == "ENTRY" and (member_id or identity_id):
        since = now - timedelta(minutes=apb_minutes)
        stmt = (
            select(SentinelIncidentLog)
            .where(
                SentinelIncidentLog.companyId == company_id,
                SentinelIncidentLog.zoneId == zone.zoneId,
                SentinelIncidentLog.occurredAt >= since,
                SentinelIncidentLog.eventType.in_(("ACCESS_GRANTED", "ACCESS_SCAN_ENTRY", "ANTI_PASSBACK_VIOLATION")),
            )
            .order_by(SentinelIncidentLog.occurredAt.desc())
            .limit(5)
        )
        if member_id:
            stmt = stmt.where(SentinelIncidentLog.memberId == member_id)
        else:
            stmt = stmt.where(SentinelIncidentLog.identityId == identity_id)
        recent = (await db.execute(stmt)).scalars().first()
        if recent is not None and (getattr(recent, "direction", None) or "ENTRY").upper() == "ENTRY":
            apb_violation = True
            inc, _ = await record_incident(
                db,
                company_id=company_id,
                event_type="ANTI_PASSBACK_VIOLATION",
                severity="MEDIUM",
                identity_id=identity_id,
                member_id=member_id,
                subject_name=subject_name,
                zone_id=zone.zoneId,
                zone_name=zone.name,
                direction=direction,
                action_taken=f"Consecutive ENTRY within {apb_minutes}m without EXIT",
                commit=False,
            )
            incidents.append(serialize_incident(inc))

    allowed = not apb_violation
    if allowed and not tailgating_detected and (member_id or identity_id):
        await record_incident(
            db,
            company_id=company_id,
            event_type="ACCESS_SCAN_ENTRY" if direction == "ENTRY" else "ACCESS_SCAN_EXIT",
            severity="INFO",
            identity_id=identity_id,
            member_id=member_id,
            subject_name=subject_name,
            zone_id=zone.zoneId,
            zone_name=zone.name,
            direction=direction,
            action_taken=f"{direction} recorded",
            commit=False,
        )

    await db.commit()
    return {
        "zoneId": str(zone.zoneId),
        "zoneName": zone.name,
        "direction": direction,
        "peopleCount": people_count,
        "allowed": allowed,
        "tailgatingDetected": tailgating_detected,
        "antiPassbackViolation": apb_violation,
        "incidents": incidents,
        "evaluatedAt": now,
    }


async def run_company_health_check(db: AsyncSession, company_id: UUID) -> dict:
    """BL-15: Camera RTSP offline & Door held-open monitor."""
    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(minutes=3)

    cameras = (
        await db.execute(
            select(Camera).where(Camera.companyId == company_id)
        )
    ).scalars().all()

    offline_cameras: list[dict] = []
    for cam in cameras:
        cam_status = str(getattr(cam, "status", "") or "").strip().lower()
        last_ping = getattr(cam, "lastPingAt", None)
        if last_ping is not None and last_ping.tzinfo is None:
            last_ping = last_ping.replace(tzinfo=timezone.utc)
        is_offline = cam_status == "offline" or (last_ping is not None and last_ping < stale_cutoff)
        if is_offline:
            inc, _ = await record_incident(
                db,
                company_id=company_id,
                event_type="CAMERA_OFFLINE",
                severity="HIGH",
                subject_name=cam.name,
                zone_id=getattr(cam, "zoneId", None),
                camera_id=cam.cameraId,
                action_taken=f"Camera {cam.name} offline or stale heartbeat",
                commit=False,
            )
            offline_cameras.append({
                "cameraId": str(cam.cameraId),
                "name": cam.name,
                "status": cam.status,
                "incidentId": str(inc.incidentId),
            })

    zones = (
        await db.execute(
            select(SentinelAccessZone).where(
                SentinelAccessZone.companyId == company_id,
                SentinelAccessZone.deletedAt.is_(None),
                SentinelAccessZone.isActive.is_(True),
            )
        )
    ).scalars().all()

    held_open_doors: list[dict] = []
    for z in zones:
        opened_at = getattr(z, "doorOpenSince", None)
        if opened_at is None:
            continue
        if opened_at.tzinfo is None:
            opened_at = opened_at.replace(tzinfo=timezone.utc)
        max_sec = max(5, int(getattr(z, "doorHeldMaxSeconds", 30) or 30))
        open_seconds = int((now - opened_at).total_seconds())
        if open_seconds > max_sec:
            def _make_outbox(
                zone_obj: SentinelAccessZone = z,
                secs: int = open_seconds,
                limit: int = max_sec,
            ) -> NotificationOutbox:
                return NotificationOutbox(
                    companyId=company_id,
                    event="DOOR_HELD_OPEN",
                    channel="WEBHOOK",
                    payload={
                        "companyId": str(company_id),
                        "zoneId": str(zone_obj.zoneId),
                        "zoneName": zone_obj.name,
                        "openSeconds": secs,
                        "thresholdSeconds": limit,
                    },
                    status="pending",
                )

            inc, _ = await record_incident(
                db,
                company_id=company_id,
                event_type="DOOR_HELD_OPEN",
                severity="HIGH",
                subject_name=z.name,
                zone_id=z.zoneId,
                zone_name=z.name,
                action_taken=f"Door held open {open_seconds}s (limit {max_sec}s)",
                outbox_factory=_make_outbox,
                commit=False,
            )
            held_open_doors.append({
                "zoneId": str(z.zoneId),
                "zoneName": z.name,
                "openSeconds": open_seconds,
                "thresholdSeconds": max_sec,
                "incidentId": str(inc.incidentId),
            })

    await db.commit()
    return {
        "companyId": str(company_id),
        "checkedCameras": len(cameras),
        "offlineCameras": offline_cameras,
        "checkedZones": len(zones),
        "doorHeldOpen": held_open_doors,
        "checkedAt": now,
    }


async def reindex_company_vectors(
    db: AsyncSession,
    company_id: UUID,
    body: Optional[dict] = None,
) -> dict:
    """BL-16: Batch normalize & version-tag active 512-d embeddings."""
    payload = body or {}
    target_model = str(payload.get("targetModel") or "buffalo_l-512d-norm-v2").strip() or "buffalo_l-512d-norm-v2"

    emp_rows = (
        await db.execute(
            select(FaceEncoding)
            .join(CompanyEmployee, CompanyEmployee.memberId == FaceEncoding.memberId)
            .where(
                CompanyEmployee.companyId == company_id,
                CompanyEmployee.deletedAt.is_(None),
            )
        )
    ).scalars().all()

    emp_count = 0
    for enc in emp_rows:
        normed = _l2_normalize_vector(getattr(enc, "embedding", None))
        if normed is not None:
            enc.embedding = normed
        enc.modelVersion = target_model
        emp_count += 1

    sentinel_rows = (
        await db.execute(
            select(SentinelIdentity).where(
                SentinelIdentity.companyId == company_id,
                SentinelIdentity.deletedAt.is_(None),
                SentinelIdentity.status == "ACTIVE",
                SentinelIdentity.embedding.is_not(None),
            )
        )
    ).scalars().all()

    sentinel_count = 0
    for ident in sentinel_rows:
        normed = _l2_normalize_vector(getattr(ident, "embedding", None))
        if normed is not None:
            ident.embedding = normed
            sentinel_count += 1

    await db.commit()
    now = datetime.now(timezone.utc)
    result = {
        "companyId": str(company_id),
        "targetModel": target_model,
        "employeeVectors": emp_count,
        "sentinelVectors": sentinel_count,
        "processedCount": emp_count + sentinel_count,
        "status": "COMPLETED",
        "completedAt": now,
    }
    _REINDEX_STATUS_BY_COMPANY[str(company_id)] = result
    return result


async def get_reindex_status(db: AsyncSession, company_id: UUID) -> dict:
    cached = _REINDEX_STATUS_BY_COMPANY.get(str(company_id))
    if cached:
        return cached
    manifest = await edge_sync_manifest(db, company_id)
    return {
        "companyId": str(company_id),
        "targetModel": manifest["embeddingModel"],
        "employeeVectors": manifest["employeeVectorsCount"],
        "sentinelVectors": manifest["sentinelVectorsCount"],
        "processedCount": manifest["totalActiveVectors"],
        "status": "IDLE",
        "completedAt": None,
    }


async def edge_unlock_zone(
    db: AsyncSession,
    company_id: UUID,
    zone_id: UUID,
    body: Optional[dict] = None,
) -> dict:
    """BL-17: Wiegand-26 / OSDP RS-485 edge bridge unlock dispatch."""
    zone = await db.get(SentinelAccessZone, zone_id)
    if not zone or zone.companyId != company_id or zone.deletedAt is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access zone not found")

    payload_in = body or {}
    protocol = str(getattr(zone, "edgeProtocol", None) or payload_in.get("protocol") or "WEBHOOK").strip().upper()
    if protocol not in {"WEBHOOK", "WIEGAND", "OSDP"}:
        protocol = "WEBHOOK"
    bridge_url = getattr(zone, "edgeBridgeUrl", None) or getattr(zone, "relayWebhookUrl", None)
    osdp_addr = int(getattr(zone, "osdpAddress", 0) or 0)
    card_number = int(payload_in.get("cardNumber") or 1001)
    facility_code = int(payload_in.get("facilityCode") or 42)
    duration_ms = max(500, min(30000, int(payload_in.get("durationMs") or 3000)))

    edge_frame: dict[str, Any] = {
        "zoneId": str(zone.zoneId),
        "zoneCode": zone.code,
        "protocol": protocol,
        "durationMs": duration_ms,
    }
    if protocol == "WIEGAND":
        edge_frame["wiegandBits"] = 26
        edge_frame["facilityCode"] = facility_code
        edge_frame["cardNumber"] = card_number
    elif protocol == "OSDP":
        edge_frame["osdpAddress"] = osdp_addr
        edge_frame["osdpCommand"] = "osdp_OUT"
        edge_frame["outputNo"] = 0

    t0 = time.perf_counter()
    dispatched = False
    error_detail: Optional[str] = None
    if bridge_url:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.post(bridge_url, json=edge_frame)
                dispatched = 200 <= resp.status_code < 300
                if not dispatched:
                    error_detail = f"HTTP {resp.status_code}"
        except Exception as exc:
            error_detail = str(exc)
    else:
        dispatched = True

    latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    return {
        "zoneId": str(zone.zoneId),
        "protocol": protocol,
        "osdpAddress": osdp_addr if protocol == "OSDP" else None,
        "bridgeUrl": bridge_url,
        "dispatched": dispatched,
        "latencyMs": latency_ms,
        "frame": edge_frame,
        "error": error_detail,
    }
