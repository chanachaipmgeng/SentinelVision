"""D2 dedicated kiosk device API (CRUD, heartbeat, remote revoke/rotate)."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.database import get_db
from ..security.deps import assert_request_company_access, assert_request_permission
from ..services import device_service

router = APIRouter()


@router.get("/company/{companyId}/devices")
async def list_devices(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, "devices.manage", companyId)
    return await device_service.list_devices(db, companyId)


@router.post("/company/{companyId}/devices")
async def create_device(
    companyId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, "devices.manage", companyId)
    return await device_service.create_device(db, companyId, body or {})


@router.get("/company/{companyId}/devices/{deviceId}")
async def get_device(
    companyId: UUID,
    deviceId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, "devices.manage", companyId)
    device = await device_service.get_company_device(db, companyId, deviceId)
    return device_service.serialize_device(device)


@router.patch("/company/{companyId}/devices/{deviceId}")
async def update_device(
    companyId: UUID,
    deviceId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, "devices.manage", companyId)
    return await device_service.update_device(db, companyId, deviceId, body or {})


@router.post("/company/{companyId}/devices/{deviceId}/pairing-code")
async def reissue_pairing_code(
    companyId: UUID,
    deviceId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, "devices.manage", companyId)
    return await device_service.reissue_pairing_code(db, companyId, deviceId)


@router.post("/company/{companyId}/devices/{deviceId}/rotate")
async def rotate_device(
    companyId: UUID,
    deviceId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Alias for remote token rotate / re-pair."""
    await assert_request_permission(request, db, "devices.manage", companyId)
    return await device_service.reissue_pairing_code(db, companyId, deviceId)


@router.delete("/company/{companyId}/devices/{deviceId}")
async def revoke_device(
    companyId: UUID,
    deviceId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, "devices.manage", companyId)
    return await device_service.revoke_device(db, companyId, deviceId)


@router.post("/company/{companyId}/devices/{deviceId}/heartbeat")
async def device_heartbeat(
    companyId: UUID,
    deviceId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """HTTP heartbeat (kiosk JWT or company admin). WS also accepts type=heartbeat."""
    await assert_request_company_access(request, db, companyId)
    # Kiosk tokens may only heartbeat their own device.
    kiosk_device_id = getattr(request.state, "kiosk_device_id", None)
    if kiosk_device_id is not None and kiosk_device_id != deviceId:
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Kiosk may only heartbeat its own device")
    return await device_service.record_heartbeat(db, companyId, deviceId, body or {})
