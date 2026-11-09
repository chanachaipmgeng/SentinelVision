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
from ..schemas.error_schema import error_body, http_exception_code, sanitize_public_message
from ..services.observability import set_company_context
from ..services.token_revocation_service import is_token_revoked
from ..utils.api_paths import canonical_api_path
from .deps import (
    assert_company_access,
    current_kiosk_company_var,
    current_member_var,
    member_from_token,
    verify_kiosk_token_db,
)
from ..services.approval_gate import assert_company_membership
from ..services import rbac_service
from .jwt import decode_token


def _error(status_code: int, detail: str, request: Request | None = None) -> JSONResponse:
    rid = getattr(request.state, "request_id", None) if request is not None else None
    return JSONResponse(
        error_body(
            code=http_exception_code(status_code, detail),
            message=sanitize_public_message(detail, status_code=status_code),
            status_code=status_code,
            request_id=rid,
        ),
        status_code=status_code,
    )

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
    re.compile(rf"/devices/company/({_UUID})"),
    re.compile(rf"/cameras/company/({_UUID})"),
    re.compile(rf"/site-floors/company/({_UUID})"),
]
# Tenant API keys (Bearer sv_…) — read-only scopes → path allow-lists.
_API_KEY_SCOPE_RES = (
    (
        "cameras.read",
        re.compile(rf"^/cameras/company/({_UUID})(?:/|$)"),
        frozenset({"GET"}),
    ),
    (
        "incidents.read",
        re.compile(rf"^/sentinel/company/({_UUID})/incidents(?:/|$)"),
        frozenset({"GET"}),
    ),
)
# D1: approval decision / inbox paths — require approve permission (or membership for boss fallback).
# Self-service create/list paths stay on membership only.
_APPROVAL_PERM_RES = [
    (re.compile(rf"/timestamp/company/({_UUID})/{_UUID}/approval/?$"), rbac_service.PERM_ATTENDANCE_APPROVE),
    (re.compile(rf"/hr/company/({_UUID})/leaves/{_UUID}/approval/?$"), rbac_service.PERM_HR_APPROVE),
    (re.compile(rf"/hr/company/({_UUID})/approvals(?:/|$)"), rbac_service.PERM_HR_APPROVE),
    (re.compile(rf"/hr/company/({_UUID})/regularizations/{_UUID}/approval/?$"), rbac_service.PERM_HR_APPROVE),
    (re.compile(rf"/hr/company/({_UUID})/ot-approvals/{_UUID}/approval/?$"), rbac_service.PERM_HR_APPROVE),
]
# Lifecycle management endpoints system admins may hit even when the tenant is suspended.
_TENANT_LIFECYCLE_ALLOW = re.compile(
    rf"^/companys/({_UUID})/(?:suspend|resume|offboard|quotas|tenant)/?$"
)
_APPROVAL_MEMBERSHIP_RES = [
    re.compile(rf"/hr/company/({_UUID})/regularizations(?:/|$)"),
    re.compile(rf"/hr/company/({_UUID})/ot-approvals(?:/|$)"),
    re.compile(rf"/hr/company/({_UUID})/leave-balances(?:/|$)"),
]
_OPEN_PREFIXES = (
    "/auth/login",
    "/auth/refresh",
    "/auth/refresh-token",
    "/auth/logout",
    "/auth/kiosk/pair",
    "/auth/kiosk/refresh",
    "/auth/sso/oidc",
    "/auth/send-reset-password",
    "/auth/reset-password",
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
    "/devices/company/",
    "/images/",
    "/enrolled_images/",
    "/system/tts-settings",
)
_MEMBER_SELF = re.compile(rf"/employees/member/({_UUID})/")
# Routes keyed by a tenant-owned resource id (no companyId in the path). The owning
# company is resolved from the row so the caller can be bound to it like /…/company/{id}.
_RESOURCE_RES = (
    (re.compile(rf"^/departments/({_UUID})$"), "department"),
    (re.compile(rf"^/positions/({_UUID})$"), "position"),
)
# Collection listings that span every tenant — system admin only.
_SYSTEM_ADMIN_LISTINGS = frozenset({"/departments", "/positions"})


def _company_id(path: str) -> Optional[str]:
    for rx in _COMPANY_RES:
        m = rx.search(path)
        if m:
            return m.group(1)
    return None


