"""HTTP authz: JWT required, company paths bound to the caller, audit on writes."""
from __future__ import annotations

import json
import logging
import re
from typing import Optional
from uuid import UUID

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from ..config.database import async_session
from ..models.member import Member, RoleType
from .deps import assert_company_access, current_member_var, member_from_token

logger = logging.getLogger("dpu.authz")

_UUID = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
_COMPANY_RES = [
    re.compile(rf"/employees/company/(?:sub/)?({_UUID})"),
    re.compile(rf"/departments/company/({_UUID})"),
    re.compile(rf"/positions/company/({_UUID})"),
    re.compile(rf"/timestamp/(?:search/)?company/({_UUID})"),
    re.compile(rf"/company-locations/company/({_UUID})"),
    re.compile(rf"/dashboard/stats/({_UUID})"),
    re.compile(rf"/face/kiosk-attendance/({_UUID})"),
    re.compile(rf"/companys/({_UUID})"),
    re.compile(rf"/notifications/company/({_UUID})"),
]
_OPEN_PREFIXES = (
    "/auth/login",
    "/auth/refresh",
    "/auth/refresh-token",
    "/health",
    "/ready",
)
_MEMBER_SELF = re.compile(rf"/employees/member/({_UUID})/")


def _company_id(path: str) -> Optional[str]:
    for rx in _COMPANY_RES:
        m = rx.search(path)
        if m:
            return m.group(1)
    return None


def _is_system_admin(member: Member) -> bool:
    role = member.role
    if role == RoleType.ADMIN_SYSTEM:
        return True
    value = getattr(role, "value", role)
    return value in (99, RoleType.ADMIN_SYSTEM.value)


class AuthzMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path.rstrip("/") or "/"
        if request.method == "OPTIONS" or path == "/" or path.startswith(_OPEN_PREFIXES):
            return await call_next(request)
        if path.startswith("/metrics") or path.startswith("/docs") or path.startswith("/redoc") or path == "/openapi.json":
            return await call_next(request)

        token = _token_from(request)
        if not token:
            return JSONResponse({"detail": "Authorization required"}, status_code=401)

        async with async_session() as db:
            try:
                member = await member_from_token(token, db)
            except Exception as exc:
                code = getattr(exc, "status_code", 401)
                detail = getattr(exc, "detail", "Invalid token")
                return JSONResponse({"detail": detail}, status_code=code)

            request.state.member = member
            token_ctx = current_member_var.set(member)
            try:
                denied = await _authorize(request, db, member, path)
                if denied is not None:
                    return denied
            finally:
                current_member_var.reset(token_ctx)

        response = await call_next(request)
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and response.status_code < 400:
            await _audit(request, member, path, response.status_code)
        return response


def _token_from(request: Request) -> str:
    header = request.headers.get("authorization") or ""
    if header.lower().startswith("bearer "):
        return header.split(" ", 1)[1].strip()
    return (request.query_params.get("token") or "").strip()


async def _authorize(request: Request, db, member: Member, path: str):
    if path.startswith("/members") or path.startswith("/system"):
        if request.method != "GET" and not _is_system_admin(member):
            # company admins may read TTS; writes stay system-admin
            if not (path.startswith("/system") and request.method == "GET"):
                if request.method != "GET":
                    return JSONResponse({"detail": "System admin required"}, status_code=403)
        if path.startswith("/members") and not _is_system_admin(member):
            return JSONResponse({"detail": "System admin required"}, status_code=403)
        return None

    if path in {"/companys", "/departments", "/positions"} and request.method != "GET":
        if not _is_system_admin(member) and path == "/companys":
            return JSONResponse({"detail": "System admin required"}, status_code=403)

    if path == "/companys" and request.method == "GET" and not _is_system_admin(member):
        return JSONResponse({"detail": "System admin required"}, status_code=403)

    self_m = _MEMBER_SELF.search(path)
    if self_m and not _is_system_admin(member):
        if str(member.memberId) != self_m.group(1):
            return JSONResponse({"detail": "Cannot list another member's companies"}, status_code=403)
        return None

    cid = _company_id(path)
    if cid:
        try:
            await assert_company_access(db, member, UUID(cid))
        except Exception as exc:
            code = getattr(exc, "status_code", 403)
            detail = getattr(exc, "detail", "Forbidden")
            return JSONResponse({"detail": detail}, status_code=code)
    return None


async def _audit(request: Request, member: Member, path: str, status_code: int) -> None:
    try:
        from ..services.audit_service import write_audit

        await write_audit(
            actor=member,
            action=request.method,
            path=path,
            status_code=status_code,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            request_id=getattr(request.state, "request_id", None),
            company_id=_company_id(path),
        )
    except Exception:
        logger.exception("audit write failed")
