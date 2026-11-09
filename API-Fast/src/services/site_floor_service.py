"""Site floor CRUD, plan-image upload, and E-Map pin updates (Phase 2)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.settings import settings
from ..models.camera import Camera
from ..models.hr_schedule import KioskDevice
from ..models.sentinel import SentinelAccessZone
from ..models.site_floor import SiteFloor
from ..services.storage_service import (
    FLOOR_PLAN_PREFIX,
    delete_stored_image,
    store_image_bytes,
)

logger = logging.getLogger(__name__)

_ALLOWED_MAGIC = {b"\xff\xd8\xff": (".jpg", "image/jpeg"), b"\x89PNG": (".png", "image/png")}
_MAX_UPLOAD = int(getattr(settings, "UPLOAD_MAX_BYTES", None) or 10 * 1024 * 1024)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _clean_uuid(raw: Any, *, field: str) -> Optional[UUID]:
    if raw in (None, ""):
        return None
    try:
        return UUID(str(raw))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid UUID for {field}") from exc


def _clean_pos(raw: Any, *, field: str) -> Optional[float]:
    if raw in (None, ""):
        return None
    try:
        val = float(raw)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid number for {field}") from exc
    if val < 0 or val > 1:
        raise HTTPException(status_code=400, detail=f"{field} must be between 0 and 1")
    return val


def serialize_floor(floor: SiteFloor) -> dict[str, Any]:
    key = floor.planImageKey
    return {
        "siteFloorId": str(floor.siteFloorId),
        "companyId": str(floor.companyId),
        "name": floor.name,
        "buildingLabel": floor.buildingLabel,
        "floorLabel": floor.floorLabel,
        "planImageKey": key,
        "planImageUrl": f"/images/{key}" if key else None,
        "widthPx": floor.widthPx,
        "heightPx": floor.heightPx,
        "sortOrder": int(floor.sortOrder or 0),
        "createdAt": floor.createdAt,
        "updatedAt": floor.updatedAt,
    }


def _pin_fields(site_floor_id: Optional[UUID], map_x: Optional[float], map_y: Optional[float]) -> dict:
    return {
        "siteFloorId": str(site_floor_id) if site_floor_id else None,
        "mapPosX": map_x,
        "mapPosY": map_y,
    }


async def get_company_floor(db: AsyncSession, company_id: UUID, floor_id: UUID) -> SiteFloor:
    floor = await db.get(SiteFloor, floor_id)
    if not floor or floor.companyId != company_id or floor.deletedAt is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site floor not found")
    return floor


async def list_floors(db: AsyncSession, company_id: UUID) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(SiteFloor)
            .where(SiteFloor.companyId == company_id, SiteFloor.deletedAt.is_(None))
            .order_by(SiteFloor.sortOrder.asc(), SiteFloor.createdAt.asc())
        )
    ).scalars().all()
    return [serialize_floor(r) for r in rows]


async def create_floor(db: AsyncSession, company_id: UUID, body: dict[str, Any]) -> dict[str, Any]:
    name = str(body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    sort_order = body.get("sortOrder")
    try:
        sort_val = int(sort_order) if sort_order is not None else 0
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="sortOrder must be an integer") from exc

    floor = SiteFloor(
        siteFloorId=uuid4(),
        companyId=company_id,
        name=name[:160],
        buildingLabel=(str(body.get("buildingLabel") or "").strip() or None),
        floorLabel=(str(body.get("floorLabel") or "").strip() or None),
        sortOrder=sort_val,
        widthPx=_optional_int(body.get("widthPx"), field="widthPx"),
        heightPx=_optional_int(body.get("heightPx"), field="heightPx"),
    )
    db.add(floor)
    await db.commit()
    await db.refresh(floor)
    return serialize_floor(floor)


def _optional_int(raw: Any, *, field: str) -> Optional[int]:
    if raw in (None, ""):
        return None
    try:
        val = int(raw)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"{field} must be an integer") from exc
    if val <= 0:
        raise HTTPException(status_code=400, detail=f"{field} must be positive")
    return val


async def update_floor(
    db: AsyncSession, company_id: UUID, floor_id: UUID, body: dict[str, Any]
) -> dict[str, Any]:
    floor = await get_company_floor(db, company_id, floor_id)
    if "name" in body:
        name = str(body.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="name is required")
        floor.name = name[:160]
    if "buildingLabel" in body:
        floor.buildingLabel = str(body.get("buildingLabel") or "").strip() or None
    if "floorLabel" in body:
        floor.floorLabel = str(body.get("floorLabel") or "").strip() or None
    if "sortOrder" in body:
        try:
            floor.sortOrder = int(body.get("sortOrder") or 0)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="sortOrder must be an integer") from exc
    if "widthPx" in body:
        floor.widthPx = _optional_int(body.get("widthPx"), field="widthPx")
    if "heightPx" in body:
        floor.heightPx = _optional_int(body.get("heightPx"), field="heightPx")
    await db.commit()
    await db.refresh(floor)
    return serialize_floor(floor)


async def delete_floor(db: AsyncSession, company_id: UUID, floor_id: UUID) -> dict[str, Any]:
    floor = await get_company_floor(db, company_id, floor_id)
    floor.deletedAt = _now()
    key = floor.planImageKey
    floor.planImageKey = None
    await db.commit()
    if key:
        try:
            delete_stored_image("uploaded_images", key)
        except Exception as exc:
            logger.warning("Failed to delete floor plan image %s: %s", key, exc)
    return {"deleted": True, "siteFloorId": str(floor_id)}


async def upload_plan_image(
    db: AsyncSession,
    company_id: UUID,
    floor_id: UUID,
    file: UploadFile,
    *,
    width_px: Optional[int] = None,
    height_px: Optional[int] = None,
) -> dict[str, Any]:
    floor = await get_company_floor(db, company_id, floor_id)
    content = await file.read()
    if len(content) < 8 or len(content) > _MAX_UPLOAD:
        raise HTTPException(status_code=400, detail="Invalid image size")
    ext = None
    mime = "image/jpeg"
    for magic, (suffix, content_type) in _ALLOWED_MAGIC.items():
        if content.startswith(magic):
            ext = suffix
            mime = content_type
            break
    if not ext:
        raise HTTPException(status_code=400, detail="Only JPEG and PNG image files are allowed")

    new_key = f"{FLOOR_PLAN_PREFIX}{uuid4()}{ext}"
    store_image_bytes("uploaded_images", new_key, content, content_type=mime)
    old_key = floor.planImageKey
    floor.planImageKey = new_key
    if width_px is not None:
        floor.widthPx = _optional_int(width_px, field="widthPx")
    if height_px is not None:
        floor.heightPx = _optional_int(height_px, field="heightPx")
    await db.commit()
    await db.refresh(floor)
    if old_key and old_key != new_key:
        try:
            delete_stored_image("uploaded_images", old_key)
        except Exception as exc:
            logger.warning("Failed to delete previous floor plan %s: %s", old_key, exc)
    return serialize_floor(floor)


async def get_emap_payload(db: AsyncSession, company_id: UUID, floor_id: UUID) -> dict[str, Any]:
    floor = await get_company_floor(db, company_id, floor_id)

    cameras = (
        await db.execute(
            select(Camera).where(Camera.companyId == company_id, Camera.deletedAt.is_(None))
        )
    ).scalars().all()
    zones = (
        await db.execute(
            select(SentinelAccessZone).where(
                SentinelAccessZone.companyId == company_id,
                SentinelAccessZone.deletedAt.is_(None),
            )
        )
    ).scalars().all()
    devices = (
        await db.execute(
            select(KioskDevice).where(
                KioskDevice.companyId == company_id,
                KioskDevice.revokedAt.is_(None),
            )
        )
    ).scalars().all()

    def _cam(c: Camera) -> dict[str, Any]:
        return {
            "kind": "camera",
            "id": str(c.cameraId),
            "name": c.name,
            **_pin_fields(c.siteFloorId, c.mapPosX, c.mapPosY),
        }

    def _zone(z: SentinelAccessZone) -> dict[str, Any]:
        return {
            "kind": "zone",
            "id": str(z.zoneId),
            "name": z.name,
            **_pin_fields(z.siteFloorId, z.mapPosX, z.mapPosY),
        }

    def _kiosk(d: KioskDevice) -> dict[str, Any]:
        return {
            "kind": "kiosk",
            "id": str(d.deviceId),
            "name": d.name,
            **_pin_fields(d.siteFloorId, d.mapPosX, d.mapPosY),
        }

    on_floor_cams = [_cam(c) for c in cameras if c.siteFloorId == floor_id]
    on_floor_zones = [_zone(z) for z in zones if z.siteFloorId == floor_id]
    on_floor_kiosks = [_kiosk(d) for d in devices if d.siteFloorId == floor_id]
    unassigned = {
        "cameras": [_cam(c) for c in cameras if c.siteFloorId is None],
        "zones": [_zone(z) for z in zones if z.siteFloorId is None],
        "kiosks": [_kiosk(d) for d in devices if d.siteFloorId is None],
    }
    return {
        "floor": serialize_floor(floor),
        "pins": {
            "cameras": on_floor_cams,
            "zones": on_floor_zones,
            "kiosks": on_floor_kiosks,
        },
        "unassigned": unassigned,
    }


async def update_camera_pin(
    db: AsyncSession, company_id: UUID, camera_id: UUID, body: dict[str, Any]
) -> dict[str, Any]:
    cam = await db.get(Camera, camera_id)
    if not cam or cam.companyId != company_id or cam.deletedAt is not None:
        raise HTTPException(status_code=404, detail="Camera not found")
    await _apply_pin(db, company_id, body, set_floor=lambda v: setattr(cam, "siteFloorId", v),
                     set_x=lambda v: setattr(cam, "mapPosX", v), set_y=lambda v: setattr(cam, "mapPosY", v))
    await db.commit()
    await db.refresh(cam)
    return {
        "kind": "camera",
        "id": str(cam.cameraId),
        "name": cam.name,
        **_pin_fields(cam.siteFloorId, cam.mapPosX, cam.mapPosY),
    }


async def update_zone_pin(
    db: AsyncSession, company_id: UUID, zone_id: UUID, body: dict[str, Any]
) -> dict[str, Any]:
    zone = await db.get(SentinelAccessZone, zone_id)
    if not zone or zone.companyId != company_id or zone.deletedAt is not None:
        raise HTTPException(status_code=404, detail="Access zone not found")
    await _apply_pin(db, company_id, body, set_floor=lambda v: setattr(zone, "siteFloorId", v),
                     set_x=lambda v: setattr(zone, "mapPosX", v), set_y=lambda v: setattr(zone, "mapPosY", v))
    await db.commit()
    await db.refresh(zone)
    return {
        "kind": "zone",
        "id": str(zone.zoneId),
        "name": zone.name,
        **_pin_fields(zone.siteFloorId, zone.mapPosX, zone.mapPosY),
    }


async def update_kiosk_pin(
    db: AsyncSession, company_id: UUID, device_id: UUID, body: dict[str, Any]
) -> dict[str, Any]:
    device = await db.get(KioskDevice, device_id)
    if not device or device.companyId != company_id:
        raise HTTPException(status_code=404, detail="Kiosk device not found")
    if device.revokedAt is not None:
        raise HTTPException(status_code=409, detail="Kiosk device is revoked")
    await _apply_pin(
        db,
        company_id,
        body,
        set_floor=lambda v: setattr(device, "siteFloorId", v),
        set_x=lambda v: setattr(device, "mapPosX", v),
        set_y=lambda v: setattr(device, "mapPosY", v),
    )
    await db.commit()
    await db.refresh(device)
    return {
        "kind": "kiosk",
        "id": str(device.deviceId),
        "name": device.name,
        **_pin_fields(device.siteFloorId, device.mapPosX, device.mapPosY),
    }


async def _apply_pin(
    db: AsyncSession,
    company_id: UUID,
    body: dict[str, Any],
    *,
    set_floor,
    set_x,
    set_y,
) -> None:
    if "siteFloorId" in body:
        floor_id = _clean_uuid(body.get("siteFloorId"), field="siteFloorId")
        if floor_id is not None:
            await get_company_floor(db, company_id, floor_id)
        set_floor(floor_id)
    if "mapPosX" in body:
        set_x(_clean_pos(body.get("mapPosX"), field="mapPosX"))
    if "mapPosY" in body:
        set_y(_clean_pos(body.get("mapPosY"), field="mapPosY"))
