"""Per-company SSO policy (stored in system_setting as ``sso:{companyId}``) and JIT provisioning.

JIT provisioning is OFF by default: an IdP identity whose email does not map to an
existing, active Member is rejected unless the company that started the login
explicitly enabled ``jitProvisioning`` and configured the default department /
position the new employee is attached to.
"""
from __future__ import annotations

import secrets
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.company import Company
from ..models.company_employee import CompanyEmployee, CompanyRoleType
from ..models.department import Department
from ..models.member import Member, RoleType, StatusType
from ..models.position import Position
from ..models.system_setting import SystemSetting
from ..security.passwords import hash_password

DEFAULT_SSO_POLICY: dict[str, Any] = {
    "jitProvisioning": False,
    "allowedEmailDomains": [],
    "defaultDepartmentId": None,
    "defaultPositionId": None,
}


def sso_policy_key(company_id: str | UUID) -> str:
    return f"sso:{company_id}"


def _clean_uuid(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    try:
        return str(UUID(str(value)))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID in SSO policy") from None


def normalize_sso_policy(payload: dict) -> dict:
    domains_raw = payload.get("allowedEmailDomains") or []
    if isinstance(domains_raw, str):
        domains_raw = domains_raw.split(",")
    domains = sorted({d.strip().lower().lstrip("@") for d in domains_raw if str(d).strip()})
    return {
        "jitProvisioning": bool(payload.get("jitProvisioning", False)),
        "allowedEmailDomains": domains,
        "defaultDepartmentId": _clean_uuid(payload.get("defaultDepartmentId")),
        "defaultPositionId": _clean_uuid(payload.get("defaultPositionId")),
    }


async def get_sso_policy(db: AsyncSession, company_id: str | UUID) -> dict:
    row = await db.get(SystemSetting, sso_policy_key(company_id))
    if row and isinstance(row.value, dict):
        return {**DEFAULT_SSO_POLICY, **row.value}
    return dict(DEFAULT_SSO_POLICY)


async def save_sso_policy(db: AsyncSession, company_id: str | UUID, payload: dict) -> dict:
    cid = UUID(str(company_id))
    clean = normalize_sso_policy(payload)
    if clean["jitProvisioning"]:
        if not clean["defaultDepartmentId"] or not clean["defaultPositionId"]:
            raise HTTPException(
                status_code=400,
                detail="jitProvisioning requires defaultDepartmentId and defaultPositionId",
            )
        dept = await db.get(Department, UUID(clean["defaultDepartmentId"]))
        if dept is None or dept.companyId != cid or dept.deletedAt is not None:
            raise HTTPException(status_code=400, detail="defaultDepartmentId does not belong to this company")
        pos = await db.get(Position, UUID(clean["defaultPositionId"]))
        if pos is None or pos.companyId != cid or pos.deletedAt is not None:
            raise HTTPException(status_code=400, detail="defaultPositionId does not belong to this company")
    key = sso_policy_key(cid)
    row = await db.get(SystemSetting, key)
    if row:
        row.value = clean
    else:
        db.add(SystemSetting(key=key, value=clean))
    await db.commit()
    return clean


def email_domain_allowed(email: str, policy: dict) -> bool:
    domains = policy.get("allowedEmailDomains") or []
    if not domains:
        return True
    domain = email.rsplit("@", 1)[-1].lower()
    return domain in domains


async def _unique_username(db: AsyncSession, preferred: str, email: str) -> str:
    base = (preferred or email.split("@", 1)[0] or "sso-user").strip()[:60]
    candidate = base
    for _ in range(5):
        exists = await db.execute(select(Member.memberId).where(Member.username == candidate))
        if exists.scalar_one_or_none() is None:
            return candidate
        candidate = f"{base}-{secrets.token_hex(3)}"
    return f"{base}-{secrets.token_hex(6)}"


async def jit_provision_member(
    db: AsyncSession,
    *,
    claims: dict,
    email: str,
    company_id: Optional[str],
) -> Member:
    """Create Member + CompanyEmployee for a verified IdP identity, or raise.

    The caller has already established there is no Member with this email.
    """
    if not company_id:
        raise HTTPException(status_code=404, detail="No active member linked to this SSO email")
    cid = UUID(str(company_id))
    company = await db.get(Company, cid)
    if company is None or getattr(company, "deletedAt", None) is not None:
        raise HTTPException(status_code=404, detail="No active member linked to this SSO email")
    policy = await get_sso_policy(db, cid)
    if not policy.get("jitProvisioning"):
        raise HTTPException(status_code=404, detail="No active member linked to this SSO email")
    if not email_domain_allowed(email, policy):
        raise HTTPException(status_code=403, detail="SSO email domain is not allowed for this company")
    dept_id = policy.get("defaultDepartmentId")
    pos_id = policy.get("defaultPositionId")
    if not dept_id or not pos_id:
        raise HTTPException(status_code=409, detail="SSO JIT provisioning is missing default department/position")

    member = Member(
        username=await _unique_username(db, claims.get("preferred_username") or "", email),
        email=email,
        firstName=(claims.get("given_name") or claims.get("name") or "").strip() or None,
        lastName=(claims.get("family_name") or "").strip() or None,
        role=RoleType.MEMBER,
        status=StatusType.ENABLE,
        mustChangePassword=False,
    )
    # SSO users never use a local password; store an unguessable random hash.
    member.passwordHash = hash_password(secrets.token_urlsafe(32))
    db.add(member)
    await db.flush()
    db.add(
        CompanyEmployee(
            memberId=member.memberId,
            companyId=cid,
            departmentId=UUID(str(dept_id)),
            positionId=UUID(str(pos_id)),
            companyRoleType=CompanyRoleType.EMP,
            employeeId=str(claims.get("sub") or "")[:100],
        )
    )
    await db.commit()
    await db.refresh(member)
    return member
