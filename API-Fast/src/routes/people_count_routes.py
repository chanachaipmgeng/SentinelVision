"""Phase 6D people-count buckets, camera ai_config, and camera CSV import."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.database import get_db
from ..security.deps import assert_request_permission
from ..services import people_count_service
from ..services.analytics_service import resolve_range

router = APIRouter()


@router.get("/company/{companyId}/buckets")
async def list_people_buckets(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    cameraId: Optional[UUID] = Query(default=None),
    start: Optional[str] = Query(default=None),
    end: Optional[str] = Query(default=None),
    limit: int = Query(default=500, ge=1, le=5000),
):
    await assert_request_permission(request, db, "cameras.read", companyId)
    start_dt, end_dt = resolve_range(start, end)
    return await people_count_service.list_buckets(
        db,
        companyId,
        camera_id=cameraId,
        start=start_dt,
        end=end_dt,
        limit=limit,
    )


@router.get("/company/{companyId}/metrics")
async def people_metrics(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    start: Optional[str] = Query(default=None),
    end: Optional[str] = Query(default=None),
):
    await assert_request_permission(request, db, "cameras.read", companyId)
    start_dt, end_dt = resolve_range(start, end)
    return await people_count_service.people_metrics_summary(
        db, companyId, start=start_dt, end=end_dt
    )


@router.put("/company/{companyId}/cameras/{cameraId}/ai-config")
async def put_camera_ai_config(
    companyId: UUID,
    cameraId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, "cameras.manage", companyId)
    return await people_count_service.update_camera_ai_config(
        db, companyId, cameraId, body or {}
    )


@router.get("/company/{companyId}/cameras/{cameraId}/ai-config")
async def get_camera_ai_config(
    companyId: UUID,
    cameraId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, "cameras.read", companyId)
    from ..services.camera_service import get_company_camera, serialize_camera
    from ..services.people_analytics import normalize_ai_config

    cam = await get_company_camera(db, companyId, cameraId)
    cfg = normalize_ai_config(cam.aiConfig if isinstance(cam.aiConfig, dict) else None)
    return {"cameraId": str(cam.cameraId), "aiConfig": cfg, "camera": serialize_camera(cam)}


@router.post("/company/{companyId}/cameras/import-csv")
async def import_cameras_csv(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
):
    await assert_request_permission(request, db, "cameras.manage", companyId)
    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    return await people_count_service.import_cameras_csv(db, companyId, text)
