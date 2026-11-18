"""Phase 3 CCTV camera API (CRUD, ping, snapshot)."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.database import get_db
from ..security.deps import assert_request_permission
from ..services import camera_service

router = APIRouter()


@router.get("/company/{companyId}/cameras")
async def list_cameras(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, "cameras.read", companyId)
    return await camera_service.list_cameras(db, companyId)


@router.post("/company/{companyId}/cameras")
async def create_camera(
    companyId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, "cameras.manage", companyId)
    return await camera_service.create_camera(db, companyId, body or {})


@router.get("/company/{companyId}/cameras/{cameraId}")
async def get_camera(
    companyId: UUID,
    cameraId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, "cameras.read", companyId)
    cam = await camera_service.get_company_camera(db, companyId, cameraId)
    return camera_service.serialize_camera(cam)


@router.patch("/company/{companyId}/cameras/{cameraId}")
async def update_camera(
    companyId: UUID,
    cameraId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, "cameras.manage", companyId)
    return await camera_service.update_camera(db, companyId, cameraId, body or {})


@router.delete("/company/{companyId}/cameras/{cameraId}")
async def delete_camera(
    companyId: UUID,
    cameraId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, "cameras.manage", companyId)
    return await camera_service.delete_camera(db, companyId, cameraId)


@router.get("/company/{companyId}/cameras/{cameraId}/ping")
async def ping_camera(
    companyId: UUID,
    cameraId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, "cameras.read", companyId)
    return await camera_service.ping_camera(db, companyId, cameraId)


@router.post("/company/{companyId}/cameras/{cameraId}/snapshot")
async def snapshot_camera(
    companyId: UUID,
    cameraId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, "cameras.read", companyId)
    return await camera_service.snapshot_camera(db, companyId, cameraId)


@router.post("/company/{companyId}/cameras/discover-onvif")
async def discover_onvif_cameras(
    companyId: UUID,
    request: Request,
    body: dict | None = None,
    db: AsyncSession = Depends(get_db),
):
    from ..services.onvif_service import discover_onvif_devices

    await assert_request_permission(request, db, "cameras.manage", companyId)
    timeout_s = float((body or {}).get("timeoutSeconds") or 2.0)
    devices = await discover_onvif_devices(timeout_seconds=timeout_s)
    return {"devices": devices, "count": len(devices)}


@router.post("/company/{companyId}/cameras/{cameraId}/ptz")
async def control_camera_ptz(
    companyId: UUID,
    cameraId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    from ..services.onvif_service import send_ptz_command

    await assert_request_permission(request, db, "cameras.manage", companyId)
    cam = await camera_service.get_company_camera(db, companyId, cameraId)
    payload = body or {}
    raw_action = str(payload.get("action") or "move").strip()
    upper_action = raw_action.upper()
    speed_raw = payload.get("speed")
    speed = float(speed_raw) if isinstance(speed_raw, (int, float, str)) and str(speed_raw).strip() else 0.5
    pan = float(payload.get("pan") or 0.0)
    tilt = float(payload.get("tilt") or 0.0)
    zoom = float(payload.get("zoom") or 0.0)
    norm_action = raw_action.lower()
    if upper_action == "STOP":
        norm_action = "stop"
    elif upper_action == "UP" and tilt == 0.0:
        norm_action = "move"
        tilt = speed
    elif upper_action == "DOWN" and tilt == 0.0:
        norm_action = "move"
        tilt = -speed
    elif upper_action == "LEFT" and pan == 0.0:
        norm_action = "move"
        pan = -speed
    elif upper_action == "RIGHT" and pan == 0.0:
        norm_action = "move"
        pan = speed
    elif upper_action == "ZOOM_IN" and zoom == 0.0:
        norm_action = "move"
        zoom = speed
    elif upper_action == "ZOOM_OUT" and zoom == 0.0:
        norm_action = "move"
        zoom = -speed
    return await send_ptz_command(
        cam,
        action=norm_action,
        profile_token=str(payload.get("profileToken") or "Profile_1"),
        pan=pan,
        tilt=tilt,
        zoom=zoom,
        onvif_url=payload.get("onvifUrl"),
    )


@router.put("/company/{companyId}/cameras/{cameraId}/privacy-masks")
async def update_camera_privacy_masks(
    companyId: UUID,
    cameraId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    from ..services.privacy_mask_service import validate_privacy_masks

    await assert_request_permission(request, db, "cameras.manage", companyId)
    cam = await camera_service.get_company_camera(db, companyId, cameraId)
    masks = validate_privacy_masks(list((body or {}).get("privacyMasks") or []))
    cfg = dict(cam.aiConfig or {})
    cfg["privacyMasks"] = masks
    cam.aiConfig = cfg
    await db.commit()
    await db.refresh(cam)
    return {"cameraId": str(cam.cameraId), "privacyMasks": masks, "count": len(masks)}
