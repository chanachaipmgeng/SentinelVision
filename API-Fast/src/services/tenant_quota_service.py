"""D5 tenant lifecycle (suspend/offboard) and quota gates (devices/employees/gpuPriority).

Package / module quotas also live in ``modules:{companyId}`` (see company_module_service);
company columns are the enforceable source of truth for hard caps.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.company import Company, LifecycleStatus
from ..models.company_employee import CompanyEmployee
from ..models.hr_schedule import KioskDevice

# Named packages → default hard caps + allowed toggleable modules (None = unlimited).
PACKAGE_PRESETS: dict[str, dict[str, Any]] = {
    "STARTER": {
        "maxDevices": 2,
        "maxEmployees": 50,
        "gpuPriority": 0,
        "allowedModules": ["ATTENDANCE"],
    },
    "PRO": {
        "maxDevices": 10,
        "maxEmployees": 500,
        "gpuPriority": 5,
        "allowedModules": ["ATTENDANCE", "ACCESS_CONTROL", "WATCHLIST", "VISITOR"],
    },
    "ENTERPRISE": {
        "maxDevices": None,
        "maxEmployees": None,
        "gpuPriority": 10,
        "allowedModules": [
            "ATTENDANCE",
            "ACCESS_CONTROL",
            "WATCHLIST",
            "VISITOR",
            "EVENTS",
        ],
    },
}


def serialize_tenant_admin(company: Company, *, usage: Optional[dict] = None) -> dict:
    return {
        "companyId": str(company.companyId),
        "companyName": company.companyName,
        "companyCode": company.companyCode,
        "lifecycleStatus": company.lifecycleStatus or LifecycleStatus.ACTIVE,
        "suspendedAt": company.suspendedAt,
        "offboardedAt": company.offboardedAt,
        "packageCode": company.packageCode,
        "quotas": {
            "maxDevices": company.maxDevices,
            "maxEmployees": company.maxEmployees,
            "gpuPriority": int(company.gpuPriority or 0),
        },
        "usage": usage or None,
    }


async def count_active_devices(db: AsyncSession, company_id: UUID) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(KioskDevice)
        .where(KioskDevice.companyId == company_id, KioskDevice.revokedAt.is_(None))
    )
    return int(result.scalar_one() or 0)


async def count_active_employees(db: AsyncSession, company_id: UUID) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(CompanyEmployee)
        .where(CompanyEmployee.companyId == company_id, CompanyEmployee.deletedAt.is_(None))
    )
    return int(result.scalar_one() or 0)


async def get_usage(db: AsyncSession, company: Company) -> dict:
    return {
        "devices": await count_active_devices(db, company.companyId),
        "employees": await count_active_employees(db, company.companyId),
    }


async def assert_tenant_active(db: AsyncSession, company_id: UUID | str) -> Company:
    """Raise 403 if the tenant is suspended/offboarded (or missing)."""
    company = await db.get(Company, UUID(str(company_id)))
    if company is None or company.deletedAt is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    life = (company.lifecycleStatus or LifecycleStatus.ACTIVE).upper()
    if life == LifecycleStatus.SUSPENDED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Company is suspended")
    if life == LifecycleStatus.OFFBOARDED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Company is offboarded")
    return company


async def assert_device_quota(db: AsyncSession, company: Company) -> None:
    if company.maxDevices is None:
        return
    used = await count_active_devices(db, company.companyId)
    if used >= int(company.maxDevices):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Device quota exceeded ({used}/{company.maxDevices})",
        )


async def assert_employee_quota(db: AsyncSession, company: Company) -> None:
    if company.maxEmployees is None:
        return
    used = await count_active_employees(db, company.companyId)
    if used >= int(company.maxEmployees):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Employee quota exceeded ({used}/{company.maxEmployees})",
        )


def apply_package_preset(company: Company, package_code: Optional[str]) -> None:
    if not package_code:
        company.packageCode = None
        return
    code = str(package_code).strip().upper()
    preset = PACKAGE_PRESETS.get(code)
    if preset is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown packageCode (expected {', '.join(PACKAGE_PRESETS)})",
        )
    company.packageCode = code
    company.maxDevices = preset["maxDevices"]
    company.maxEmployees = preset["maxEmployees"]
    company.gpuPriority = int(preset["gpuPriority"])


async def suspend_company(db: AsyncSession, company: Company) -> Company:
    life = (company.lifecycleStatus or LifecycleStatus.ACTIVE).upper()
    if life == LifecycleStatus.OFFBOARDED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Company is already offboarded")
    company.lifecycleStatus = LifecycleStatus.SUSPENDED
    company.suspendedAt = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(company)
    return company


async def resume_company(db: AsyncSession, company: Company) -> Company:
    life = (company.lifecycleStatus or LifecycleStatus.ACTIVE).upper()
    if life == LifecycleStatus.OFFBOARDED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot resume an offboarded company")
    company.lifecycleStatus = LifecycleStatus.ACTIVE
    company.suspendedAt = None
    await db.commit()
    await db.refresh(company)
    return company


async def offboard_company(db: AsyncSession, company: Company, *, purge_devices: bool = True) -> Company:
    """Mark tenant offboarded and revoke all active kiosk devices (soft offboard)."""
    from . import token_revocation_service as revocation
    from ..config.settings import settings

    now = datetime.now(timezone.utc)
    company.lifecycleStatus = LifecycleStatus.OFFBOARDED
    company.offboardedAt = now
    company.suspendedAt = company.suspendedAt or now

    if purge_devices:
        rows = (
            await db.execute(
                select(KioskDevice).where(
                    KioskDevice.companyId == company.companyId,
                    KioskDevice.revokedAt.is_(None),
                )
            )
        ).scalars().all()
        for device in rows:
            if device.tokenFamily:
                await revocation.revoke_family(
                    db,
                    device.tokenFamily,
                    now + timedelta(days=int(getattr(settings, "KIOSK_REFRESH_TOKEN_DAYS", 30) or 30)),
                    reason=revocation.REASON_DEVICE_REVOKED,
                )
            device.tokenHash = None
            device.tokenFamily = None
            device.pairingCodeHash = None
            device.pairingExpiresAt = None
            device.revokedAt = now

    await db.commit()
    await db.refresh(company)
    return company


async def update_quotas(db: AsyncSession, company: Company, body: dict) -> Company:
    if "packageCode" in body:
        apply_package_preset(company, body.get("packageCode"))
    if "maxDevices" in body:
        val = body.get("maxDevices")
        company.maxDevices = None if val in (None, "") else int(val)
        if company.maxDevices is not None and company.maxDevices < 0:
            raise HTTPException(status_code=400, detail="maxDevices must be >= 0")
    if "maxEmployees" in body:
        val = body.get("maxEmployees")
        company.maxEmployees = None if val in (None, "") else int(val)
        if company.maxEmployees is not None and company.maxEmployees < 0:
            raise HTTPException(status_code=400, detail="maxEmployees must be >= 0")
    if "gpuPriority" in body:
        company.gpuPriority = int(body.get("gpuPriority") or 0)
    await db.commit()
    await db.refresh(company)
    return company
