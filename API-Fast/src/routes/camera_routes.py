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
