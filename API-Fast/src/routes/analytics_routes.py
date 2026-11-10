"""Phase 6C face-monitor analytics HTTP API."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.database import get_db
from ..security.deps import assert_request_permission
from ..services import analytics_pdf_service, analytics_service

router = APIRouter()


async def _guard(request: Request, db: AsyncSession, company_id: UUID) -> None:
    # Face-monitor sits under CCTV nav — cameras.read is the natural gate.
    await assert_request_permission(request, db, "cameras.read", company_id)


@router.get("/company/{companyId}/heatmap")
async def heatmap(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    source: str = Query(default="incidents"),
):
    await _guard(request, db, companyId)
    start_dt, end_dt = analytics_service.resolve_range(start, end)
    return await analytics_service.get_hour_day_heatmap(
        db, companyId, start=start_dt, end=end_dt, source=source
    )


@router.get("/company/{companyId}/occupancy")
async def occupancy(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
):
    await _guard(request, db, companyId)
    start_dt, end_dt = analytics_service.resolve_range(start, end)
    return await analytics_service.get_occupancy_series(
        db, companyId, start=start_dt, end=end_dt
    )


@router.get("/company/{companyId}/dwell")
async def dwell(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
):
    await _guard(request, db, companyId)
    start_dt, end_dt = analytics_service.resolve_range(start, end)
    return await analytics_service.get_dwell_series(
        db, companyId, start=start_dt, end=end_dt
    )


@router.get("/company/{companyId}/camera-health")
async def camera_health(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
):
    await _guard(request, db, companyId)
    start_dt, end_dt = analytics_service.resolve_range(start, end)
    return await analytics_service.get_camera_health(
        db, companyId, start=start_dt, end=end_dt
    )


@router.get("/company/{companyId}/summary")
async def summary(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    source: str = Query(default="both"),
):
    await _guard(request, db, companyId)
    start_dt, end_dt = analytics_service.resolve_range(start, end)
    return await analytics_service.get_analytics_summary(
        db, companyId, start=start_dt, end=end_dt, source=source
    )


@router.get("/company/{companyId}/export/pdf")
async def export_pdf(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    source: str = Query(default="both"),
):
    await _guard(request, db, companyId)
    start_dt, end_dt = analytics_service.resolve_range(start, end)
    payload = await analytics_service.get_analytics_summary(
        db, companyId, start=start_dt, end=end_dt, source=source
    )
    pdf = analytics_pdf_service.render_analytics_pdf(payload)
    filename = f"face-monitor-{companyId}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
