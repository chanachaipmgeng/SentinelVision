"""D2 kiosk device management: CRUD, pairing rotate, revoke, heartbeat, stationMode binding."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.settings import settings
from ..models.hr_schedule import KioskDevice
from ..security.kiosk_pairing import generate_pairing_code, hash_pairing_code, pairing_code_expiry
from ..services import token_revocation_service as revocation
from ..services.company_module_service import VALID_STATION_MODES
from ..services.tenant_quota_service import assert_device_quota, assert_tenant_active
from ..security.jwt import kiosk_refresh_ttl


def serialize_device(r: KioskDevice) -> dict:
    now = datetime.now(timezone.utc)
    pairing_exp = r.pairingExpiresAt
    if pairing_exp is not None and pairing_exp.tzinfo is None:
        pairing_exp = pairing_exp.replace(tzinfo=timezone.utc)
    return {
        "deviceId": str(r.deviceId),
        "companyId": str(r.companyId),
        "locationId": str(r.locationId) if r.locationId else None,
        "locationLabel": r.locationLabel,
        "name": r.name,
        "fingerprint": r.fingerprint,
        "appVersion": r.appVersion,
        "heartbeatAt": r.heartbeatAt,
        "config": r.config or {},
        "stationMode": r.stationMode,
        "zoneId": str(r.zoneId) if r.zoneId else None,
        "siteFloorId": str(r.siteFloorId) if r.siteFloorId else None,
        "mapPosX": r.mapPosX,
        "mapPosY": r.mapPosY,
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


async def _revoke_device_tokens(db: AsyncSession, device: KioskDevice, *, reason: str) -> None:
    if device.tokenFamily:
        await revocation.revoke_family(
            db, device.tokenFamily, datetime.now(timezone.utc) + kiosk_refresh_ttl(), reason=reason
        )
    device.tokenHash = None
    device.tokenFamily = None


async def get_company_device(db: AsyncSession, company_id: UUID, device_id: UUID) -> KioskDevice:
    device = await db.get(KioskDevice, device_id)
    if not device or device.companyId != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kiosk device not found")
    return device


def _clean_station_mode(raw: Any) -> Optional[str]:
    if raw in (None, ""):
        return None
    mode = str(raw).strip().upper()
    if mode not in VALID_STATION_MODES:
        raise HTTPException(
            status_code=400,
            detail=f"stationMode must be one of {', '.join(VALID_STATION_MODES)}",
        )
    return mode


def _clean_uuid(raw: Any, *, field: str) -> Optional[UUID]:
    if raw in (None, ""):
        return None
    try:
        return UUID(str(raw))
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid UUID for {field}")


def _clean_config(raw: Any) -> dict:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise HTTPException(status_code=400, detail="config must be an object")
    return raw


async def list_devices(db: AsyncSession, company_id: UUID) -> list[dict]:
    rows = (
        await db.execute(
            select(KioskDevice)
            .where(KioskDevice.companyId == company_id)
            .order_by(KioskDevice.createdAt.desc())
        )
    ).scalars().all()
    return [serialize_device(r) for r in rows]


async def create_device(db: AsyncSession, company_id: UUID, body: dict) -> dict:
    company = await assert_tenant_active(db, company_id)
    await assert_device_quota(db, company)

    name = str(body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Device name is required")

    map_x = body.get("mapPosX")
    map_y = body.get("mapPosY")
    device = KioskDevice(
        deviceId=uuid4(),
        companyId=company_id,
        locationId=_clean_uuid(body.get("locationId"), field="locationId"),
        locationLabel=(str(body.get("locationLabel") or body.get("location") or "").strip() or None),
        name=name,
        fingerprint=(str(body.get("fingerprint") or "").strip() or None),
        appVersion=(str(body.get("appVersion") or "").strip() or None),
        config=_clean_config(body.get("config")),
        stationMode=_clean_station_mode(body.get("stationMode")),
        zoneId=_clean_uuid(body.get("zoneId"), field="zoneId"),
        siteFloorId=_clean_uuid(body.get("siteFloorId"), field="siteFloorId"),
        mapPosX=None if map_x in (None, "") else float(map_x),
        mapPosY=None if map_y in (None, "") else float(map_y),
    )
    code = _issue_pairing_code(device)
    db.add(device)
    await db.commit()
    await db.refresh(device)
    return {
        **serialize_device(device),
        "pairingCode": code,
        "pairingCodeTtlMinutes": int(settings.KIOSK_PAIRING_CODE_TTL_MINUTES),
        "pairUrl": "/kiosk/pair",
    }


async def update_device(db: AsyncSession, company_id: UUID, device_id: UUID, body: dict) -> dict:
    await assert_tenant_active(db, company_id)
    device = await get_company_device(db, company_id, device_id)
    if device.revokedAt is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Kiosk device is revoked")

    if "name" in body:
        name = str(body.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="Device name is required")
        device.name = name
    if "locationId" in body:
        device.locationId = _clean_uuid(body.get("locationId"), field="locationId")
    if "locationLabel" in body or "location" in body:
        device.locationLabel = (
            str(body.get("locationLabel") if "locationLabel" in body else body.get("location") or "").strip() or None
        )
    if "fingerprint" in body:
        device.fingerprint = str(body.get("fingerprint") or "").strip() or None
    if "appVersion" in body:
        device.appVersion = str(body.get("appVersion") or "").strip() or None
    if "config" in body:
        device.config = _clean_config(body.get("config"))
    if "stationMode" in body:
        device.stationMode = _clean_station_mode(body.get("stationMode"))
    if "zoneId" in body:
        device.zoneId = _clean_uuid(body.get("zoneId"), field="zoneId")
    if "siteFloorId" in body:
        device.siteFloorId = _clean_uuid(body.get("siteFloorId"), field="siteFloorId")
    if "mapPosX" in body:
        device.mapPosX = None if body.get("mapPosX") in (None, "") else float(body["mapPosX"])
    if "mapPosY" in body:
        device.mapPosY = None if body.get("mapPosY") in (None, "") else float(body["mapPosY"])

    await db.commit()
    await db.refresh(device)
    return serialize_device(device)


async def reissue_pairing_code(db: AsyncSession, company_id: UUID, device_id: UUID) -> dict:
    """Remote rotate: invalidate current token family and issue a fresh one-time pairing code."""
    await assert_tenant_active(db, company_id)
    device = await get_company_device(db, company_id, device_id)
    if device.revokedAt is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Kiosk device is revoked; register a new device",
        )
    await _revoke_device_tokens(db, device, reason=revocation.REASON_REPAIR)
    code = _issue_pairing_code(device)
    await db.commit()
    await db.refresh(device)
    return {
        **serialize_device(device),
        "pairingCode": code,
        "pairingCodeTtlMinutes": int(settings.KIOSK_PAIRING_CODE_TTL_MINUTES),
        "pairUrl": "/kiosk/pair",
    }


async def revoke_device(db: AsyncSession, company_id: UUID, device_id: UUID) -> dict:
    device = await get_company_device(db, company_id, device_id)
    await _revoke_device_tokens(db, device, reason=revocation.REASON_DEVICE_REVOKED)
    device.pairingCodeHash = None
    device.pairingExpiresAt = None
    device.revokedAt = datetime.now(timezone.utc)
    await db.commit()
    return {
        "deviceId": str(device_id),
        "revokedAt": device.revokedAt,
        "isActive": False,
    }


async def record_heartbeat(
    db: AsyncSession,
    company_id: UUID,
    device_id: UUID,
    body: Optional[dict] = None,
) -> dict:
    """Update heartbeat / lastSeen and optional fingerprint/appVersion/config from kiosk."""
    device = await get_company_device(db, company_id, device_id)
    if device.revokedAt is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Kiosk device token has been revoked")
    body = body or {}
    now = datetime.now(timezone.utc)
    device.heartbeatAt = now
    device.lastSeenAt = now
    if body.get("fingerprint"):
        device.fingerprint = str(body["fingerprint"]).strip()[:255] or device.fingerprint
    if body.get("appVersion"):
        device.appVersion = str(body["appVersion"]).strip()[:64] or device.appVersion
    if isinstance(body.get("config"), dict):
        merged = dict(device.config or {})
        merged.update(body["config"])
        device.config = merged
    await db.commit()
    await db.refresh(device)
    return serialize_device(device)
