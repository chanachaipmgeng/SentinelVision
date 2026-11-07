"""Request auth dependencies, company tenancy checks, and Kiosk device token validation."""
from __future__ import annotations

from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.database import get_db
from ..models.company_employee import CompanyEmployee, CompanyRoleType
from ..models.hr_schedule import KioskDevice
from ..models.member import Member, RoleType
from .jwt import decode_token, hash_kiosk_token

_bearer = HTTPBearer(auto_error=False)
current_member_var: ContextVar[Optional[Member]] = ContextVar("current_member", default=None)
current_kiosk_company_var: ContextVar[Optional[UUID]] = ContextVar("current_kiosk_company", default=None)


def _is_system_admin(member: Member) -> bool:
    role = member.role
    if role == RoleType.ADMIN_SYSTEM:
        return True
    value = getattr(role, "value", role)
    return value == 99 or value == RoleType.ADMIN_SYSTEM.value


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
    result = await db.execute(
        select(CompanyEmployee.companyRoleType).where(
            CompanyEmployee.memberId == member.memberId,
            CompanyEmployee.companyId == cid,
            CompanyEmployee.deletedAt.is_(None),
        )
    )
    role = result.scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this company")
    role_val = getattr(role, "value", role)
    if role != CompanyRoleType.ADMIN_COMPANY and role_val not in (1, "ADMIN_COMPANY"):
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
        role_val = getattr(role, "value", role)
        if role == CompanyRoleType.ADMIN_COMPANY or role_val in (1, "ADMIN_COMPANY"):
            return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Company admin required for this member")


async def assert_encoding_company_access(request, db: AsyncSession, face_encoding_id) -> None:
    """Ensure caller has company admin or kiosk access to the owner of face_encoding_id."""
    kiosk_cid = getattr(request.state, "kiosk_company_id", None) or current_kiosk_company_var.get()
    if kiosk_cid is not None:
        cid_param = request.query_params.get("companyId")
        if cid_param and UUID(str(cid_param)) == UUID(str(kiosk_cid)):
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Kiosk token forbidden for this encoding")
    member = getattr(request.state, "member", None) or current_member_var.get()
    if member is None:
        from ..config.settings import settings

        if not settings.FACE_ROUTES_REQUIRE_JWT:
            return
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization required")
    if _is_system_admin(member):
        return
    from ..models.face_encoding import FaceEncoding

    fid = UUID(str(face_encoding_id))
    enc = await db.get(FaceEncoding, fid)
    if enc is not None:
        await assert_member_company_access(request, db, enc.memberId)
        return
    cid_param = request.query_params.get("companyId")
    if cid_param:
        await assert_company_access(db, member, cid_param)
        return
    caller_admin_res = await db.execute(
        select(CompanyEmployee.companyRoleType).where(
            CompanyEmployee.memberId == member.memberId,
            CompanyEmployee.deletedAt.is_(None),
        )
    )
    for (role,) in caller_admin_res.all():
        role_val = getattr(role, "value", role)
        if role == CompanyRoleType.ADMIN_COMPANY or role_val in (1, "ADMIN_COMPANY"):
            return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Company admin required")


async def require_company_access(
    companyId: str,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
) -> Member:
    await assert_company_access(db, member, companyId)
    return member