async def _resource_company_id(db, path: str) -> Optional[UUID]:
    """Resolve the owning companyId for /departments/{id} and /positions/{id}."""
    for rx, kind in _RESOURCE_RES:
        m = rx.match(path)
        if not m:
            continue
        rid = UUID(m.group(1))
        if kind == "department":
            from ..models.department import Department

            row = await db.get(Department, rid)
        else:
            from ..models.position import Position

            row = await db.get(Position, rid)
        if row is None:
            return None
        return row.companyId
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


def _is_api_key_path_allowed(method: str, path: str, scopes: list[str] | None) -> bool:
    allowed = set(scopes or [])
    for scope, rx, methods in _API_KEY_SCOPE_RES:
        if scope not in allowed:
            continue
        if method.upper() not in methods:
            continue
        if rx.search(path):
            return True
    return False


def _is_kiosk_path_allowed(method: str, path: str) -> bool:
    if path == "/system/tts-settings" and method != "GET":
        return False
    if path.startswith("/company-locations/company/") and method != "GET":
        return False
    if path.startswith("/devices/company/"):
        # Kiosk may only POST heartbeat on its own device (handler enforces deviceId).
        return method == "POST" and path.rstrip("/").endswith("/heartbeat")
    if path.startswith("/sentinel/company/"):
        if path.endswith("/scan") and method == "POST":
            return True
        if method == "GET" and path.endswith(
            ("/edge-sync", "/zones", "/events", "/module-config")
        ):
            return True
        return False
    return path.startswith(_KIOSK_ALLOWED_PREFIXES)


class AuthzMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        raw_path = request.url.path.rstrip("/") or "/"
        # Authz + kiosk allow-lists operate on the legacy shape so /api/v1 and
        # /companies aliases share the same rules as /companys and root paths.
        path = canonical_api_path(raw_path)
        if request.method == "OPTIONS" or path == "/" or path.startswith(_OPEN_PREFIXES):
            return await call_next(request)
        if path == "/notifications/system":
            return await call_next(request)
        if path.startswith("/metrics") or path.startswith("/docs") or path.startswith("/redoc") or path == "/openapi.json":
            return await call_next(request)

        token = _token_from(request)
        if not token:
            return _error(401, "Authorization required", request)

        # Phase 5 tenant API keys: Authorization: Bearer sv_…
        if token.startswith("sv_"):
            from ..services.api_key_service import verify_bearer_api_key

            async with async_session() as db:
                key_row = await verify_bearer_api_key(db, token)
                if key_row is None:
                    return _error(401, "Invalid API key", request)
                cid = _company_id(path)
                if not cid:
                    return _error(403, "API key requires a company-scoped path", request)
                if UUID(cid) != key_row.companyId:
                    return _error(403, "API key does not match requested company", request)
                if not _is_api_key_path_allowed(request.method, path, key_row.scopes):
                    return _error(403, "API key scope does not allow this endpoint", request)
                request.state.api_key_company_id = key_row.companyId
                request.state.api_key_scopes = list(key_row.scopes or [])
                request.state.api_key_id = key_row.apiKeyId
                set_company_context(key_row.companyId)
                return await call_next(request)

        try:
            raw_payload = decode_token(token, expected_typ=None)
        except Exception as exc:
            code = getattr(exc, "status_code", 401)
            detail = getattr(exc, "detail", "Invalid token")
            return _error(code, detail if isinstance(detail, str) else "Invalid token", request)

        if await is_token_revoked(raw_payload):
            return _error(401, "Token has been revoked", request)

        if raw_payload.get("typ") == "kiosk":
            if not _is_kiosk_path_allowed(request.method, path):
                return _error(
                    403,
                    "Kiosk device token is restricted to kiosk check-in endpoints only",
                    request,
                )
            async with async_session() as db:
                try:
                    device = await verify_kiosk_token_db(token, db)
                except Exception as exc:
                    code = getattr(exc, "status_code", 401)
                    detail = getattr(exc, "detail", "Invalid kiosk token")
                    return _error(code, detail if isinstance(detail, str) else "Invalid kiosk token", request)
                cid = _company_id(path)
                if cid and UUID(cid) != device.companyId:
                    return _error(
                        403,
                        "Kiosk device token does not match requested company",
                        request,
                    )
                request.state.kiosk_company_id = device.companyId
                request.state.kiosk_device_id = device.deviceId
                set_company_context(device.companyId)
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
                return _error(code, detail if isinstance(detail, str) else "Invalid token", request)

            request.state.member = member
            token_ctx = current_member_var.set(member)
            try:
                denied = await _authorize(request, db, member, path)
                if denied is not None:
                    return denied
            finally:
                current_member_var.reset(token_ctx)

        # Tenant correlation for JSON logs emitted by the handler (reset by RequestIdMiddleware).
        set_company_context(_company_id(path) or getattr(request.state, "company_id", None))
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
                    return _error(403, "System admin required", request)
        if path.startswith("/members") and not _is_system_admin(member):
            return _error(403, "System admin required", request)
        return None

    if path in {"/companys", "/departments", "/positions"} and request.method != "GET":
        if not _is_system_admin(member) and path == "/companys":
            return _error(403, "System admin required", request)

    if path == "/companys" and request.method == "GET" and not _is_system_admin(member):
        return _error(403, "System admin required", request)

    if path in _SYSTEM_ADMIN_LISTINGS and request.method == "GET" and not _is_system_admin(member):
        return _error(403, "System admin required", request)

    self_m = _MEMBER_SELF.search(path)
    if self_m and not _is_system_admin(member):
        if str(member.memberId) != self_m.group(1):
            return _error(403, "Cannot list another member's companies", request)
        return None

    cid = _company_id(path)
    if not cid:
        # /departments/{id}, /positions/{id}: bind through the row's companyId.
        # Unknown ids fall through so the handler returns its usual 404.
        resolved = await _resource_company_id(db, path)
        if resolved is not None:
            cid = str(resolved)
            request.state.company_id = resolved
    if cid:
        try:
            perm_hit = next((perm for rx, perm in _APPROVAL_PERM_RES if rx.search(path)), None)
            if perm_hit is not None:
                # Permission holders enter; bosses without a role still need membership so the
                # handler's can_approve_for_employee (boss match) can run.
                has_perm = await rbac_service.has_permission(
                    db, member, perm_hit, UUID(cid)
                )
                if not has_perm:
                    # Also accept the sibling approve permission (attendance ↔ hr).
                    alt = (
                        rbac_service.PERM_HR_APPROVE
                        if perm_hit == rbac_service.PERM_ATTENDANCE_APPROVE
                        else rbac_service.PERM_ATTENDANCE_APPROVE
                    )
                    has_perm = await rbac_service.has_permission(db, member, alt, UUID(cid))
                if has_perm:
                    pass
                else:
                    await assert_company_membership(db, member, UUID(cid))
            elif any(rx.search(path) for rx in _APPROVAL_MEMBERSHIP_RES):
                await assert_company_membership(db, member, UUID(cid))
            else:
                await assert_company_access(db, member, UUID(cid))
            # D5: block operational access to suspended/offboarded tenants.
            # System admins may still hit lifecycle/quota endpoints + GET /companys/{id}.
            life_denied = await _lifecycle_denied(db, member, UUID(cid), path)
            if life_denied is not None:
                return life_denied
        except Exception as exc:
            code = getattr(exc, "status_code", 403)
            detail = getattr(exc, "detail", "Forbidden")
            return _error(code, detail if isinstance(detail, str) else "Forbidden", request)
    return None


async def _lifecycle_denied(db, member: Member, company_id: UUID, path: str):
    from ..models.company import Company, LifecycleStatus

    company = await db.get(Company, company_id)
    if company is None or company.deletedAt is not None:
        return None
    life = (company.lifecycleStatus or LifecycleStatus.ACTIVE).upper()
    if life == LifecycleStatus.ACTIVE:
        return None
    if _is_system_admin(member) and (
        _TENANT_LIFECYCLE_ALLOW.match(path) or path.rstrip("/") == f"/companys/{company_id}"
    ):
        return None
    detail = "Company is suspended" if life == LifecycleStatus.SUSPENDED else "Company is offboarded"
    return JSONResponse({"detail": detail}, status_code=403)


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
            company_id=_company_id(path) or getattr(request.state, "company_id", None),
        )
    except Exception:
        logger.exception("audit write failed")
