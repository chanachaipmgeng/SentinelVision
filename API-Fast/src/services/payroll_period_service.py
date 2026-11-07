"""C5 payroll period lock helpers."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.approvals_payroll import PayrollPeriod, PayrollPeriodStatus


async def find_locked_period_covering(
    db: AsyncSession,
    company_id: UUID,
    day: date,
) -> Optional[PayrollPeriod]:
    locked_states = (PayrollPeriodStatus.LOCKED.value, PayrollPeriodStatus.CLOSED.value)
    row = await db.execute(
        select(PayrollPeriod).where(
            PayrollPeriod.companyId == company_id,
            PayrollPeriod.status.in_(locked_states),
            PayrollPeriod.startDate <= day,
            PayrollPeriod.endDate >= day,
        ).limit(1)
    )
    return row.scalar_one_or_none()


async def assert_date_not_locked(
    db: AsyncSession,
    company_id: UUID,
    day: date,
    *,
    detail: str = "Payroll period is locked for this date",
) -> None:
    locked = await find_locked_period_covering(db, company_id, day)
    if locked is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


async def assert_range_not_locked(
    db: AsyncSession,
    company_id: UUID,
    start: date,
    end: date,
) -> None:
    locked_states = (PayrollPeriodStatus.LOCKED.value, PayrollPeriodStatus.CLOSED.value)
    row = await db.execute(
        select(PayrollPeriod).where(
            PayrollPeriod.companyId == company_id,
            PayrollPeriod.status.in_(locked_states),
            PayrollPeriod.startDate <= end,
            PayrollPeriod.endDate >= start,
        ).limit(1)
    )
    if row.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Payroll period is locked for part of this date range",
        )


async def close_and_lock_period(
    db: AsyncSession,
    period: PayrollPeriod,
    locked_by: UUID,
) -> PayrollPeriod:
    st = getattr(period.status, "value", period.status)
    if st in (PayrollPeriodStatus.LOCKED.value, PayrollPeriodStatus.CLOSED.value):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Period already closed")
    period.status = PayrollPeriodStatus.LOCKED.value
    period.lockedAt = datetime.now(timezone.utc)
    period.lockedBy = locked_by
    await db.commit()
    await db.refresh(period)
    return period


def serialize_period(p: PayrollPeriod) -> dict:
    return {
        "periodId": str(p.periodId),
        "companyId": str(p.companyId),
        "name": p.name or "",
        "startDate": p.startDate.isoformat() if p.startDate else None,
        "endDate": p.endDate.isoformat() if p.endDate else None,
        "status": getattr(p.status, "value", p.status),
        "lockedAt": p.lockedAt,
        "lockedBy": str(p.lockedBy) if p.lockedBy else None,
        "createdAt": p.createdAt,
    }
