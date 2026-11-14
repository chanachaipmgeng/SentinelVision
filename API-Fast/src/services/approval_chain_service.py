"""BL-07 Multi-level approval chain & delegate approver service."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.approvals_payroll import ApprovalPolicy
from ..models.company_employee import CompanyEmployee
from ..models.member import Member
from .rbac_service import resolve_delegator_for_approval

DEFAULT_LEVELS: list[dict[str, Any]] = [
    {"level": 1, "role": "MANAGER", "label": "Line Manager"},
]

STANDARD_MULTI_LEVELS: list[dict[str, Any]] = [
    {"level": 1, "role": "MANAGER", "label": "Line Manager"},
    {"level": 2, "role": "MANAGER", "label": "Department Manager"},
    {"level": 3, "role": "HR_ADMIN", "label": "HR Final"},
]


async def get_company_approval_levels(
    db: AsyncSession,
    company_id: UUID,
    request_type: str = "ALL",
) -> list[dict[str, Any]]:
    """Return configured approval levels for (company_id, request_type) or fallback to ALL / 1-level."""
    rt = (request_type or "ALL").upper()
    rows = (
        await db.execute(
            select(ApprovalPolicy).where(
                ApprovalPolicy.companyId == company_id,
                ApprovalPolicy.isActive.is_(True),
                ApprovalPolicy.requestType.in_([rt, "ALL"]),
            )
        )
    ).scalars().all()

    chosen: Optional[ApprovalPolicy] = None
    for r in rows:
        if r.requestType == rt:
            chosen = r
            break
        if r.requestType == "ALL":
            chosen = r

    if chosen and isinstance(chosen.levels, list) and len(chosen.levels) > 0:
        return [dict(lvl) for lvl in chosen.levels]
    return [dict(lvl) for lvl in DEFAULT_LEVELS]


def level_label_for(levels: list[dict[str, Any]], level_num: int) -> str:
    for lvl in levels:
        if int(lvl.get("level") or 0) == int(level_num):
            return str(lvl.get("label") or f"Level {level_num}")
    return f"Level {level_num}"


async def advance_approval_step(
    db: AsyncSession,
    row: Any,
    company_id: UUID,
    subject: CompanyEmployee,
    caller: Optional[Member],
    approve: bool,
    reject_reason: Optional[str],
    request_type: str,
) -> bool:
    """Advance one step in the multi-level approval chain.

    Returns True when the request reaches final APPROVED state; False if rejected or
    advancing to the next pending level.
    """
    now = datetime.now(timezone.utc)
    current_level = int(getattr(row, "approvalLevel", 1) or 1)
    max_level = int(getattr(row, "maxApprovalLevel", 1) or 1)
    levels = await get_company_approval_levels(db, company_id, request_type)
    role_label = level_label_for(levels, current_level)

    delegator_id: Optional[UUID] = None
    caller_name = ""
    if caller is not None:
        caller_name = (
            f"{getattr(caller, 'firstName', '') or ''} {getattr(caller, 'lastName', '') or ''}".strip()
            or getattr(caller, "username", "")
            or ""
        )
        delegator_id = await resolve_delegator_for_approval(db, caller, company_id, subject)

    history = list(getattr(row, "approvalHistory", None) or [])
    history.append(
        {
            "level": current_level,
            "roleLabel": role_label,
            "approverMemberId": str(caller.memberId) if caller else None,
            "approverName": caller_name,
            "delegatedFromMemberId": str(delegator_id) if delegator_id else None,
            "action": "APPROVED" if approve else "REJECTED",
            "comment": str(reject_reason or "").strip() if not approve else None,
            "decidedAt": now.isoformat(),
        }
    )
    row.approvalHistory = history

    if not approve:
        row.status = "REJECTED"
        row.rejectReason = str(reject_reason or "ไม่อนุมัติ").strip()
        row.approvedBy = caller.memberId if caller else None
        row.approvedAt = now
        return False

    if current_level < max_level:
        row.approvalLevel = current_level + 1
        row.status = "PENDING"
        row.rejectReason = None
        return False

    row.status = "APPROVED"
    row.rejectReason = None
    row.approvedBy = caller.memberId if caller else None
    row.approvedAt = now
    return True
