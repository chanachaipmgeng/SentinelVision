"""Thin HR helpers for shift CRUD — keeps ``hr_routes`` free of business logic."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..controllers.employee_timestamp_controller import (
    get_company_shift_settings,
    update_company_shift_settings,
)
from ..models.company_employee import CompanyEmployee
from ..models.department import Department
from ..models.hr_schedule import WorkShift
from ..schemas.hr_schema import AssignShiftBody, WorkShiftCreate, WorkShiftUpdate


def serialize_shift(ws: WorkShift) -> dict[str, Any]:
    windows = getattr(ws, "breakWindows", None) or []
    if not isinstance(windows, list):
        windows = []
    return {
        "shiftId": str(ws.shiftId),
        "companyId": str(ws.companyId),
        "name": ws.name,
        "startTime": ws.startTime,
        "endTime": ws.endTime,
        "graceMinutes": int(ws.graceMinutes or 0),
        "roundingMinutes": int(getattr(ws, "roundingMinutes", 0) or 0),
        "breakMinutes": int(getattr(ws, "breakMinutes", 0) or 0),
        "breakWindows": windows,
        "otThresholdMinutes": int(getattr(ws, "otThresholdMinutes", 0) or 0),
        "isCrossMidnight": bool(ws.isCrossMidnight),
        "isDefault": bool(ws.isDefault),
        "createdAt": ws.createdAt,
    }


async def list_shifts(company_id: UUID, db: AsyncSession) -> dict[str, Any]:
    rows = (
        await db.execute(
            select(WorkShift)
            .where(WorkShift.companyId == company_id, WorkShift.deletedAt.is_(None))
            .order_by(WorkShift.isDefault.desc(), WorkShift.createdAt.asc())
        )
    ).scalars().all()
    default_cfg = await get_company_shift_settings(company_id, db)
    return {
        "defaultSetting": default_cfg,
        "shifts": [serialize_shift(r) for r in rows],
    }


async def _clear_other_defaults(
    company_id: UUID, db: AsyncSession, *, keep_shift_id: Optional[UUID] = None
) -> None:
    stmt = select(WorkShift).where(
        WorkShift.companyId == company_id,
        WorkShift.isDefault.is_(True),
        WorkShift.deletedAt.is_(None),
    )
    if keep_shift_id is not None:
        stmt = stmt.where(WorkShift.shiftId != keep_shift_id)
    for ed in (await db.execute(stmt)).scalars().all():
        ed.isDefault = False


async def create_shift(company_id: UUID, body: WorkShiftCreate, db: AsyncSession) -> dict[str, Any]:
    if body.isDefault:
        await _clear_other_defaults(company_id, db)

    windows = [w.model_dump() for w in body.breakWindows]
    ws = WorkShift(
        companyId=company_id,
        name=body.name,
        startTime=body.startTime,
        endTime=body.endTime,
        graceMinutes=body.graceMinutes,
        roundingMinutes=body.roundingMinutes,
        breakMinutes=body.breakMinutes,
        breakWindows=windows,
        otThresholdMinutes=body.otThresholdMinutes,
        isCrossMidnight=body.isCrossMidnight,
        isDefault=body.isDefault,
    )
    db.add(ws)
    await db.commit()
    await db.refresh(ws)
    if body.isDefault:
        await update_company_shift_settings(
            company_id,
            {
                "name": body.name,
                "startTime": body.startTime,
                "endTime": body.endTime,
                "graceMinutes": body.graceMinutes,
                "roundingMinutes": body.roundingMinutes,
                "breakMinutes": body.breakMinutes,
                "breakWindows": windows,
                "otThresholdMinutes": body.otThresholdMinutes,
                "isCrossMidnight": body.isCrossMidnight,
            },
            db,
        )
    return serialize_shift(ws)


async def update_shift(
    company_id: UUID, shift_id: UUID, body: WorkShiftUpdate, db: AsyncSession
) -> dict[str, Any]:
    ws = await db.get(WorkShift, shift_id)
    if not ws or ws.companyId != company_id or ws.deletedAt is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found")

    data = body.model_dump(exclude_unset=True)
    if "name" in data and data["name"] is not None:
        ws.name = data["name"]
    if "startTime" in data and data["startTime"] is not None:
        ws.startTime = data["startTime"]
    if "endTime" in data and data["endTime"] is not None:
        ws.endTime = data["endTime"]
    if "graceMinutes" in data and data["graceMinutes"] is not None:
        ws.graceMinutes = data["graceMinutes"]
    if "roundingMinutes" in data and data["roundingMinutes"] is not None:
        ws.roundingMinutes = data["roundingMinutes"]
    if "breakMinutes" in data and data["breakMinutes"] is not None:
        ws.breakMinutes = data["breakMinutes"]
    if "breakWindows" in data and data["breakWindows"] is not None:
        ws.breakWindows = data["breakWindows"]
    if "otThresholdMinutes" in data and data["otThresholdMinutes"] is not None:
        ws.otThresholdMinutes = data["otThresholdMinutes"]
    if "isCrossMidnight" in data and data["isCrossMidnight"] is not None:
        ws.isCrossMidnight = data["isCrossMidnight"]
    if "isDefault" in data and data["isDefault"] is not None:
        if data["isDefault"]:
            await _clear_other_defaults(company_id, db, keep_shift_id=shift_id)
        ws.isDefault = bool(data["isDefault"])

    await db.commit()
    await db.refresh(ws)
    return serialize_shift(ws)


async def delete_shift(company_id: UUID, shift_id: UUID, db: AsyncSession) -> dict[str, Any]:
    ws = await db.get(WorkShift, shift_id)
    if not ws or ws.companyId != company_id or ws.deletedAt is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found")
    ws.deletedAt = datetime.now(timezone.utc)
    await db.commit()
    return {"deleted": True, "shiftId": str(shift_id)}


async def assign_shift(company_id: UUID, body: AssignShiftBody, db: AsyncSession) -> dict[str, Any]:
    shift_uuid = body.shiftId
    if shift_uuid:
        ws = await db.get(WorkShift, shift_uuid)
        if not ws or ws.companyId != company_id or ws.deletedAt is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found")

    if body.departmentId:
        dept = await db.get(Department, body.departmentId)
        if not dept or dept.companyId != company_id or dept.deletedAt is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
        dept.shiftId = shift_uuid
        await db.commit()
        return {
            "assigned": "department",
            "departmentId": str(body.departmentId),
            "shiftId": str(shift_uuid) if shift_uuid else None,
        }

    if body.company_employeeId:
        emp = await db.get(CompanyEmployee, body.company_employeeId)
        if not emp or emp.companyId != company_id or emp.deletedAt is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
        emp.shiftId = shift_uuid
        await db.commit()
        return {
            "assigned": "employee",
            "company_employeeId": str(body.company_employeeId),
            "shiftId": str(shift_uuid) if shift_uuid else None,
        }

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Provide departmentId or company_employeeId",
    )
