"""Persist API and client-reported errors for system-admin triage."""
from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import traceback
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, Index, Integer, String, Text, and_, delete, func, or_, select
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.database import Base, async_session
from ..config.settings import settings
from .observability import current_company_id_var, current_request_id_var, current_trace_id_var, redact

logger = logging.getLogger("dpu.error_log")

SOURCE_API = "api"
SOURCE_CLIENT = "client"

_CAPTURE_STATUSES = frozenset({400, 409, 422})
_DEDUP_WINDOW = timedelta(minutes=5)
_UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
_NUM_SEGMENT_RE = re.compile(r"/\d+(?=/|$)")
_MAX_MESSAGE = 2000
_MAX_STACK = 8000
_MAX_PATH = 500
_MAX_PAGE_URL = 1000
_MAX_UA = 500
_MAX_CODE = 64


class ErrorLog(Base):
    __tablename__ = "error_log"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    occurredAt = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    lastSeenAt = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    hitCount = Column(Integer, nullable=False, default=1, server_default="1")
    source = Column(String(16), nullable=False)
    statusCode = Column(Integer, nullable=False)
    method = Column(String(16), nullable=True)
    path = Column(String(500), nullable=True)
    errorCode = Column(String(64), nullable=True)
    message = Column(Text, nullable=False)
    exceptionType = Column(String(128), nullable=True)
    stack = Column(Text, nullable=True)
    requestId = Column(String(64), nullable=True)
    traceId = Column(String(64), nullable=True)
    companyId = Column(PGUUID(as_uuid=True), nullable=True)
    actorMemberId = Column(PGUUID(as_uuid=True), nullable=True)
    pageUrl = Column(String(1000), nullable=True)
    userAgent = Column(Text, nullable=True)
    ip = Column(String(64), nullable=True)
    fingerprint = Column(String(64), nullable=False)
    detail = Column(JSONB, nullable=True)
    resolvedAt = Column(DateTime(timezone=True), nullable=True)
    resolvedBy = Column(PGUUID(as_uuid=True), nullable=True)

    __table_args__ = (
        Index("error_log_occurred_idx", occurredAt.desc()),
        Index("error_log_fingerprint_seen_idx", "fingerprint", lastSeenAt.desc()),
        Index("error_log_source_status_idx", "source", "statusCode"),
    )


class ClientErrorIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=_MAX_MESSAGE)
    statusCode: int = Field(0, ge=0, le=599)
    method: Optional[str] = Field(None, max_length=16)
    path: Optional[str] = Field(None, max_length=_MAX_PATH)
    pageUrl: Optional[str] = Field(None, max_length=_MAX_PAGE_URL)
    requestId: Optional[str] = Field(None, max_length=64)
    errorCode: Optional[str] = Field(None, max_length=_MAX_CODE)
    stack: Optional[str] = Field(None, max_length=_MAX_STACK)
    companyId: Optional[str] = None


class ErrorLogResolveIn(BaseModel):
    resolved: bool = True


def should_capture_status(status_code: int) -> bool:
    code = int(status_code or 0)
    if code >= 500:
        return True
    return code in _CAPTURE_STATUSES


def should_capture_client_status(status_code: int) -> bool:
    code = int(status_code or 0)
    if code == 0:
        return True
    return should_capture_status(code)


def strip_query(path: Optional[str]) -> str:
    raw = (path or "").strip()
    if not raw:
        return ""
    return raw.split("?", 1)[0][:_MAX_PATH]


def normalize_path(path: Optional[str]) -> str:
    cleaned = strip_query(path)
    if not cleaned:
        return ""
    cleaned = _UUID_RE.sub("{id}", cleaned)
    cleaned = _NUM_SEGMENT_RE.sub("/{id}", cleaned)
    return cleaned[:_MAX_PATH]


def build_fingerprint(
    *,
    source: str,
    method: Optional[str],
    path: Optional[str],
    status_code: int,
    exception_type: Optional[str],
) -> str:
    parts = [
        (source or "").lower(),
        (method or "").upper(),
        normalize_path(path),
        str(int(status_code or 0)),
        (exception_type or "").strip(),
    ]
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return digest[:40]


def _clip(value: Optional[str], limit: int) -> Optional[str]:
    if value is None:
        return None
    text = str(value)
    if not text:
        return None
    return text[:limit]


