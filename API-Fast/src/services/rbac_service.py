"""Phase D1 RBAC: permission resolution, role matrix, department scope.

Legacy bridges:
- ``RoleType.ADMIN_SYSTEM`` → all permissions (SYSTEM_ADMIN)
- ``CompanyRoleType.ADMIN_COMPANY`` employment → all company permissions (maps to HR_ADMIN set)
- Direct-report boss relation still satisfies approve checks when the caller holds
  ``attendance.approve`` / ``hr.approve`` *or* is the subject's boss (C4 manager-of).
"""
from __future__ import annotations

from typing import Iterable, Optional, Sequence
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.company_employee import CompanyEmployee, CompanyRoleType
from ..models.member import Member, RoleType
from ..models.rbac import MemberRoleAssignment, RbacRoleCode, RbacRolePermission

# Stable permission codes seeded by 0014_rbac.
PERM_COMPANY_READ = "company.read"
PERM_COMPANY_SETTINGS = "company.settings"
PERM_EMPLOYEES_READ = "employees.read"
PERM_EMPLOYEES_WRITE = "employees.write"
PERM_DEPARTMENTS_READ = "departments.read"
PERM_DEPARTMENTS_WRITE = "departments.write"
PERM_POSITIONS_READ = "positions.read"
PERM_POSITIONS_WRITE = "positions.write"
PERM_ATTENDANCE_READ = "attendance.read"
PERM_ATTENDANCE_WRITE = "attendance.write"
PERM_ATTENDANCE_APPROVE = "attendance.approve"
PERM_ATTENDANCE_EXPORT = "attendance.export"
PERM_HR_SHIFTS = "hr.shifts"
PERM_HR_LEAVES = "hr.leaves"
PERM_HR_HOLIDAYS = "hr.holidays"
PERM_HR_APPROVE = "hr.approve"
PERM_DEVICES_MANAGE = "devices.manage"
PERM_NOTIFICATIONS_MANAGE = "notifications.manage"
PERM_AUDIT_READ = "audit.read"
PERM_PAYROLL_EXPORT = "payroll.export"
PERM_SENTINEL_MANAGE = "sentinel.manage"
PERM_CAMERAS_READ = "cameras.read"
PERM_CAMERAS_MANAGE = "cameras.manage"
PERM_SYSTEM_ADMIN = "system.admin"

ALL_PERMISSIONS: tuple[str, ...] = (
    PERM_COMPANY_READ,
    PERM_COMPANY_SETTINGS,
    PERM_EMPLOYEES_READ,
    PERM_EMPLOYEES_WRITE,
    PERM_DEPARTMENTS_READ,
    PERM_DEPARTMENTS_WRITE,
    PERM_POSITIONS_READ,
    PERM_POSITIONS_WRITE,
    PERM_ATTENDANCE_READ,
    PERM_ATTENDANCE_WRITE,
    PERM_ATTENDANCE_APPROVE,
    PERM_ATTENDANCE_EXPORT,
    PERM_HR_SHIFTS,
    PERM_HR_LEAVES,
    PERM_HR_HOLIDAYS,
    PERM_HR_APPROVE,
    PERM_DEVICES_MANAGE,
    PERM_NOTIFICATIONS_MANAGE,
    PERM_AUDIT_READ,
    PERM_PAYROLL_EXPORT,
    PERM_SENTINEL_MANAGE,
    PERM_CAMERAS_READ,
    PERM_CAMERAS_MANAGE,
    PERM_SYSTEM_ADMIN,
)

