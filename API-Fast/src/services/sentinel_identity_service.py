"""SentinelVision identity / zone / event helpers (serializers, schedule, expiry)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.sentinel import SentinelAccessZone, SentinelEvent, SentinelIdentity
from ..services.company_module_service import VALID_STATION_MODES as MODULE_STATION_MODES

VALID_IDENTITY_TYPES = {"BLACKLIST", "POI", "VIP", "VISITOR", "EVENT_ATTENDEE"}
VALID_SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
VALID_STATION_MODES = set(MODULE_STATION_MODES)


def bangkok_tz():
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo("Asia/Bangkok")
    except Exception:
        return timezone(timedelta(hours=7))


def parse_iso_dt(raw: Optional[str]) -> Optional[datetime]:
    if not raw or not str(raw).strip():
        return None
    val = str(raw).strip()
    try:
        if val.endswith("Z"):
            val = val[:-1] + "+00:00"
        dt = datetime.fromisoformat(val)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=bangkok_tz())
        return dt
    except Exception:
        return None


def is_within_schedule(start_hhmm: str, end_hhmm: str, now_local: datetime) -> bool:
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


def serialize_identity(item: SentinelIdentity) -> dict:
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


def serialize_zone(zone: SentinelAccessZone) -> dict:
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


def serialize_event(ev: SentinelEvent, attendee_count: int = 0, checked_in_count: int = 0) -> dict:
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


async def expire_sentinel_identities_tick() -> dict:
    """
    PDPA Automated Biometric Expiry Sweeper:
    Finds active SentinelIdentity rows whose ``expiresAt < now()``, marks them ``EXPIRED``,
    and purges their 512-d ``embedding`` vector from pgvector.
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


async def get_active_identity(
    db: AsyncSession, company_id: UUID, identity_id: UUID
) -> Optional[SentinelIdentity]:
    ident = await db.get(SentinelIdentity, identity_id)
    if not ident or ident.companyId != company_id or ident.deletedAt is not None:
        return None
    return ident
