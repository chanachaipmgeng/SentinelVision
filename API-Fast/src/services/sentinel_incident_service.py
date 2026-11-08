"""SentinelVision incident lifecycle, dedupe, scan decision engine, kiosk match."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from typing import Callable, List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.settings import settings
from ..models.member import Member
from ..models.sentinel import SentinelAccessZone, SentinelEvent, SentinelIdentity, SentinelIncidentLog
from ..services.face_match_service import (
    search_face_pgvector,
    search_sentinel_identity_pgvector,
)
from ..services.notification_service import NotificationOutbox
from ..services.sentinel_identity_service import (
    bangkok_tz,
    is_within_schedule,
    serialize_zone,
)
from ..services.sentinel_relay_service import dispatch_relay_webhook
from ..services.siem_export_service import queue_siem_incident_export
from ..services.storage_service import (
    EVIDENCE_KIND_INCIDENT_SNAPSHOT,
    store_evidence_image,
)

logger = logging.getLogger("dpu.sentinel")

STATUS_OPEN = "OPEN"
STATUS_ACKNOWLEDGED = "ACKNOWLEDGED"
STATUS_ASSIGNED = "ASSIGNED"
STATUS_CLOSED = "CLOSED"
VALID_INCIDENT_STATUSES = {STATUS_OPEN, STATUS_ACKNOWLEDGED, STATUS_ASSIGNED, STATUS_CLOSED}
OPEN_LIFECYCLE_STATUSES = (STATUS_OPEN, STATUS_ACKNOWLEDGED, STATUS_ASSIGNED)

DEFAULT_DEDUPE_WINDOW_SECONDS = 300


def dedupe_window_seconds() -> int:
    return int(
        getattr(settings, "SENTINEL_INCIDENT_DEDUPE_SECONDS", DEFAULT_DEDUPE_WINDOW_SECONDS)
        or DEFAULT_DEDUPE_WINDOW_SECONDS
    )


def build_dedupe_key(
    company_id: UUID,
    identity_id: Optional[UUID],
    event_type: str,
    zone_id: Optional[UUID],
    *,
    member_id: Optional[UUID] = None,
) -> str:
    """Stable key for open-incident dedupe: company + subject + eventType + zone."""
    subject = identity_id or member_id or ""
    return f"{company_id}|{subject}|{str(event_type or '').upper()}|{zone_id or ''}"


def serialize_incident(inc: SentinelIncidentLog) -> dict:
    return {
        "incidentId": str(inc.incidentId),
        "companyId": str(inc.companyId),
        "eventType": inc.eventType,
        "severity": inc.severity,
        "status": getattr(inc, "status", None) or STATUS_OPEN,
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
        "assignedTo": str(inc.assignedTo) if getattr(inc, "assignedTo", None) else None,
        "assignedAt": getattr(inc, "assignedAt", None),
        "closedBy": str(inc.closedBy) if getattr(inc, "closedBy", None) else None,
        "closedAt": getattr(inc, "closedAt", None),
        "dedupeKey": getattr(inc, "dedupeKey", None),
        "occurredAt": inc.occurredAt,
    }


async def find_open_dedupe_match(
    db: AsyncSession,
    *,
    company_id: UUID,
    dedupe_key: str,
    now: Optional[datetime] = None,
    window_seconds: Optional[int] = None,
) -> Optional[SentinelIncidentLog]:
    now = now or datetime.now(timezone.utc)
    window = timedelta(seconds=window_seconds if window_seconds is not None else dedupe_window_seconds())
    since = now - window
    stmt = (
        select(SentinelIncidentLog)
        .where(
            SentinelIncidentLog.companyId == company_id,
            SentinelIncidentLog.dedupeKey == dedupe_key,
            SentinelIncidentLog.status.in_(OPEN_LIFECYCLE_STATUSES),
            SentinelIncidentLog.occurredAt >= since,
        )
        .order_by(SentinelIncidentLog.occurredAt.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def record_incident(
    db: AsyncSession,
    *,
    company_id: UUID,
    event_type: str,
    severity: str = "INFO",
    identity_id: Optional[UUID] = None,
    member_id: Optional[UUID] = None,
    subject_name: Optional[str] = None,
    identity_type: Optional[str] = None,
    zone_id: Optional[UUID] = None,
    zone_name: Optional[str] = None,
    event_id: Optional[UUID] = None,
    confidence_percent: Optional[float] = None,
    distance: Optional[float] = None,
    snapshot_url: Optional[str] = None,
    action_taken: Optional[str] = None,
    outbox_factory: Optional[Callable[[], Optional[NotificationOutbox]]] = None,
    commit: bool = True,
) -> tuple[SentinelIncidentLog, bool]:
    """
    Insert a new incident, or refresh an open duplicate within the dedupe window.

    Returns ``(incident, created_new)``. When ``created_new`` is False, outbox is skipped.
    """
    now = datetime.now(timezone.utc)
    key = build_dedupe_key(
        company_id, identity_id, event_type, zone_id, member_id=member_id
    )
    existing = await find_open_dedupe_match(db, company_id=company_id, dedupe_key=key, now=now)
    if existing is not None:
        existing.occurredAt = now
        if confidence_percent is not None:
            existing.confidencePercent = confidence_percent
        if distance is not None:
            existing.distance = distance
        if snapshot_url:
            existing.snapshotUrl = snapshot_url
        if action_taken:
            existing.actionTaken = action_taken
        if subject_name:
            existing.subjectName = subject_name
        if commit:
            await db.commit()
            await db.refresh(existing)
        return existing, False

    inc = SentinelIncidentLog(
        companyId=company_id,
        eventType=event_type,
        severity=severity,
        status=STATUS_OPEN,
        identityId=identity_id,
        memberId=member_id,
        subjectName=subject_name,
        identityType=identity_type,
        zoneId=zone_id,
        zoneName=zone_name,
        eventId=event_id,
        confidencePercent=confidence_percent,
        distance=distance,
        snapshotUrl=snapshot_url,
        actionTaken=action_taken,
        dedupeKey=key,
        occurredAt=now,
    )
    db.add(inc)
    if outbox_factory is not None:
        ob = outbox_factory()
        if ob is not None:
            db.add(ob)
    await queue_siem_incident_export(db, company_id, inc)
    if commit:
        await db.commit()
        await db.refresh(inc)
    return inc, True


async def acknowledge_incident(
    db: AsyncSession,
    company_id: UUID,
    incident_id: UUID,
    actor_id: Optional[UUID],
) -> SentinelIncidentLog:
    inc = await db.get(SentinelIncidentLog, incident_id)
    if not inc or inc.companyId != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    if (inc.status or STATUS_OPEN) == STATUS_CLOSED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Closed incidents cannot be acknowledged",
        )
    now = datetime.now(timezone.utc)
    inc.acknowledgedBy = actor_id
    inc.acknowledgedAt = now
    inc.status = STATUS_ACKNOWLEDGED
    await db.commit()
    await db.refresh(inc)
    return inc


async def assign_incident(
    db: AsyncSession,
    company_id: UUID,
    incident_id: UUID,
    *,
    actor_id: Optional[UUID],
    assignee_id: Optional[UUID] = None,
) -> SentinelIncidentLog:
    inc = await db.get(SentinelIncidentLog, incident_id)
    if not inc or inc.companyId != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    if (inc.status or STATUS_OPEN) == STATUS_CLOSED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Closed incidents cannot be assigned",
        )
    target = assignee_id or actor_id
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="assignee (or authenticated actor) is required",
        )
    now = datetime.now(timezone.utc)
    inc.assignedTo = target
    inc.assignedAt = now
    inc.status = STATUS_ASSIGNED
    await db.commit()
    await db.refresh(inc)
    return inc


async def close_incident(
    db: AsyncSession,
    company_id: UUID,
    incident_id: UUID,
    actor_id: Optional[UUID],
) -> SentinelIncidentLog:
    inc = await db.get(SentinelIncidentLog, incident_id)
    if not inc or inc.companyId != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    if (inc.status or STATUS_OPEN) == STATUS_CLOSED:
        return inc
    now = datetime.now(timezone.utc)
    inc.closedBy = actor_id
    inc.closedAt = now
    inc.status = STATUS_CLOSED
    await queue_siem_incident_export(
        db, company_id, inc, event="sentinel.incident.closed"
    )
    await db.commit()
    await db.refresh(inc)
    return inc


async def list_incidents(
    db: AsyncSession,
    company_id: UUID,
    *,
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    status_filter: Optional[str] = None,
    zone_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    stmt = select(SentinelIncidentLog).where(SentinelIncidentLog.companyId == company_id)
    if event_type:
        stmt = stmt.where(SentinelIncidentLog.eventType == event_type.strip().upper())
    if severity:
        stmt = stmt.where(SentinelIncidentLog.severity == severity.strip().upper())
    if status_filter:
        st = status_filter.strip().upper()
        if st in VALID_INCIDENT_STATUSES:
            stmt = stmt.where(SentinelIncidentLog.status == st)
    if zone_id and str(zone_id).strip():
        try:
            zid = UUID(str(zone_id).strip())
            stmt = stmt.where(SentinelIncidentLog.zoneId == zid)
        except (ValueError, TypeError):
            # Invalid UUID → empty result rather than 500
            return []
    stmt = stmt.order_by(SentinelIncidentLog.occurredAt.desc()).limit(limit).offset(offset)
    rows = (await db.execute(stmt)).scalars().all()
    return [serialize_incident(r) for r in rows]


async def dispatch_relay_webhook_async(
    webhook_url: str,
    secret: Optional[str],
    payload: dict,
) -> bool:
    """Thin wrapper → ``sentinel_relay_service.dispatch_relay_webhook`` (httpx + circuit)."""
    return await dispatch_relay_webhook(webhook_url, secret, payload)


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
    return await dispatch_relay_webhook_async(
        zone.relayWebhookUrl,
        zone.relaySecret,
        {
            "event": "door.access_granted",
            "subjectName": subject_name,
            "identityType": identity_type,
            "zoneCode": zone.code,
        },
    )


def store_incident_snapshot(filename: str, source_path) -> str:
    """Persist scan evidence under the ``incident_snapshot`` retention kind."""
    return store_evidence_image(
        EVIDENCE_KIND_INCIDENT_SNAPSHOT, filename, source_path, move=True
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
        inc, _ = await record_incident(
            db,
            company_id=company_id,
            event_type="ACCESS_DENIED",
            severity="WARNING",
            subject_name="Unknown Person",
            identity_type="UNKNOWN",
            zone_id=zone.zoneId if zone else None,
            zone_name=zone.name if zone else station_mode,
            snapshot_url=snapshot_url,
            action_taken="Face not registered in company database",
        )
        return {
            "matched": False,
            "accessGranted": False,
            "decision": "UNKNOWN_FACE",
            "stationMode": station_mode,
            "message": "ไม่พบข้อมูลใบหน้าในระบบ (ไม่อนุญาตให้ผ่าน)",
            "incident": serialize_incident(inc),
        }

    confidence_pct = round(max(0.0, min(1.0, 1.0 - float(best_distance))) * 100.0, 2)

    if chosen_kind == "SENTINEL" and matched_ident is not None:
        itype = matched_ident.identityType

        if itype in ("BLACKLIST", "POI"):
            def _blacklist_outbox() -> NotificationOutbox:
                return NotificationOutbox(
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

            inc, _ = await record_incident(
                db,
                company_id=company_id,
                event_type="BLACKLIST_ALERT",
                severity="CRITICAL" if itype == "BLACKLIST" else "WARNING",
                identity_id=matched_ident.identityId,
                subject_name=matched_ident.fullName,
                identity_type=itype,
                zone_id=zone.zoneId if zone else None,
                zone_name=zone.name if zone else station_mode,
                confidence_percent=confidence_pct,
                distance=round(float(best_distance), 6),
                snapshot_url=snapshot_url,
                action_taken=(
                    f"Silent Security Alert Dispatched "
                    f"({matched_ident.alertNote or 'Watchlist match'})"
                ),
                outbox_factory=_blacklist_outbox if silent_alarm else None,
            )
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
                "incident": serialize_incident(inc),
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
            inc, _ = await record_incident(
                db,
                company_id=company_id,
                event_type="EVENT_CHECKIN",
                severity="INFO",
                identity_id=matched_ident.identityId,
                subject_name=matched_ident.fullName,
                identity_type=itype,
                zone_id=zone.zoneId if zone else None,
                zone_name=zone.name if zone else (ev_obj.name if ev_obj else "Event Gate"),
                event_id=ev_obj.eventId if ev_obj else matched_ident.eventId,
                confidence_percent=confidence_pct,
                distance=round(float(best_distance), 6),
                snapshot_url=snapshot_url,
                action_taken=f"Checked in • Seat: {matched_ident.seatNumber or 'General'}",
            )
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
                "incident": serialize_incident(inc),
            }

        now_local = datetime.now(bangkok_tz())
        allowed = True
        deny_reason = ""
        if zone is not None:
            if itype not in (zone.allowedIdentityTypes or ["EMPLOYEE", "VIP", "VISITOR"]):
                allowed = False
                deny_reason = f"ประเภทตัวตน {itype} ไม่ได้รับสิทธิ์เข้าโซน {zone.name}"
            elif not is_within_schedule(zone.scheduleStart, zone.scheduleEnd, now_local):
                allowed = False
                deny_reason = (
                    f"อยู่นอกช่วงเวลาที่อนุญาตของโซน ({zone.scheduleStart}-{zone.scheduleEnd})"
                )
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
        inc, _ = await record_incident(
            db,
            company_id=company_id,
            event_type=event_type,
            severity="INFO" if allowed else "WARNING",
            identity_id=matched_ident.identityId,
            subject_name=matched_ident.fullName,
            identity_type=itype,
            zone_id=zone.zoneId if zone else None,
            zone_name=zone.name if zone else station_mode,
            confidence_percent=confidence_pct,
            distance=round(float(best_distance), 6),
            snapshot_url=snapshot_url,
            action_taken=(
                f"Access Granted ({itype})"
                + (" + Door Unlocked" if relay_ok else "")
                if allowed
                else deny_reason
            ),
        )
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
            "incident": serialize_incident(inc),
        }

    _, matched_member_id, _ = emp_match
    matched_member = await db.get(Member, matched_member_id)
    emp_name = (
        f"{matched_member.firstName or ''} {matched_member.lastName or ''}".strip()
        or matched_member.username
        if matched_member
        else "Employee"
    )

    now_local = datetime.now(bangkok_tz())
    allowed = True
    deny_reason = ""
    if zone is not None:
        if "EMPLOYEE" not in (zone.allowedIdentityTypes or ["EMPLOYEE"]):
            allowed = False
            deny_reason = f"โซน {zone.name} ไม่อนุญาตสำหรับพนักงานทั่วไป"
        elif not is_within_schedule(zone.scheduleStart, zone.scheduleEnd, now_local):
            allowed = False
            deny_reason = (
                f"อยู่นอกช่วงเวลาเปิดทำการของโซน ({zone.scheduleStart}-{zone.scheduleEnd})"
            )
        elif zone.require2FA and not (totp_or_pin and str(totp_or_pin).strip()):
            allowed = False
            deny_reason = "โซนความมั่นคงสูง: กรุณาระบุรหัส 2FA / PIN ร่วมกับการสแกนใบหน้า"

    relay_ok = False
    if allowed:
        relay_ok = await maybe_dispatch_zone_relay(
            zone, subject_name=emp_name, identity_type="EMPLOYEE"
        )

    inc, _ = await record_incident(
        db,
        company_id=company_id,
        event_type="ACCESS_GRANTED" if allowed else "ACCESS_DENIED",
        severity="INFO" if allowed else "WARNING",
        member_id=matched_member_id,
        subject_name=emp_name,
        identity_type="EMPLOYEE",
        zone_id=zone.zoneId if zone else None,
        zone_name=zone.name if zone else station_mode,
        confidence_percent=confidence_pct,
        distance=round(float(best_distance), 6),
        snapshot_url=snapshot_url,
        action_taken=(
            "Employee Verified & Access Granted"
            + (" + Door Unlocked" if relay_ok else "")
            if allowed
            else deny_reason
        ),
    )
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
        "incident": serialize_incident(inc),
    }


async def evaluate_kiosk_sentinel_match(
    db: AsyncSession,
    company_id: UUID,
    target_encoding: List[float],
    threshold: float,
) -> Optional[dict]:
    """
    Evaluates a live Kiosk face embedding against ``sentinel_identity``.
    Logs an incident and dispatches a silent webhook if ``BLACKLIST``/``POI`` is detected,
    or returns enriched ``sentinelMatch`` metadata for ``VIP``/``VISITOR``/``EVENT_ATTENDEE``.

    Stable import path for F3: also re-exported from ``routes.sentinel_routes``.
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
        else (
            "VIP_ARRIVAL"
            if itype == "VIP"
            else ("EVENT_CHECKIN" if itype == "EVENT_ATTENDEE" else "VISITOR_CHECKIN")
        )
    )
    severity = "CRITICAL" if itype == "BLACKLIST" else ("WARNING" if itype == "POI" else "INFO")
    action_taken = (
        f"Kiosk Silent Alert ({ident.alertNote or 'Watchlist match'})"
        if itype in ("BLACKLIST", "POI")
        else (f"Kiosk Seat: {ident.seatNumber}" if ident.seatNumber else f"Kiosk Verified ({itype})")
    )

    def _kiosk_blacklist_outbox() -> NotificationOutbox:
        return NotificationOutbox(
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

    await record_incident(
        db,
        company_id=company_id,
        event_type=event_type,
        severity=severity,
        identity_id=ident.identityId,
        subject_name=ident.fullName,
        identity_type=itype,
        zone_name="Live Face Kiosk",
        event_id=ident.eventId,
        confidence_percent=confidence_pct,
        distance=round(float(distance), 6),
        snapshot_url=ident.pictureUrl,
        action_taken=action_taken,
        outbox_factory=_kiosk_blacklist_outbox if itype in ("BLACKLIST", "POI") else None,
    )
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


# Re-export for callers that historically pulled zone serializer alongside scan helpers.
__all__ = [
    "STATUS_OPEN",
    "STATUS_ACKNOWLEDGED",
    "STATUS_ASSIGNED",
    "STATUS_CLOSED",
    "acknowledge_incident",
    "assign_incident",
    "build_dedupe_key",
    "close_incident",
    "dispatch_relay_webhook_async",
    "evaluate_kiosk_sentinel_match",
    "evaluate_unified_scan_decision",
    "list_incidents",
    "maybe_dispatch_zone_relay",
    "record_incident",
    "resolve_scan_zone",
    "serialize_incident",
    "serialize_zone",
    "store_incident_snapshot",
]
