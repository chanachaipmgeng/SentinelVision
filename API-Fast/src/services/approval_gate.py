"""C4 approval gate — now backed by D1 RBAC (``rbac_service``).

Kept as a thin re-export so existing imports continue to work. Prefer
``rbac_service.assert_can_approve_for_employee`` / ``require_permission`` for new code.
"""
from __future__ import annotations

from ..services.rbac_service import (  # noqa: F401
    assert_can_approve_for_employee,
    assert_permission,
    boss_matches,
    can_approve_for_employee,
    get_company_employment,
    has_permission,
    is_legacy_company_admin,
    is_system_admin_member,
)

# Back-compat aliases used by older call sites / tests.
is_admin_role = is_system_admin_member
is_company_admin_role = is_legacy_company_admin


async def assert_company_membership(db, member, company_id):
    """Any active employment in the company (or system admin) — softer than assert_company_access."""
    from fastapi import HTTPException, status

    if member is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization required")
    if is_system_admin_member(member):
        return member
    emp = await get_company_employment(db, member.memberId, company_id)
    if emp is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this company")
    return member
