"""Request auth dependencies and company tenancy checks."""
from __future__ import annotations

from contextvars import ContextVar
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.database import get_db
from ..models.company_employee import CompanyEmployee, CompanyRoleType
from ..models.member import Member, RoleType
from .jwt import decode_token

_bearer = HTTPBearer(auto_error=False)
current_member_var: ContextVar[Optional[Member]] = ContextVar("current_member", default=None)


def _is_system_admin(member: Member) -> bool:
    role = member.role
    if role == RoleType.ADMIN_SYSTEM:
        return True
    value = getattr(role, "value", role)
    return value == 99 or value == RoleType.ADMIN_SYSTEM.value


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


async def assert_company_access(db: AsyncSession, member: Member, company_id) -> None:
    if member is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization required")
    if _is_system_admin(member):
        return
    cid = UUID(str(company_id))
    result = await db.execute(
        select(CompanyEmployee.companyRoleType).where(
            CompanyEmployee.memberId == member.memberId,
            CompanyEmployee.companyId == cid,
        )
    )
    role = result.scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this company")
    role_val = getattr(role, "value", role)
    if role != CompanyRoleType.ADMIN_COMPANY and role_val not in (1, "ADMIN_COMPANY"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Company admin required")


async def assert_request_company_access(request, db: AsyncSession, company_id) -> None:
    """Bind a companyId taken from a form/body to the member resolved by AuthzMiddleware."""
    member = getattr(request.state, "member", None) or current_member_var.get()
    if member is None:
        from ..config.settings import settings

        if not settings.FACE_ROUTES_REQUIRE_JWT:
            return
    await assert_company_access(db, member, company_id)


async def require_company_access(
    companyId: str,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
) -> Member:
    await assert_company_access(db, member, companyId)
    return member
