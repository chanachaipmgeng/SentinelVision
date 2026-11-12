"""Person presence trail APIs (locate / booth dwell / OT evidence / live)."""
from __future__ import annotations

import asyncio
from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.database import get_db
from ..security.deps import assert_request_permission
from ..services import presence_service
from ..services.analytics_service import resolve_range
from ..services.audit_service import write_audit

router = APIRouter()


def _actor(request: Request):
    return getattr(request.state, "member", None) or getattr(request.state, "user", None)


def _schedule_audit(
    request: Request,
    *,
    action: str,
    company_id: UUID,
    entity_type: str = "presence",
    entity_id: Optional[str] = None,
    detail: Optional[dict] = None,
) -> None:
    asyncio.create_task(
        write_audit(
            actor=_actor(request),
            action=action,
            path=str(request.url.path),
            status_code=200,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            request_id=getattr(request.state, "request_id", None),
            company_id=str(company_id),
            entity_type=entity_type,
            entity_id=entity_id,
            detail=detail,
        )
    )


@router.get("/company/{companyId}/search")
async def presence_search(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    q: str = Query(default="", min_length=0, max_length=120),
    limit: int = Query(default=20, ge=1, le=50),
):
    await assert_request_permission(request, db, "cameras.read", companyId)
    result = await presence_service.search_members(db, companyId, q, limit=limit)
    _schedule_audit(
        request,
        action="presence.search",
        company_id=companyId,
        detail={"q": (q or "")[:80], "resultCount": len(result.get("items") or [])},
    )
    return result


@router.get("/company/{companyId}/members/{memberId}/trail")
async def presence_trail(
    companyId: UUID,
    memberId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    start: Optional[str] = Query(default=None),
    end: Optional[str] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
):
    await assert_request_permission(request, db, "cameras.read", companyId)
    start_dt, end_dt = resolve_range(start, end)
    result = await presence_service.member_trail(
        db, companyId, memberId, start=start_dt, end=end_dt, limit=limit
    )
    _schedule_audit(
        request,
        action="presence.trail",
        company_id=companyId,
        entity_id=str(memberId),
        detail={"from": start, "to": end},
    )
    return result


@router.get("/company/{companyId}/events/{eventId}/dwell")
async def presence_event_dwell(
    companyId: UUID,
    eventId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_permission(request, db, "cameras.read", companyId)
    result = await presence_service.event_dwell_report(db, companyId, eventId)
    _schedule_audit(
        request,
        action="presence.event_dwell",
        company_id=companyId,
        entity_id=str(eventId),
    )
    return result


@router.get("/company/{companyId}/ot-evidence")
async def presence_ot_evidence(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    workDate: Optional[str] = Query(default=None),
):
    await assert_request_permission(request, db, "cameras.read", companyId)
    day: Optional[date] = None
    if workDate:
        day = date.fromisoformat(workDate)
    result = await presence_service.ot_evidence_report(db, companyId, work_date=day)
    _schedule_audit(
        request,
        action="presence.ot_evidence",
        company_id=companyId,
        detail={"workDate": result.get("workDate")},
    )
    return result


@router.get("/company/{companyId}/live")
async def presence_live(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    cameraId: Optional[UUID] = Query(default=None),
):
    await assert_request_permission(request, db, "cameras.read", companyId)
    return await presence_service.live_by_camera(db, companyId, camera_id=cameraId)
