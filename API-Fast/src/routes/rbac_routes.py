"""BL-06 RBAC Management routes: roles, permission matrix, and branch/department-scoped assignments."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.database import get_db
from ..models.company_location import CompanyLocation
from ..models.department import Department
from ..models.member import Member
from ..models.rbac import MemberRoleAssignment, RbacRole, RbacRoleCode
from ..security.deps import assert_request_company_membership, get_current_member
from ..services import rbac_service

router = APIRouter()


class RoleAssignmentCreate(BaseModel):
    memberId: UUID
    roleCode: str
    departmentId: Optional[UUID] = None
    locationId: Optional[UUID] = None


_ROLE_LABELS: dict[str, str] = {
    RbacRoleCode.SYSTEM_ADMIN.value: "Super Admin",
    RbacRoleCode.HR_ADMIN.value: "Company Admin / HR",
    RbacRoleCode.MANAGER.value: "Line Manager",
    RbacRoleCode.APPROVER.value: "Approver",
    RbacRoleCode.AUDITOR.value: "Auditor",
    RbacRoleCode.DEVICE_OPERATOR.value: "Device Operator",
    RbacRoleCode.SECURITY_GUARD.value: "Security Guard",
    RbacRoleCode.EMPLOYEE.value: "Employee",
}


@router.get("/roles")
async def list_rbac_roles(
    _member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    db_roles = {
        r.code: r.description
        for r in (await db.execute(select(RbacRole))).scalars().all()
    }
    roles = []
    for code in RbacRoleCode:
        perms = sorted(rbac_service.ROLE_PERMISSIONS.get(code.value, frozenset()))
        roles.append(
            {
                "code": code.value,
                "label": _ROLE_LABELS.get(code.value, code.value),
                "description": db_roles.get(code.value) or _ROLE_LABELS.get(code.value, ""),
                "permissions": perms,
            }
        )
    return {
        "roles": roles,
        "permissions": list(rbac_service.ALL_PERMISSIONS),
    }


@router.get("/company/{companyId}/assignments")
async def list_company_role_assignments(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    caller = await assert_request_company_membership(request, db, companyId)
    await rbac_service.assert_permission(db, caller, rbac_service.PERM_COMPANY_SETTINGS, companyId)

    rows = (
        await db.execute(
            select(MemberRoleAssignment)
            .where(MemberRoleAssignment.companyId == companyId)
            .order_by(MemberRoleAssignment.createdAt.desc())
        )
    ).scalars().all()

    member_ids = list({r.memberId for r in rows})
    dept_ids = list({r.departmentId for r in rows if r.departmentId is not None})
    loc_ids = list({r.locationId for r in rows if getattr(r, "locationId", None) is not None})

    members = (
        {
            m.memberId: m
            for m in (
                await db.execute(
                    select(Member).where(
                        Member.memberId.in_(member_ids),
                        Member.deletedAt.is_(None),
                    )
                )
            ).scalars().all()
        }
        if member_ids
        else {}
    )
    depts = (
        {
            d.departmentId: (d.thName or d.engName or "")
            for d in (
                await db.execute(
                    select(Department).where(
                        Department.departmentId.in_(dept_ids),
                        Department.deletedAt.is_(None),
                    )
                )
            ).scalars().all()
        }
        if dept_ids
        else {}
    )
    locs = (
        {
            loc.locationId: loc.locationName
            for loc in (
                await db.execute(
                    select(CompanyLocation).where(
                        CompanyLocation.locationId.in_(loc_ids),
                        CompanyLocation.deletedAt.is_(None),
                    )
                )
            ).scalars().all()
        }
        if loc_ids
        else {}
    )

    items = []
    for r in rows:
        m = members.get(r.memberId)
        loc_id = getattr(r, "locationId", None)
        full_name = (
            f"{getattr(m, 'firstName', '') or ''} {getattr(m, 'lastName', '') or ''}".strip()
            if m
            else ""
        ) or (getattr(m, "username", "") if m else "")
        items.append(
            {
                "assignmentId": str(r.assignmentId),
                "memberId": str(r.memberId),
                "memberName": full_name,
                "memberEmail": getattr(m, "email", "") if m else "",
                "companyId": str(r.companyId) if r.companyId else None,
                "roleCode": r.roleCode,
                "roleLabel": _ROLE_LABELS.get(r.roleCode, r.roleCode),
                "departmentId": str(r.departmentId) if r.departmentId else None,
                "departmentName": depts.get(r.departmentId) if r.departmentId else None,
                "locationId": str(loc_id) if loc_id is not None else None,
                "locationName": locs.get(loc_id) if loc_id is not None else None,
                "createdAt": r.createdAt,
            }
        )
    return {"items": items, "total": len(items)}


@router.post("/company/{companyId}/assignments")
async def create_company_role_assignment(
    companyId: UUID,
    body: RoleAssignmentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    caller = await assert_request_company_membership(request, db, companyId)
    await rbac_service.assert_permission(db, caller, rbac_service.PERM_COMPANY_SETTINGS, companyId)

    role_code = body.roleCode.strip().upper()
    valid_codes = {c.value for c in RbacRoleCode}
    if role_code not in valid_codes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid roleCode")
    if role_code == RbacRoleCode.SYSTEM_ADMIN.value and not rbac_service.is_system_admin_member(caller):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system administrators can assign SYSTEM_ADMIN",
        )

    target_member = await db.get(Member, body.memberId)
    if target_member is None or target_member.deletedAt is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    if body.departmentId is not None:
        dept = await db.get(Department, body.departmentId)
        if dept is None or dept.companyId != companyId or dept.deletedAt is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    if body.locationId is not None:
        loc = await db.get(CompanyLocation, body.locationId)
        if loc is None or loc.companyId != companyId or loc.deletedAt is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location/Branch not found")

    # Ensure RbacRole row exists in case DB was initialized without running 0031 seed
    role_row = await db.get(RbacRole, role_code)
    if role_row is None:
        db.add(RbacRole(code=role_code, description=_ROLE_LABELS.get(role_code, role_code)))
        await db.flush()

    existing = (
        await db.execute(
            select(MemberRoleAssignment).where(
                MemberRoleAssignment.memberId == body.memberId,
                MemberRoleAssignment.companyId == companyId,
                MemberRoleAssignment.roleCode == role_code,
                MemberRoleAssignment.departmentId == body.departmentId,
                MemberRoleAssignment.locationId == body.locationId,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return {
            "assignmentId": str(existing.assignmentId),
            "memberId": str(existing.memberId),
            "companyId": str(existing.companyId),
            "roleCode": existing.roleCode,
            "departmentId": str(existing.departmentId) if existing.departmentId else None,
            "locationId": str(existing.locationId) if existing.locationId else None,
        }

    asg = MemberRoleAssignment(
        memberId=body.memberId,
        companyId=companyId,
        roleCode=role_code,
        departmentId=body.departmentId,
        locationId=body.locationId,
    )
    db.add(asg)
    await db.commit()
    await db.refresh(asg)
    return {
        "assignmentId": str(asg.assignmentId),
        "memberId": str(asg.memberId),
        "companyId": str(asg.companyId),
        "roleCode": asg.roleCode,
        "departmentId": str(asg.departmentId) if asg.departmentId else None,
        "locationId": str(asg.locationId) if asg.locationId else None,
    }


@router.delete("/company/{companyId}/assignments/{assignmentId}")
async def delete_company_role_assignment(
    companyId: UUID,
    assignmentId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    caller = await assert_request_company_membership(request, db, companyId)
    await rbac_service.assert_permission(db, caller, rbac_service.PERM_COMPANY_SETTINGS, companyId)

    asg = await db.get(MemberRoleAssignment, assignmentId)
    if asg is None or asg.companyId != companyId:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role assignment not found")

    await db.delete(asg)
    await db.commit()
    return {"status": "deleted", "assignmentId": str(assignmentId)}
