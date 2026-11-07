"""Request auth dependencies, company tenancy checks, and Kiosk device token validation."""
from __future__ import annotations

from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Callable, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.database import get_db
from ..models.company_employee import CompanyEmployee, CompanyRoleType
from ..models.hr_schedule import KioskDevice
from ..models.member import Member, RoleType
from ..services import rbac_service
from .jwt import decode_token, hash_kiosk_token

_bearer = HTTPBearer(auto_error=False)
current_member_var: ContextVar[Optional[Member]] = ContextVar("current_member", default=None)
current_kiosk_company_var: ContextVar[Optional[UUID]] = ContextVar("current_kiosk_company", default=None)


def _is_system_admin(member: Member) -> bool:
    return rbac_service.is_system_admin_member(member)


async def verify_kiosk_token_db(token: str, db: AsyncSession) -> KioskDevice:
    """Validate a typ='kiosk' JWT against kiosk_device (not revoked, matching token_hash)."""
    payload = decode_token(token, expected_typ="kiosk")
    device_id = UUID(str(payload["deviceId"]))
    company_id = UUID(str(payload["companyId"]))
    device = await db.get(KioskDevice, device_id)
    if device is None or device.companyId != company_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Kiosk device not found")
    if device.revokedAt is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Kiosk device token has been revoked")
    if device.tokenHash != hash_kiosk_token(token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid kiosk device token")
    # D5: refuse kiosk traffic for suspended/offboarded tenants.
    from ..models.company import Company, LifecycleStatus

    company = await db.get(Company, company_id)
    if company is not None:
        life = (company.lifecycleStatus or LifecycleStatus.ACTIVE).upper()
        if life == LifecycleStatus.SUSPENDED:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Company is suspended")
        if life == LifecycleStatus.OFFBOARDED:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Company is offboarded")
    device.lastSeenAt = datetime.now(timezone.utc)
    await db.commit()
    return device


async def member_from_token(token: str, db: AsyncSession) -> Member:
    payload = decode_token(token, expected_typ="access")
    member = await db.get(Member, UUID(str(payload["memberId"])))
    if member is None or getattr(member, "deletedAt", None) is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Member not found")
    status_val = getattr(member.status, "value", member.status)
    if status_val in (0, "DISABLED"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")
    return member


async def get_current_member(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> Member:
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization required")
    member = await member_from_token(credentials.credentials, db)
    current_member_var.set(member)
    return member


async def require_system_admin(member: Member = Depends(get_current_member)) -> Member:
    if not _is_system_admin(member):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="System admin required")
    return member


async def assert_company_access(db: AsyncSession, member: Optional[Member], company_id) -> None:
    """Elevated company access: system admin, legacy ADMIN_COMPANY, or any D1 RBAC role."""
    cid = UUID(str(company_id))
    kiosk_cid = current_kiosk_company_var.get()
    if kiosk_cid is not None:
        if kiosk_cid == cid:
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Kiosk token scoped to a different company")
    if member is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization required")
    if _is_system_admin(member):
        return
    emp = await rbac_service.get_company_employment(db, member.memberId, cid)
    if emp is None:
        # Still allow members with an explicit company-scoped RBAC assignment (no emp row).
        if await rbac_service.has_any_elevated_company_access(db, member, cid):
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this company")
    if rbac_service.is_legacy_company_admin(emp.companyRoleType):
        return
    if await rbac_service.has_any_elevated_company_access(db, member, cid):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Company admin required")


async def assert_request_company_access(request, db: AsyncSession, company_id) -> Optional[Member]:
    """Bind a companyId taken from a form/body to the member or kiosk device resolved by AuthzMiddleware."""
    cid = UUID(str(company_id))
    kiosk_cid = getattr(request.state, "kiosk_company_id", None) or current_kiosk_company_var.get()
    if kiosk_cid is not None:
        if UUID(str(kiosk_cid)) == cid:
            return None
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Kiosk token scoped to a different company")
    member = getattr(request.state, "member", None) or current_member_var.get()
    if member is None:
        from ..config.settings import settings

        if not settings.FACE_ROUTES_REQUIRE_JWT:
            return None
    await assert_company_access(db, member, company_id)
    return member


async def assert_request_company_membership(request, db: AsyncSession, company_id) -> Optional[Member]:
    """Softer than assert_request_company_access: any company employment (for thin C4 approval paths)."""
    from ..services.approval_gate import assert_company_membership

    cid = UUID(str(company_id))
    kiosk_cid = getattr(request.state, "kiosk_company_id", None) or current_kiosk_company_var.get()
    if kiosk_cid is not None:
        if UUID(str(kiosk_cid)) == cid:
            return None
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Kiosk token scoped to a different company")
    member = getattr(request.state, "member", None) or current_member_var.get()
    if member is None:
        from ..config.settings import settings

        if not settings.FACE_ROUTES_REQUIRE_JWT:
            return None
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization required")
    await assert_company_membership(db, member, cid)
    return member


async def assert_member_company_access(request, db: AsyncSession, target_member_id) -> None:
    """Ensure caller is system admin, the member themselves, or a company admin of the target member's company."""
    member = getattr(request.state, "member", None) or current_member_var.get()
    if member is None:
        from ..config.settings import settings

        if not settings.FACE_ROUTES_REQUIRE_JWT:
            return
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization required")
    if _is_system_admin(member):
        return
    tid = UUID(str(target_member_id))
    if member.memberId == tid:
        return
    target_companies_res = await db.execute(
        select(CompanyEmployee.companyId).where(
            CompanyEmployee.memberId == tid,
            CompanyEmployee.deletedAt.is_(None),
        )
    )
    target_cids = [row[0] for row in target_companies_res.all()]
    if not target_cids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this member")
    caller_admin_res = await db.execute(
        select(CompanyEmployee.companyRoleType).where(
            CompanyEmployee.memberId == member.memberId,
            CompanyEmployee.companyId.in_(target_cids),
            CompanyEmployee.deletedAt.is_(None),
        )
    )
    for (role,) in caller_admin_res.all():
        if rbac_service.is_legacy_company_admin(role):
            return
    for cid in target_cids:
        if await rbac_service.has_permission(
            db, member, rbac_service.PERM_EMPLOYEES_WRITE, cid
        ) or await rbac_service.has_any_elevated_company_access(db, member, cid):
            return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Company admin required for this member")


async def _member_in_company(db: AsyncSession, member_id: UUID, company_id: UUID) -> bool:
    row = await db.execute(
        select(CompanyEmployee.company_employeeId)
        .where(
            CompanyEmployee.memberId == member_id,
            CompanyEmployee.companyId == company_id,
            CompanyEmployee.deletedAt.is_(None),
        )
        .limit(1)
    )
    return row.first() is not None


async def assert_encoding_company_access(request, db: AsyncSession, face_encoding_id) -> None:
    """Bind a faceEncodingId to the caller's tenant.

    Resolution order:
    - encoding row exists and has ``companyId`` → caller must be admin of (or kiosk for)
      exactly that company; a ``companyId`` query param, when present, must match it;
    - encoding row exists without ``companyId`` (legacy, backfill unresolved) → fall back to
      the member→company check (``assert_member_company_access``);
    - encoding row does not exist locally (Face Core BFF mode) → the ``companyId`` query
      param is required and the caller must be admin of / kiosk for that company.

    There is deliberately no "admin of any company" fallback.
    """
    from ..models.face_encoding import FaceEncoding

    fid = UUID(str(face_encoding_id))
    cid_param_raw = request.query_params.get("companyId")
    cid_param: Optional[UUID] = UUID(str(cid_param_raw)) if cid_param_raw else None

    kiosk_cid = getattr(request.state, "kiosk_company_id", None) or current_kiosk_company_var.get()
    if kiosk_cid is not None:
        kiosk_cid = UUID(str(kiosk_cid))
        if cid_param is not None and cid_param != kiosk_cid:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Kiosk token forbidden for this encoding")
        enc = await db.get(FaceEncoding, fid)
        if enc is None:
            if cid_param is None:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Kiosk token forbidden for this encoding")
            return
        if enc.companyId is not None:
            if enc.companyId != kiosk_cid:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Kiosk token forbidden for this encoding")
            return
        if not await _member_in_company(db, enc.memberId, kiosk_cid):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Kiosk token forbidden for this encoding")
        return

    member = getattr(request.state, "member", None) or current_member_var.get()
    if member is None:
        from ..config.settings import settings

        if not settings.FACE_ROUTES_REQUIRE_JWT:
            return
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization required")
    if _is_system_admin(member):
        return

    enc = await db.get(FaceEncoding, fid)
    if enc is None:
        if cid_param is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Face encoding not found")
        await assert_company_access(db, member, cid_param)
        return
    if enc.companyId is not None:
        if cid_param is not None and cid_param != enc.companyId:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Face encoding belongs to a different company")
        await assert_company_access(db, member, enc.companyId)
        return
    if cid_param is not None:
        await assert_company_access(db, member, cid_param)
        if not await _member_in_company(db, enc.memberId, cid_param):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Face encoding belongs to a different company")
        return
    await assert_member_company_access(request, db, enc.memberId)


def require_request_system_admin(request) -> Member:
    """System-admin gate for handlers that read the member resolved by AuthzMiddleware."""
    member = getattr(request.state, "member", None) or current_member_var.get()
    if member is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization required")
    if not _is_system_admin(member):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="System admin required")
    return member


async def require_company_access(
    companyId: str,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
) -> Member:
    await assert_company_access(db, member, companyId)
    return member


def _path_uuid(request: Request, name: str) -> Optional[UUID]:
    raw = request.path_params.get(name) or request.query_params.get(name)
    if raw is None:
        return None
    try:
        return UUID(str(raw))
    except (TypeError, ValueError):
        return None


def require_permission(
    permission: str,
    *,
    company_param: str = "companyId",
    department_param: Optional[str] = None,
) -> Callable:
    """FastAPI dependency factory: enforce a D1 RBAC permission for the path company.

    Usage::

        @router.get("/company/{companyId}/…")
        async def handler(..., _: Member = Depends(require_permission("employees.read"))):
            ...
    """

    async def _dep(
        request: Request,
        member: Member = Depends(get_current_member),
        db: AsyncSession = Depends(get_db),
    ) -> Member:
        company_id = _path_uuid(request, company_param)
        department_id = _path_uuid(request, department_param) if department_param else None
        return await rbac_service.assert_permission(
            db,
            member,
            permission,
            company_id,
            department_id=department_id,
        )

    _dep.__name__ = f"require_permission_{permission.replace('.', '_')}"
    _dep.__doc__ = f"Requires permission `{permission}`."
    return _dep


async def assert_request_permission(
    request: Request,
    db: AsyncSession,
    permission: str,
    company_id,
    *,
    department_id=None,
) -> Optional[Member]:
    """Permission check for handlers that already resolve the member via AuthzMiddleware."""
    cid = UUID(str(company_id)) if company_id is not None else None
    dept = UUID(str(department_id)) if department_id is not None else None
    kiosk_cid = getattr(request.state, "kiosk_company_id", None) or current_kiosk_company_var.get()
    if kiosk_cid is not None:
        if cid is not None and UUID(str(kiosk_cid)) != cid:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Kiosk token scoped to a different company")
        return None
    member = getattr(request.state, "member", None) or current_member_var.get()
    return await rbac_service.assert_permission(
        db, member, permission, cid, department_id=dept
    )