# Company-scoped permissions granted to legacy ADMIN_COMPANY / HR_ADMIN.
COMPANY_ADMIN_PERMISSIONS: frozenset[str] = frozenset(
    p for p in ALL_PERMISSIONS if p != PERM_SYSTEM_ADMIN
)

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    RbacRoleCode.SYSTEM_ADMIN.value: frozenset(ALL_PERMISSIONS),
    RbacRoleCode.HR_ADMIN.value: COMPANY_ADMIN_PERMISSIONS,
    RbacRoleCode.MANAGER.value: frozenset(
        {
            PERM_COMPANY_READ,
            PERM_EMPLOYEES_READ,
            PERM_DEPARTMENTS_READ,
            PERM_ATTENDANCE_READ,
            PERM_ATTENDANCE_APPROVE,
            PERM_HR_LEAVES,
            PERM_HR_APPROVE,
        }
    ),
    RbacRoleCode.APPROVER.value: frozenset(
        {
            PERM_COMPANY_READ,
            PERM_ATTENDANCE_READ,
            PERM_ATTENDANCE_APPROVE,
            PERM_HR_APPROVE,
        }
    ),
    RbacRoleCode.AUDITOR.value: frozenset(
        {
            PERM_COMPANY_READ,
            PERM_EMPLOYEES_READ,
            PERM_DEPARTMENTS_READ,
            PERM_POSITIONS_READ,
            PERM_ATTENDANCE_READ,
            PERM_ATTENDANCE_EXPORT,
            PERM_HR_SHIFTS,
            PERM_HR_LEAVES,
            PERM_HR_HOLIDAYS,
            PERM_AUDIT_READ,
            PERM_PAYROLL_EXPORT,
            PERM_CAMERAS_READ,
        }
    ),
    RbacRoleCode.DEVICE_OPERATOR.value: frozenset(
        {
            PERM_COMPANY_READ,
            PERM_DEVICES_MANAGE,
            PERM_ATTENDANCE_READ,
            PERM_CAMERAS_READ,
        }
    ),
}


def _role_value(role) -> object:
    return getattr(role, "value", role)


def is_system_admin_member(member: Optional[Member]) -> bool:
    if member is None:
        return False
    role = member.role
    if role == RoleType.ADMIN_SYSTEM:
        return True
    val = _role_value(role)
    return val in (RoleType.ADMIN_SYSTEM.value, 99, "ADMIN_SYSTEM")


def is_legacy_company_admin(company_role) -> bool:
    if company_role == CompanyRoleType.ADMIN_COMPANY:
        return True
    val = _role_value(company_role)
    return val in (CompanyRoleType.ADMIN_COMPANY.value, 1, "ADMIN_COMPANY")


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


async def list_role_assignments(
    db: AsyncSession,
    member_id: UUID,
    company_id: Optional[UUID] = None,
) -> Sequence[MemberRoleAssignment]:
    stmt = select(MemberRoleAssignment).where(MemberRoleAssignment.memberId == member_id)
    if company_id is not None:
        stmt = stmt.where(
            (MemberRoleAssignment.companyId == company_id)
            | (MemberRoleAssignment.roleCode == RbacRoleCode.SYSTEM_ADMIN.value)
        )
    return (await db.execute(stmt)).scalars().all()


async def permissions_for_member(
    db: AsyncSession,
    member: Member,
    company_id: Optional[UUID] = None,
    *,
    department_id: Optional[UUID] = None,
) -> set[str]:
    """Resolve effective permission codes for a member in an optional company scope."""
    if is_system_admin_member(member):
        return set(ALL_PERMISSIONS)

    perms: set[str] = set()

    if company_id is not None:
        emp = await get_company_employment(db, member.memberId, company_id)
        if emp is not None and is_legacy_company_admin(emp.companyRoleType):
            perms |= set(COMPANY_ADMIN_PERMISSIONS)
        # Member.role ADMIN_COMPANY without employment row (rare legacy)
        if emp is None and _role_value(member.role) in (
            RoleType.ADMIN_COMPANY.value,
            1,
            "ADMIN_COMPANY",
        ):
            perms |= set(COMPANY_ADMIN_PERMISSIONS)

    assignments = await list_role_assignments(db, member.memberId, company_id)
    for asg in assignments:
        role_code = asg.roleCode
        role_perms = ROLE_PERMISSIONS.get(role_code)
        if role_perms is None:
            # Fall back to DB join if role matrix was extended outside code.
            rows = await db.execute(
                select(RbacRolePermission.permissionCode).where(
                    RbacRolePermission.roleCode == role_code
                )
            )
            role_perms = frozenset(r[0] for r in rows.all())
        if asg.departmentId is not None:
            # Department-scoped assignment only applies when the resource department matches
            # (or when no department filter was requested — then include for nav/listing).
            if department_id is not None and asg.departmentId != department_id:
                continue
        perms |= set(role_perms)
    return perms


