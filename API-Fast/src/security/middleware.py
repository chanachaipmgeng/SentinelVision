"""HTTP authz: JWT required, company paths bound to the caller, Kiosk scope isolation, audit on writes."""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional
from uuid import UUID

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from ..config.database import async_session
from ..config.settings import settings
from ..models.member import Member, RoleType
from ..services.token_revocation_service import is_token_revoked
from .deps import (
    assert_company_access,
    current_kiosk_company_var,
    current_member_var,
    member_from_token,
    verify_kiosk_token_db,
)
from .jwt import decode_token

logger = logging.getLogger("dpu.authz")

_UUID = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
_COMPANY_RES = [
    re.compile(rf"/employees/company/(?:sub/)?({_UUID})"),
    re.compile(rf"/departments/company/({_UUID})"),
    re.compile(rf"/positions/company/({_UUID})"),
    re.compile(rf"/timestamp/(?:search/|export/)?company/({_UUID})"),
    re.compile(rf"/company-locations/company/({_UUID})"),
    re.compile(rf"/dashboard/stats/({_UUID})"),
    re.compile(rf"/face/kiosk-attendance/({_UUID})"),
    re.compile(rf"/companys/({_UUID})"),
    re.compile(rf"/notifications/company/({_UUID})"),
    re.compile(rf"/hr/company/({_UUID})"),
    re.compile(rf"/sentinel/company/({_UUID})"),
]
_OPEN_PREFIXES = (
    "/auth/login",
    "/auth/refresh",
    "/auth/refresh-token",
    "/auth/logout",
    "/auth/kiosk/pair",
    "/auth/kiosk/refresh",
    "/auth/sso/oidc",
    "/health",
    "/ready",
)
_KIOSK_ALLOWED_PREFIXES = (
    "/face/members/check-in",
    "/face/members/check-in-walkby",
    "/face/members/check-face-emp",
    "/face/members/identify",
    "/face/members/detect",
    "/face/kiosk-attendance/",
    "/face/enrolled-images/",
    "/face/queue-stats",
    "/sentinel/company/",
    "/company-locations/company/",
    "/images/",
    "/enrolled_images/",
    "/system/tts-settings",
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


def _client_ip(request: Request) -> Optional[str]:
    xff = (request.headers.get("x-forwarded-for") or "").strip()
    if xff:
        return xff.split(",")[0].strip()
    xrip = (request.headers.get("x-real-ip") or "").strip()
    if xrip:
        return xrip
    return request.client.host if request.client else None


def _is_kiosk_path_allowed(method: str, path: str) -> bool:
    if path == "/system/tts-settings" and method != "GET":
        return False
    if path.startswith("/company-locations/company/") and method != "GET":
        return False
    if path.startswith("/sentinel/company/"):
        if path.endswith("/scan") and method == "POST":
            return True
        if (path.endswith("/edge-sync") or path.endswith("/zones")) and method == "GET":
            return True
        return False
    return path.startswith(_KIOSK_ALLOWED_PREFIXES)


class AuthzMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path.rstrip("/") or "/"
        if request.method == "OPTIONS" or path == "/" or path.startswith(_OPEN_PREFIXES):
            return await call_next(request)
        if path == "/notifications/system":
            return await call_next(request)
        if path.startswith("/metrics") or path.startswith("/docs") or path.startswith("/redoc") or path == "/openapi.json":
            return await call_next(request)

        token = _token_from(request)
        if not token:
            return JSONResponse({"detail": "Authorization required"}, status_code=401)

        try:
            raw_payload = decode_token(token, expected_typ=None)
        except Exception as exc:
            code = getattr(exc, "status_code", 401)
            detail = getattr(exc, "detail", "Invalid token")
            return JSONResponse({"detail": detail}, status_code=code)

        if await is_token_revoked(raw_payload):
            return JSONResponse({"detail": "Token has been revoked"}, status_code=401)

        if raw_payload.get("typ") == "kiosk":
            if not _is_kiosk_path_allowed(request.method, path):
                return JSONResponse(
                    {"detail": "Kiosk device token is restricted to kiosk check-in endpoints only"},
                    status_code=403,
                )
            async with async_session() as db:
                try:
                    device = await verify_kiosk_token_db(token, db)
                except Exception as exc:
                    code = getattr(exc, "status_code", 401)
                    detail = getattr(exc, "detail", "Invalid kiosk token")
                    return JSONResponse({"detail": detail}, status_code=code)
                cid = _company_id(path)
                if cid and UUID(cid) != device.companyId:
                    return JSONResponse(
                        {"detail": "Kiosk device token does not match requested company"},
                        status_code=403,
                    )
                request.state.kiosk_company_id = device.companyId
                request.state.kiosk_device_id = device.deviceId
                kiosk_ctx = current_kiosk_company_var.set(device.companyId)
                try:
                    return await call_next(request)
                finally:
                    current_kiosk_company_var.reset(kiosk_ctx)

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
            asyncio.create_task(_audit(request, member, path, response.status_code))
        return response


def _token_from(request: Request) -> str:
    header = request.headers.get("authorization") or ""
    if header.lower().startswith("bearer "):
        return header.split(" ", 1)[1].strip()
    # `?token=` leaks credentials into proxy/browser logs. Only honoured behind the
    # deprecation flag AUTH_ALLOW_QUERY_TOKEN (default off); will be removed.
    query_token = (request.query_params.get("token") or "").strip()
    if query_token and settings.AUTH_ALLOW_QUERY_TOKEN:
        logger.warning("deprecated ?token= used path=%s ip=%s", request.url.path, _client_ip(request))
        return query_token
    return ""


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
            ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            request_id=getattr(request.state, "request_id", None),
            company_id=_company_id(path),
        )
    except Exception:
        logger.exception("audit write failed")
