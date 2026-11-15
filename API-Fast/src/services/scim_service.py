"""RFC 7643/7644 SCIM 2.0 User Provisioning scoped per company."""
from __future__ import annotations

from datetime import datetime, timezone
import re
import secrets
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.company_employee import CompanyEmployee, CompanyRoleType, EmpType
from ..models.department import Department
from ..models.member import Member, RoleType, StatusType
from ..models.position import Position
from .pdpa_service import erase_member_personal_data

SCIM_USER_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:User"
SCIM_LIST_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:ListResponse"
SCIM_PATCH_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:PatchOp"

_FILTER_EQ_RE = re.compile(
    r'^\s*(userName|emails\.value|externalId)\s+eq\s+"([^"]+)"\s*$',
    re.IGNORECASE,
)


def service_provider_config() -> dict[str, Any]:
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"],
        "patch": {"supported": True},
        "bulk": {"supported": False, "maxOperations": 0, "maxPayloadSize": 0},
        "filter": {"supported": True, "maxResults": 200},
        "changePassword": {"supported": False},
        "sort": {"supported": False},
        "etag": {"supported": False},
        "authenticationSchemes": [
            {
                "type": "oauthbearertoken",
                "name": "OAuth Bearer Token / Tenant API Key",
                "description": "Bearer JWT or sv_ Tenant API Key with scim.write scope",
            }
        ],
    }


def serialize_scim_user(member: Member, emp: CompanyEmployee) -> dict[str, Any]:
    active = member.status == StatusType.ENABLE and member.deletedAt is None and emp.deletedAt is None
    full_name = f"{member.firstName or ''} {member.lastName or ''}".strip() or member.username
    return {
        "schemas": [SCIM_USER_SCHEMA],
        "id": str(member.memberId),
        "externalId": emp.employeeId or str(member.memberId),
        "userName": member.username,
        "name": {
            "formatted": full_name,
            "givenName": member.firstName or "",
            "familyName": member.lastName or "",
        },
        "emails": [{"value": member.email, "type": "work", "primary": True}] if member.email else [],
        "active": active,
        "meta": {
            "resourceType": "User",
            "created": member.createdAt.isoformat() if member.createdAt else None,
            "lastModified": member.updatedAt.isoformat() if member.updatedAt else None,
        },
    }