def _parse_uuid(value: Any) -> Optional[UUID]:
    if value is None or value == "":
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def serialize_error_log(row: ErrorLog, *, include_stack: bool = False) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": str(row.id),
        "occurredAt": row.occurredAt.isoformat() if row.occurredAt else None,
        "lastSeenAt": row.lastSeenAt.isoformat() if row.lastSeenAt else None,
        "hitCount": int(row.hitCount or 1),
        "source": row.source,
        "statusCode": int(row.statusCode or 0),
        "method": row.method,
        "path": row.path,
        "errorCode": row.errorCode,
        "message": row.message,
        "exceptionType": row.exceptionType,
        "requestId": row.requestId,
        "traceId": row.traceId,
        "companyId": str(row.companyId) if row.companyId else None,
        "actorMemberId": str(row.actorMemberId) if row.actorMemberId else None,
        "pageUrl": row.pageUrl,
        "userAgent": row.userAgent,
        "ip": row.ip,
        "fingerprint": row.fingerprint,
        "detail": row.detail,
        "resolvedAt": row.resolvedAt.isoformat() if row.resolvedAt else None,
        "resolvedBy": str(row.resolvedBy) if row.resolvedBy else None,
    }
    if include_stack:
        payload["stack"] = row.stack
    return payload


async def write_error_log(
    *,
    source: str,
    status_code: int,
    message: str,
    method: Optional[str] = None,
    path: Optional[str] = None,
    error_code: Optional[str] = None,
    exception_type: Optional[str] = None,
    stack: Optional[str] = None,
    request_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    company_id: Optional[str | UUID] = None,
    actor_member_id: Optional[str | UUID] = None,
    page_url: Optional[str] = None,
    user_agent: Optional[str] = None,
    ip: Optional[str] = None,
    detail: Optional[dict[str, Any]] = None,
) -> Optional[ErrorLog]:
    """Insert or bump hitCount for an unresolved fingerprint within the dedupe window."""
    now = datetime.now(timezone.utc)
    clean_path = strip_query(path)
    fingerprint = build_fingerprint(
        source=source,
        method=method,
        path=clean_path,
        status_code=status_code,
        exception_type=exception_type,
    )
    safe_detail = redact(detail) if detail is not None else None
    cutoff = now - _DEDUP_WINDOW

    async with async_session() as db:
        existing = (
            await db.execute(
                select(ErrorLog)
                .where(
                    and_(
                        ErrorLog.fingerprint == fingerprint,
                        ErrorLog.resolvedAt.is_(None),
                        ErrorLog.lastSeenAt >= cutoff,
                    )
                )
                .order_by(ErrorLog.lastSeenAt.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        if existing is not None:
            existing.hitCount = int(existing.hitCount or 1) + 1
            existing.lastSeenAt = now
            if request_id:
                existing.requestId = request_id[:64]
            if trace_id:
                existing.traceId = trace_id[:64]
            if safe_detail is not None:
                existing.detail = safe_detail
            await db.commit()
            await db.refresh(existing)
            return existing

        row = ErrorLog(
            id=uuid4(),
            occurredAt=now,
            lastSeenAt=now,
            hitCount=1,
            source=(source or SOURCE_API)[:16],
            statusCode=int(status_code or 0),
            method=_clip((method or "").upper() or None, 16),
            path=_clip(clean_path, _MAX_PATH),
            errorCode=_clip(error_code, _MAX_CODE),
            message=_clip(message, _MAX_MESSAGE) or "Error",
            exceptionType=_clip(exception_type, 128),
            stack=_clip(stack, _MAX_STACK),
            requestId=_clip(request_id, 64),
            traceId=_clip(trace_id, 64),
            companyId=_parse_uuid(company_id),
            actorMemberId=_parse_uuid(actor_member_id),
            pageUrl=_clip(page_url, _MAX_PAGE_URL),
            userAgent=_clip(user_agent, _MAX_UA),
            ip=_clip(ip, 64),
            fingerprint=fingerprint,
            detail=safe_detail,
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return row


async def _safe_write_error_log(**kwargs: Any) -> None:
    try:
        await write_error_log(**kwargs)
    except Exception:
        logger.exception("error_log write failed")


def schedule_error_log(**kwargs: Any) -> None:
    """Fire-and-forget write; never raises into the request path."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(_safe_write_error_log(**kwargs))


def schedule_api_error(
    request: Any,
    *,
    status_code: int,
    message: str,
    error_code: Optional[str] = None,
    exc: Optional[BaseException] = None,
    details: Any = None,
) -> None:
    if not should_capture_status(status_code):
        return
    member = getattr(getattr(request, "state", None), "member", None)
    actor_id = getattr(member, "memberId", None) if member is not None else None
    company_id = (
        getattr(getattr(request, "state", None), "company_id", None)
        or getattr(getattr(request, "state", None), "kiosk_company_id", None)
        or current_company_id_var.get("")
        or None
    )
    request_id = getattr(getattr(request, "state", None), "request_id", None) or current_request_id_var.get("")
    trace_id = getattr(getattr(request, "state", None), "trace_id", None) or current_trace_id_var.get("")
    method = getattr(request, "method", None)
    path = str(getattr(getattr(request, "url", None), "path", "") or "")
    headers = getattr(request, "headers", None)
    user_agent = headers.get("user-agent") if headers is not None else None
    client = getattr(request, "client", None)
    ip = None
    if headers is not None:
        xff = (headers.get("x-forwarded-for") or "").strip()
        if xff:
            ip = xff.split(",")[0].strip()
        else:
            ip = (headers.get("x-real-ip") or "").strip() or None
    if not ip and client is not None:
        ip = getattr(client, "host", None)

    exception_type = type(exc).__name__ if exc is not None else None
    stack = None
    if exc is not None and int(status_code) >= 500:
        stack = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

    detail: Optional[dict[str, Any]] = None
    if details is not None:
        detail = {"details": details}

    schedule_error_log(
        source=SOURCE_API,
        status_code=int(status_code),
        message=message,
        method=method,
        path=path,
        error_code=error_code,
        exception_type=exception_type,
        stack=stack,
        request_id=request_id or None,
        trace_id=trace_id or None,
        company_id=company_id,
        actor_member_id=actor_id,
        user_agent=user_agent,
        ip=ip,
        detail=detail,
    )


async def list_error_logs(
    db: AsyncSession,
    *,
    limit: int = 50,
    offset: int = 0,
    q: Optional[str] = None,
    source: Optional[str] = None,
    status_code: Optional[int] = None,
    resolved: Optional[bool] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_dir: str = "desc",
) -> tuple[list[ErrorLog], int]:
    clauses: list[Any] = []
    source_q = (source or "").strip().lower()
    if source_q in {SOURCE_API, SOURCE_CLIENT}:
        clauses.append(ErrorLog.source == source_q)
    if status_code is not None:
        clauses.append(ErrorLog.statusCode == int(status_code))
    if resolved is True:
        clauses.append(ErrorLog.resolvedAt.is_not(None))
    elif resolved is False:
        clauses.append(ErrorLog.resolvedAt.is_(None))

    if date_from:
        try:
            start = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            clauses.append(ErrorLog.occurredAt >= start)
        except ValueError:
            pass
    if date_to:
        try:
            end = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
            # Inclusive calendar day when only a date is provided.
            if len(date_to.strip()) <= 10:
                end = end + timedelta(days=1)
            clauses.append(ErrorLog.occurredAt < end)
        except ValueError:
            pass

    free = (q or "").strip()
    if free:
        like = f"%{free}%"
        clauses.append(
            or_(
                ErrorLog.path.ilike(like),
                ErrorLog.message.ilike(like),
                ErrorLog.errorCode.ilike(like),
                ErrorLog.requestId.ilike(like),
                ErrorLog.exceptionType.ilike(like),
            )
        )

    where = and_(*clauses) if clauses else True
    total = int((await db.execute(select(func.count()).select_from(ErrorLog).where(where))).scalar_one() or 0)

    sort_map = {
        "occurredAt": ErrorLog.occurredAt,
        "lastSeenAt": ErrorLog.lastSeenAt,
        "statusCode": ErrorLog.statusCode,
        "hitCount": ErrorLog.hitCount,
        "source": ErrorLog.source,
        "path": ErrorLog.path,
    }
    col = sort_map.get((sort_by or "").strip() or "lastSeenAt", ErrorLog.lastSeenAt)
    order = col.asc() if (sort_dir or "desc").lower() == "asc" else col.desc()

    safe_limit = min(max(int(limit or 50), 1), 500)
    safe_offset = max(0, int(offset or 0))
    rows = (
        await db.execute(select(ErrorLog).where(where).order_by(order).offset(safe_offset).limit(safe_limit))
    ).scalars().all()
    return list(rows), total


async def get_error_log(db: AsyncSession, error_id: UUID) -> Optional[ErrorLog]:
    return await db.get(ErrorLog, error_id)


async def set_resolved(
    db: AsyncSession,
    row: ErrorLog,
    *,
    resolved: bool,
    actor_member_id: Optional[UUID],
) -> ErrorLog:
    if resolved:
        row.resolvedAt = datetime.now(timezone.utc)
        row.resolvedBy = actor_member_id
    else:
        row.resolvedAt = None
        row.resolvedBy = None
    await db.commit()
    await db.refresh(row)
    return row


async def purge_old_error_logs(*, retention_days: Optional[int] = None) -> int:
    days = retention_days
    if days is None:
        days = int(getattr(settings, "ERROR_LOG_RETENTION_DAYS", 30) or 30)
    days = max(1, int(days))
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    async with async_session() as db:
        result = await db.execute(delete(ErrorLog).where(ErrorLog.occurredAt < cutoff))
        await db.commit()
        return int(result.rowcount or 0)
