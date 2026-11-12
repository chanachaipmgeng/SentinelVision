from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.database import get_db
from ..controllers.system_controller import (
    get_tts_settings,
    rebuild_face_index,
    update_tts_settings,
)
from ..schemas.page_schema import page_envelope
from ..security.deps import get_current_member, require_system_admin
from ..services.error_log_service import (
    SOURCE_CLIENT,
    ClientErrorIn,
    ErrorLogResolveIn,
    get_error_log,
    list_error_logs,
    schedule_error_log,
    serialize_error_log,
    set_resolved,
    should_capture_client_status,
)
from ..services.observability import get_observability_summary
from ..services.rate_limit_service import rate_limit_client_errors
from ..models.member import Member

router = APIRouter()


@router.post(
    "/rebuild-index",
    status_code=status.HTTP_200_OK,
    tags=["System"],
    summary="Face index status (pgvector — no rebuild required)",
)
async def rebuild_index_route():
    """
    Kept for backward compatibility with older admin tooling.
    InsightFace embeddings are stored in Postgres with pgvector; there is no
    separate FAISS file to rebuild.
    """
    return await rebuild_face_index()


@router.get(
    "/tts-settings",
    tags=["System"],
    summary="Global TTS speech templates (shared by all companies)",
)
async def get_tts_settings_route(db: AsyncSession = Depends(get_db)):
    return await get_tts_settings(db)


@router.put(
    "/tts-settings",
    tags=["System"],
    summary="Update global TTS speech templates",
)
async def put_tts_settings_route(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    return await update_tts_settings(payload, db)


@router.get(
    "/observability-summary",
    tags=["System"],
    summary="Live Prometheus latency histograms, GPU queue, and Cloud Storage status",
)
async def get_observability_summary_route(_member=Depends(get_current_member)):
    return get_observability_summary()


@router.post(
    "/client-errors",
    status_code=status.HTTP_202_ACCEPTED,
    tags=["System"],
    summary="Ingest a frontend / client HTTP failure for system-admin triage",
)
async def post_client_error(
    request: Request,
    body: ClientErrorIn,
    _rl=Depends(rate_limit_client_errors),
):
    if not should_capture_client_status(body.statusCode):
        return {"accepted": False, "reason": "status_not_captured"}

    member = getattr(request.state, "member", None)
    actor_id = getattr(member, "memberId", None) if member is not None else None
    company_id = (
        body.companyId
        or getattr(request.state, "company_id", None)
        or getattr(request.state, "kiosk_company_id", None)
    )
    headers = request.headers
    xff = (headers.get("x-forwarded-for") or "").strip()
    ip = xff.split(",")[0].strip() if xff else (headers.get("x-real-ip") or "").strip() or None
    if not ip and request.client:
        ip = request.client.host

    schedule_error_log(
        source=SOURCE_CLIENT,
        status_code=int(body.statusCode),
        message=body.message,
        method=body.method,
        path=body.path,
        error_code=body.errorCode,
        exception_type="ClientHttpError",
        stack=body.stack,
        request_id=body.requestId or getattr(request.state, "request_id", None),
        trace_id=getattr(request.state, "trace_id", None),
        company_id=company_id,
        actor_member_id=actor_id,
        page_url=body.pageUrl,
        user_agent=headers.get("user-agent"),
        ip=ip,
        detail=None,
    )
    return {"accepted": True}


@router.get(
    "/error-logs",
    tags=["System"],
    summary="List persisted API/client errors (system admin)",
)
async def get_error_logs_route(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    q: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    statusCode: Optional[int] = Query(None),
    resolved: Optional[bool] = Query(None),
    dateFrom: Optional[str] = Query(None),
    dateTo: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_dir: str = Query("desc"),
    paged: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    _admin: Member = Depends(require_system_admin),
):
    rows, total = await list_error_logs(
        db,
        limit=limit,
        offset=offset,
        q=q,
        source=source,
        status_code=statusCode,
        resolved=resolved,
        date_from=dateFrom,
        date_to=dateTo,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    items = [serialize_error_log(r, include_stack=False) for r in rows]
    if paged:
        return page_envelope(items, total=total, limit=limit, offset=offset)
    return items


@router.get(
    "/error-logs/{errorId}",
    tags=["System"],
    summary="Error log detail including stack (system admin)",
)
async def get_error_log_detail_route(
    errorId: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Member = Depends(require_system_admin),
):
    row = await get_error_log(db, errorId)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Error log not found")
    return serialize_error_log(row, include_stack=True)


@router.patch(
    "/error-logs/{errorId}",
    tags=["System"],
    summary="Mark an error log resolved or reopen it (system admin)",
)
async def patch_error_log_route(
    errorId: UUID,
    body: ErrorLogResolveIn,
    db: AsyncSession = Depends(get_db),
    admin: Member = Depends(require_system_admin),
):
    row = await get_error_log(db, errorId)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Error log not found")
    row = await set_resolved(db, row, resolved=bool(body.resolved), actor_member_id=admin.memberId)
    return serialize_error_log(row, include_stack=True)
