"""C4 thin approval gate (pre-D1 RBAC).

Approvers:
- ``RoleType.ADMIN_SYSTEM`` / ``RoleType.ADMIN_COMPANY``
- ``CompanyRoleType.ADMIN_COMPANY`` employment in the company
- manager-of: subject ``CompanyEmployee.bossId`` matches caller's memberId or company_employeeId
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.company_employee import CompanyEmployee, CompanyRoleType
from ..models.member import Member, RoleType


def _role_value(role) -> object:
    return getattr(role, "value", role)


def is_admin_role(member: Optional[Member]) -> bool:
    if member is None:
        return False
    role = member.role
    if role in (RoleType.ADMIN_SYSTEM, RoleType.ADMIN_COMPANY):
        return True
    val = _role_value(role)
    return val in (
        RoleType.ADMIN_SYSTEM.value,
        RoleType.ADMIN_COMPANY.value,
        99,
        1,
        "ADMIN_SYSTEM",
        "ADMIN_COMPANY",
    )


def is_company_admin_role(company_role) -> bool:
    if company_role == CompanyRoleType.ADMIN_COMPANY:
        return True
    val = _role_value(company_role)
    return val in (CompanyRoleType.ADMIN_COMPANY.value, 1, "ADMIN_COMPANY")


def boss_matches(subject: CompanyEmployee, caller: Member, caller_employment: Optional[CompanyEmployee]) -> bool:
    boss = (subject.bossId or "").strip()
    if not boss:
        return False
    if boss == str(caller.memberId):
        return True
    if caller_employment and boss == str(caller_employment.company_employeeId):
        return True
    return False


async def get_company_employment(
    db: AsyncSession,
    member_id: UUID,
    company_id: UUID,
) -> Optional[CompanyEmployee]:
    row = await db.execute(
        select(CompanyEmployee).where(
            CompanyEmployee.memberId == member_id,
            CompanyEmployee.companyId == company_id,
            CompanyEmployee.deletedAt.is_(None),
        )
    )
    return row.scalar_one_or_none()


async def assert_company_membership(
    db: AsyncSession,
    member: Optional[Member],
    company_id: UUID,
) -> Member:
    """Any active employment in the company (or system admin) — softer than assert_company_access."""
    if member is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization required")
    if is_admin_role(member) and _role_value(member.role) in (
        RoleType.ADMIN_SYSTEM.value,
        99,
        "ADMIN_SYSTEM",
    ):
        return member
    if member.role == RoleType.ADMIN_SYSTEM:
        return member
    emp = await get_company_employment(db, member.memberId, company_id)
    if emp is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this company")
    return member


async def can_approve_for_employee(
    db: AsyncSession,
    caller: Member,
    company_id: UUID,
    subject: CompanyEmployee,
) -> bool:
    if is_admin_role(caller) and (
        caller.role == RoleType.ADMIN_SYSTEM
        or _role_value(caller.role) in (RoleType.ADMIN_SYSTEM.value, 99, "ADMIN_SYSTEM")
    ):
        return True

    caller_emp = await get_company_employment(db, caller.memberId, company_id)
    if caller_emp is None:
        # Member.role ADMIN_COMPANY without employment row — still allow when global admin_company
        return is_admin_role(caller) and _role_value(caller.role) in (
            RoleType.ADMIN_COMPANY.value,
            1,
            "ADMIN_COMPANY",
        )

    if is_company_admin_role(caller_emp.companyRoleType):
        return True
    if is_admin_role(caller) and _role_value(caller.role) in (
        RoleType.ADMIN_COMPANY.value,
        1,
        "ADMIN_COMPANY",
    ):
        return True
    return boss_matches(subject, caller, caller_emp)


async def assert_can_approve_for_employee(
    db: AsyncSession,
    caller: Optional[Member],
    company_id: UUID,
    subject: CompanyEmployee,
) -> Member:
    if caller is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization required")
    if not await can_approve_for_employee(db, caller, company_id, subject):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not an approver for this employee",
        )
    return caller