async def _resolve_default_org(
    db: AsyncSession,
    company_id: UUID,
    department_id: Optional[str] = None,
    position_id: Optional[str] = None,
) -> tuple[UUID, UUID]:
    dept_uuid: Optional[UUID] = UUID(str(department_id)) if department_id else None
    pos_uuid: Optional[UUID] = UUID(str(position_id)) if position_id else None

    if dept_uuid is not None:
        dept = await db.get(Department, dept_uuid)
        if not dept or dept.companyId != company_id or dept.deletedAt is not None:
            raise HTTPException(status_code=400, detail="Invalid departmentId for company")
    else:
        dept = (
            await db.execute(
                select(Department)
                .where(Department.companyId == company_id, Department.deletedAt.is_(None))
                .order_by(Department.createdAt.asc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if dept is None:
            raise HTTPException(
                status_code=400,
                detail="Company has no active department for SCIM provisioning",
            )
        dept_uuid = dept.departmentId

    if pos_uuid is not None:
        pos = await db.get(Position, pos_uuid)
        if not pos or pos.companyId != company_id or pos.deletedAt is not None:
            raise HTTPException(status_code=400, detail="Invalid positionId for company")
    else:
        pos = (
            await db.execute(
                select(Position)
                .where(Position.companyId == company_id, Position.deletedAt.is_(None))
                .order_by(Position.createdAt.asc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if pos is None:
            raise HTTPException(
                status_code=400,
                detail="Company has no active position for SCIM provisioning",
            )
        pos_uuid = pos.positionId

    return dept_uuid, pos_uuid


async def list_scim_users(
    db: AsyncSession,
    company_id: UUID,
    *,
    start_index: int = 1,
    count: int = 50,
    filter_str: Optional[str] = None,
) -> dict[str, Any]:
    offset = max(0, int(start_index) - 1)
    limit = max(1, min(int(count), 200))

    base = (
        select(Member, CompanyEmployee)
        .join(CompanyEmployee, CompanyEmployee.memberId == Member.memberId)
        .where(
            CompanyEmployee.companyId == company_id,
            CompanyEmployee.deletedAt.is_(None),
            Member.deletedAt.is_(None),
        )
    )
    if filter_str:
        m = _FILTER_EQ_RE.match(filter_str)
        if not m:
            raise HTTPException(status_code=400, detail="Unsupported SCIM filter syntax")
        attr, val = m.group(1).lower(), m.group(2).strip()
        if attr == "username":
            base = base.where(Member.username == val)
        elif attr == "emails.value":
            base = base.where(Member.email == val)
        elif attr == "externalid":
            base = base.where(CompanyEmployee.employeeId == val)

    total = int(
        (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
    )
    rows = (
        await db.execute(base.order_by(Member.createdAt.asc()).offset(offset).limit(limit))
    ).all()

    return {
        "schemas": [SCIM_LIST_SCHEMA],
        "totalResults": total,
        "startIndex": offset + 1,
        "itemsPerPage": len(rows),
        "Resources": [serialize_scim_user(member, emp) for member, emp in rows],
    }


async def get_scim_user(db: AsyncSession, company_id: UUID, member_id: UUID) -> dict[str, Any]:
    row = (
        await db.execute(
            select(Member, CompanyEmployee)
            .join(CompanyEmployee, CompanyEmployee.memberId == Member.memberId)
            .where(
                CompanyEmployee.companyId == company_id,
                CompanyEmployee.deletedAt.is_(None),
                Member.memberId == member_id,
                Member.deletedAt.is_(None),
            )
            .limit(1)
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="SCIM user not found")
    member, emp = row
    return serialize_scim_user(member, emp)


async def create_scim_user(
    db: AsyncSession,
    company_id: UUID,
    payload: dict[str, Any],
) -> dict[str, Any]:
    username = str(payload.get("userName") or "").strip()
    emails = payload.get("emails") or []
    primary_email = ""
    if isinstance(emails, list) and emails:
        first_email = emails[0]
        if isinstance(first_email, dict):
            primary_email = str(first_email.get("value") or "").strip()
    email = primary_email or (username if "@" in username else f"{username}@scim.local")
    if not username:
        raise HTTPException(status_code=400, detail="userName is required")

    dup = (
        await db.execute(
            select(Member)
            .where(
                Member.deletedAt.is_(None),
                or_(Member.username == username, Member.email == email),
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if dup is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="SCIM user already exists")

    dept_id, pos_id = await _resolve_default_org(
        db,
        company_id,
        department_id=payload.get("departmentId"),
        position_id=payload.get("positionId"),
    )
    raw_name = payload.get("name")
    name_obj: dict[str, Any] = raw_name if isinstance(raw_name, dict) else {}
    active = bool(payload.get("active", True))

    member = Member(
        username=username,
        email=email,
        firstName=str(name_obj.get("givenName") or "").strip() or None,
        lastName=str(name_obj.get("familyName") or "").strip() or None,
        role=RoleType.MEMBER,
        status=StatusType.ENABLE if active else StatusType.DISABLED,
        mustChangePassword=True,
    )
    member.hash_password(secrets.token_urlsafe(24))
    db.add(member)
    await db.flush()

    emp = CompanyEmployee(
        memberId=member.memberId,
        companyId=company_id,
        departmentId=dept_id,
        positionId=pos_id,
        employeeId=str(payload.get("externalId") or "").strip() or "",
        empType=EmpType.PERMONTH,
        companyRoleType=CompanyRoleType.EMP,
        salary=0.0,
    )
    db.add(emp)
    await db.commit()
    await db.refresh(member)
    await db.refresh(emp)
    return serialize_scim_user(member, emp)


async def patch_scim_user(
    db: AsyncSession,
    company_id: UUID,
    member_id: UUID,
    payload: dict[str, Any],
) -> dict[str, Any]:
    row = (
        await db.execute(
            select(Member, CompanyEmployee)
            .join(CompanyEmployee, CompanyEmployee.memberId == Member.memberId)
            .where(
                CompanyEmployee.companyId == company_id,
                CompanyEmployee.deletedAt.is_(None),
                Member.memberId == member_id,
                Member.deletedAt.is_(None),
            )
            .limit(1)
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="SCIM user not found")
    member, emp = row

    ops = payload.get("Operations") or []
    if not isinstance(ops, list):
        raise HTTPException(status_code=400, detail="Operations must be a list")

    for op in ops:
        if not isinstance(op, dict):
            continue
        op_type = str(op.get("op") or "replace").strip().lower()
        if op_type not in {"replace", "add"}:
            continue
        path = str(op.get("path") or "").strip().lower()
        val = op.get("value")
        if path == "active":
            member.status = StatusType.ENABLE if bool(val) else StatusType.DISABLED
        elif not path and isinstance(val, dict) and "active" in val:
            member.status = StatusType.ENABLE if bool(val["active"]) else StatusType.DISABLED
        if path == "name.givenname" and isinstance(val, str):
            member.firstName = val.strip() or None
        elif path == "name.familyname" and isinstance(val, str):
            member.lastName = val.strip() or None
        elif path == "externalid" and isinstance(val, str):
            emp.employeeId = val.strip()
        elif not path and isinstance(val, dict):
            if isinstance(val.get("name"), dict):
                if "givenName" in val["name"]:
                    member.firstName = str(val["name"]["givenName"] or "").strip() or None
                if "familyName" in val["name"]:
                    member.lastName = str(val["name"]["familyName"] or "").strip() or None
            if "externalId" in val:
                emp.employeeId = str(val["externalId"] or "").strip()

    await db.commit()
    await db.refresh(member)
    await db.refresh(emp)
    return serialize_scim_user(member, emp)


async def delete_scim_user(db: AsyncSession, company_id: UUID, member_id: UUID) -> dict[str, Any]:
    row = (
        await db.execute(
            select(Member, CompanyEmployee)
            .join(CompanyEmployee, CompanyEmployee.memberId == Member.memberId)
            .where(
                CompanyEmployee.companyId == company_id,
                CompanyEmployee.deletedAt.is_(None),
                Member.memberId == member_id,
                Member.deletedAt.is_(None),
            )
            .limit(1)
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="SCIM user not found")
    member, emp = row

    now = datetime.now(timezone.utc)
    emp.deletedAt = now
    await erase_member_personal_data(db, company_id, member_id, clear_consent=True)

    other_active = (
        await db.execute(
            select(func.count())
            .select_from(CompanyEmployee)
            .where(
                CompanyEmployee.memberId == member_id,
                CompanyEmployee.companyId != company_id,
                CompanyEmployee.deletedAt.is_(None),
            )
        )
    ).scalar() or 0
    if int(other_active) == 0:
        member.status = StatusType.DISABLED
        member.deletedAt = now

    await db.commit()
    return {"deleted": True, "id": str(member_id)}