async def has_permission(
    db: AsyncSession,
    member: Member,
    permission: str,
    company_id: Optional[UUID] = None,
    *,
    department_id: Optional[UUID] = None,
) -> bool:
    perms = await permissions_for_member(
        db, member, company_id, department_id=department_id
    )
    return permission in perms


async def has_any_elevated_company_access(
    db: AsyncSession,
    member: Member,
    company_id: UUID,
) -> bool:
    """True when the member is more than a plain EMP for this company (legacy admin or any RBAC role)."""
    if is_system_admin_member(member):
        return True
    emp = await get_company_employment(db, member.memberId, company_id)
    if emp is not None and is_legacy_company_admin(emp.companyRoleType):
        return True
    assignments = await list_role_assignments(db, member.memberId, company_id)
    return any(a.companyId == company_id for a in assignments)


async def assert_permission(
    db: AsyncSession,
    member: Optional[Member],
    permission: str,
    company_id: Optional[UUID] = None,
    *,
    department_id: Optional[UUID] = None,
) -> Member:
    if member is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization required")
    if await has_permission(db, member, permission, company_id, department_id=department_id):
        return member
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Missing permission: {permission}",
    )


async def roles_for_member(
    db: AsyncSession,
    member: Member,
    company_id: Optional[UUID] = None,
) -> list[dict]:
    """Server-driven role list for the frontend (never trust localStorage)."""
    out: list[dict] = []
    if is_system_admin_member(member):
        out.append(
            {
                "role": RbacRoleCode.SYSTEM_ADMIN.value,
                "companyId": None,
                "departmentId": None,
                "source": "member.role",
            }
        )
    if company_id is not None:
        emp = await get_company_employment(db, member.memberId, company_id)
        if emp is not None and is_legacy_company_admin(emp.companyRoleType):
            out.append(
                {
                    "role": RbacRoleCode.HR_ADMIN.value,
                    "companyId": str(company_id),
                    "departmentId": None,
                    "source": "company_employee.ADMIN_COMPANY",
                }
            )
    for asg in await list_role_assignments(db, member.memberId, company_id):
        if company_id is not None and asg.companyId not in (None, company_id):
            continue
        out.append(
            {
                "role": asg.roleCode,
                "companyId": str(asg.companyId) if asg.companyId else None,
                "departmentId": str(asg.departmentId) if asg.departmentId else None,
                "source": "member_role_assignment",
            }
        )
    return out


def boss_matches(
    subject: CompanyEmployee,
    caller: Member,
    caller_employment: Optional[CompanyEmployee],
) -> bool:
    boss = (subject.bossId or "").strip()
    if not boss:
        return False
    if boss == str(caller.memberId):
        return True
    if caller_employment and boss == str(caller_employment.company_employeeId):
        return True
    return False


async def can_approve_for_employee(
    db: AsyncSession,
    caller: Member,
    company_id: UUID,
    subject: CompanyEmployee,
) -> bool:
    """Approve gate: RBAC approve permission (honouring department scope) or direct boss."""
    if is_system_admin_member(caller):
        return True

    dept_id = subject.departmentId
    if await has_permission(
        db, caller, PERM_ATTENDANCE_APPROVE, company_id, department_id=dept_id
    ) or await has_permission(
        db, caller, PERM_HR_APPROVE, company_id, department_id=dept_id
    ):
        # Department-scoped managers: only if assignment covers subject's dept or is company-wide.
        # has_permission already filters by department_id against assignments.
        return True

    caller_emp = await get_company_employment(db, caller.memberId, company_id)
    if boss_matches(subject, caller, caller_emp):
        return True
    return False


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


def permission_codes_for_roles(role_codes: Iterable[str]) -> set[str]:
    out: set[str] = set()
    for code in role_codes:
        out |= set(ROLE_PERMISSIONS.get(code, frozenset()))
    return out
