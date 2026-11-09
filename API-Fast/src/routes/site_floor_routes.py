"""Phase 2 site floor + E-Map pin API."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.database import get_db
from ..security.deps import assert_request_company_access
from ..services import site_floor_service

router = APIRouter()


@router.get("/company/{companyId}/floors")
async def list_floors(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await site_floor_service.list_floors(db, companyId)


@router.post("/company/{companyId}/floors")
async def create_floor(
    companyId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await site_floor_service.create_floor(db, companyId, body or {})


@router.get("/company/{companyId}/floors/{floorId}")
async def get_floor(
    companyId: UUID,
    floorId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    floor = await site_floor_service.get_company_floor(db, companyId, floorId)
    return site_floor_service.serialize_floor(floor)


@router.patch("/company/{companyId}/floors/{floorId}")
async def update_floor(
    companyId: UUID,
    floorId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await site_floor_service.update_floor(db, companyId, floorId, body or {})


@router.delete("/company/{companyId}/floors/{floorId}")
async def delete_floor(
    companyId: UUID,
    floorId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await site_floor_service.delete_floor(db, companyId, floorId)


@router.post("/company/{companyId}/floors/{floorId}/plan-image")
async def upload_plan_image(
    companyId: UUID,
    floorId: UUID,
    request: Request,
    file: UploadFile = File(...),
    widthPx: Optional[int] = Form(None),
    heightPx: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await site_floor_service.upload_plan_image(
        db, companyId, floorId, file, width_px=widthPx, height_px=heightPx
    )


@router.get("/company/{companyId}/floors/{floorId}/emap")
async def get_emap(
    companyId: UUID,
    floorId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await site_floor_service.get_emap_payload(db, companyId, floorId)


@router.patch("/company/{companyId}/pins/camera/{cameraId}")
async def update_camera_pin(
    companyId: UUID,
    cameraId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await site_floor_service.update_camera_pin(db, companyId, cameraId, body or {})


@router.patch("/company/{companyId}/pins/zone/{zoneId}")
async def update_zone_pin(
    companyId: UUID,
    zoneId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await site_floor_service.update_zone_pin(db, companyId, zoneId, body or {})


@router.patch("/company/{companyId}/pins/kiosk/{deviceId}")
async def update_kiosk_pin(
    companyId: UUID,
    deviceId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await site_floor_service.update_kiosk_pin(db, companyId, deviceId, body or {})
