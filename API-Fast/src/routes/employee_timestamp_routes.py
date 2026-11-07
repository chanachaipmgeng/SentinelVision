from datetime import datetime
import io
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from uuid import UUID

from ..config.database import get_db
from ..controllers.employee_timestamp_controller import (
    get_all_timestamps,
    get_timestamp_by_id,
    create_timestamp,
    update_timestamp,
    delete_timestamp,
    search_timestamps,
    approve_or_reject_timestamp,
    get_company_shift_settings,
    update_company_shift_settings,
    build_timestamps_csv,
    build_timestamps_xlsx,
)
from ..schemas.employee_timestamp_schema import (
    EmployeeTimestampCreate,
    EmployeeTimestampUpdate,
    EmployeeTimestampResponse,
    EmployeeTimestampBase,
    TimestampApprovalAction,
)

router = APIRouter()


def _blank(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    v = v.strip()
    return v or None


def _parse_dt(v: Optional[str]) -> Optional[datetime]:
    v = _blank(v)
    if not v:
        return None
    try:
        if len(v) == 10 and v[4] == "-" and v[7] == "-":
            return datetime.fromisoformat(v)
        return datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid datetime: {v}",
        ) from exc


def _parse_int(v: Optional[str]) -> Optional[int]:
    v = _blank(v)
    if v is None:
        return None
    try:
        return int(v)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid timestampType: {v}",
        ) from exc


@router.get("/company/{companyId}/shift-settings")
async def get_shift_settings_route(companyId: UUID, db: AsyncSession = Depends(get_db)):
    return await get_company_shift_settings(companyId, db)


@router.put("/company/{companyId}/shift-settings")
async def put_shift_settings_route(
    companyId: UUID, payload: Dict[str, Any], db: AsyncSession = Depends(get_db)
):
    return await update_company_shift_settings(companyId, payload, db)


@router.get("/export/company/{companyId}")
async def export_timestamps_route(
    companyId: str,
    format: str = Query("xlsx"),
    company_employeeId: Optional[str] = Query(None),
    startDate: Optional[str] = Query(None),
    endDate: Optional[str] = Query(None),
    timestampType: Optional[str] = Query(None),
    approvalStatus: Optional[str] = Query(None),
    limit: int = Query(5000, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
):
    items = await search_timestamps(
        companyId,
        _blank(company_employeeId),
        _parse_dt(startDate),
        _parse_dt(endDate),
        _parse_int(timestampType),
        _blank(approvalStatus),
        db,
        limit=limit,
        offset=0,
    )
    fmt = (format or "xlsx").strip().lower()
    if fmt == "csv":
        data = build_timestamps_csv(items)
        return Response(
            content=data,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": 'attachment; filename="attendance-report.csv"'
            },
        )
    data = build_timestamps_xlsx(items)
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="attendance-report.xlsx"'
        },
    )


# ดึงข้อมูลการลงเวลาทั้งหมดของพนักงานในบริษัท
@router.get("/company/{companyId}", response_model=List[EmployeeTimestampResponse])
async def get_all_timestamps_route(
    companyId: UUID,
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    return await get_all_timestamps(companyId, db, limit=limit, offset=offset)


# ดึงข้อมูลการลงเวลาของพนักงานจาก timestampId
@router.get("/company/{companyId}/{timestampId}", response_model=EmployeeTimestampResponse)
async def get_timestamp_by_id_route(companyId: UUID, timestampId: UUID, db: AsyncSession = Depends(get_db)):
    return await get_timestamp_by_id(timestampId, companyId, db)


# สร้างข้อมูลการลงเวลาของพนักงานใหม่
@router.post("/company/{companyId}", response_model=EmployeeTimestampResponse)
async def create_timestamp_route(companyId: UUID, timestamp: EmployeeTimestampCreate, db: AsyncSession = Depends(get_db)):
    return await create_timestamp(timestamp.dict(), companyId, db)


# อัปเดตข้อมูลการลงเวลาของพนักงาน
@router.put("/company/{companyId}/{timestampId}", response_model=EmployeeTimestampBase)
async def update_timestamp_route(companyId: UUID, timestampId: UUID, timestamp: EmployeeTimestampUpdate, db: AsyncSession = Depends(get_db)):
    return await update_timestamp(timestampId, companyId, timestamp, db)


# ลบข้อมูลการลงเวลาของพนักงาน
@router.delete("/company/{companyId}/{timestampId}")
async def delete_timestamp_route(companyId: UUID, timestampId: UUID, db: AsyncSession = Depends(get_db)):
    await delete_timestamp(timestampId, companyId, db)
    return {"detail": "Timestamp deleted successfully"}


# ค้นหา timestamps ทั้งหมดของพนักงานจาก employeeId และเงื่อนไขอื่น ๆ
@router.get("/search/company/{companyId}", response_model=List[EmployeeTimestampResponse])
async def search_timestamps_route(
    companyId: str,
    company_employeeId: Optional[str] = Query(None),
    startDate: Optional[str] = Query(None),
    endDate: Optional[str] = Query(None),
    timestampType: Optional[str] = Query(None),
    approvalStatus: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Empty query strings (from Angular) are treated as omitted filters."""
    return await search_timestamps(
        companyId,
        _blank(company_employeeId),
        _parse_dt(startDate),
        _parse_dt(endDate),
        _parse_int(timestampType),
        _blank(approvalStatus),
        db,
        limit=limit,
        offset=offset,
    )


@router.post("/company/{companyId}/{timestampId}/approval", response_model=EmployeeTimestampResponse)
async def approve_timestamp_route(
    companyId: UUID,
    timestampId: UUID,
    action: TimestampApprovalAction,
    db: AsyncSession = Depends(get_db),
):
    return await approve_or_reject_timestamp(timestampId, companyId, action, db)
