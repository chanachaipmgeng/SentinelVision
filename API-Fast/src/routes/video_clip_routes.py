"""Phase 4B video clip list / get / download / export APIs."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.database import get_db
from ..security.deps import assert_request_permission
from ..services import video_clip_service

router = APIRouter()


@router.get("/company/{companyId}/clips")
async def list_clips(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    cameraId: Optional[UUID] = Query(None),
    incidentId: Optional[UUID] = Query(None),
    kind: Optional[str] = Query(None, description="event | continuous_ref"),
    startedFrom: Optional[str] = Query(
        None, description="ISO datetime; naive = Asia/Bangkok"
    ),
    startedTo: Optional[str] = Query(
        None, description="ISO datetime; naive = Asia/Bangkok"
    ),
    limit: int = Query(100, ge=1, le=500),
):
    await assert_request_permission(request, db, "cameras.read", companyId)
    return await video_clip_service.list_clips(
        db,
        companyId,
        camera_id=cameraId,
        incident_id=incidentId,
        kind=kind,
        started_from=video_clip_service.parse_clip_query_dt(startedFrom),
        started_to=video_clip_service.parse_clip_query_dt(startedTo),
        limit=limit,
    )


@router.get("/company/{companyId}/clips/{clipId}")
async def get_clip(
    companyId: UUID,
    clipId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, "cameras.read", companyId)
    clip = await video_clip_service.get_clip(db, companyId, clipId)
    return video_clip_service.serialize_clip(clip)


@router.get("/company/{companyId}/clips/{clipId}/download")
async def download_clip(
    companyId: UUID,
    clipId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Stream clip bytes with HTTP Range support (Starlette FileResponse)."""
    await assert_request_permission(request, db, "cameras.read", companyId)
    clip = await video_clip_service.get_clip(db, companyId, clipId)
    path = video_clip_service.resolve_clip_path(clip)
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=path.name,
        content_disposition_type="inline",
    )


@router.post("/company/{companyId}/cameras/{cameraId}/clips")
async def export_camera_clip(
    companyId: UUID,
    cameraId: UUID,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Cut/export a 5s-pre / 10s-post event clip from MediaMTX buffer or live ffmpeg."""
    await assert_request_permission(request, db, "cameras.manage", companyId)
    payload = body or {}
    incident_raw = payload.get("incidentId")
    incident_id = UUID(str(incident_raw)) if incident_raw else None
    occurred_raw = payload.get("occurredAt")
    occurred_at = None
    if occurred_raw:
        try:
            occurred_at = datetime.fromisoformat(str(occurred_raw).replace("Z", "+00:00"))
        except ValueError as exc:
            from fastapi import HTTPException

            raise HTTPException(status_code=400, detail="Invalid occurredAt") from exc
    wait = bool(payload.get("waitForPost", True))
    clip = await video_clip_service.export_event_clip(
        db,
        companyId,
        cameraId,
        incident_id=incident_id,
        occurred_at=occurred_at,
        wait_for_post=wait,
    )
    return video_clip_service.serialize_clip(clip)


@router.get("/company/{companyId}/cameras/{cameraId}/continuous-refs")
async def list_continuous_refs(
    companyId: UUID,
    cameraId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """List continuous recording refs — continuous cameras only."""
    await assert_request_permission(request, db, "cameras.read", companyId)
    rows = await video_clip_service.upsert_continuous_refs(db, companyId, cameraId)
    return [video_clip_service.serialize_clip(r) for r in rows]


@router.delete("/company/{companyId}/clips/{clipId}")
async def delete_clip(
    companyId: UUID,
    clipId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, "cameras.manage", companyId)
    return await video_clip_service.delete_clip(db, companyId, clipId)
