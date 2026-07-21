from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from ..models.employee_timestamp import TimestampType
from ..config.database import get_db
from ..controllers.employee_timestamp_controller import (
    get_all_timestamps,
    get_timestamp_by_id,
    create_timestamp,
    update_timestamp,
    delete_timestamp,
    search_timestamps,
    approve_or_reject_timestamp,
)
from ..schemas.employee_timestamp_schema import (
    EmployeeTimestampCreate,
    EmployeeTimestampUpdate,
    EmployeeTimestampResponse,
    EmployeeTimestampBase,
    TimestampApprovalAction,
)

router = APIRouter()

# ดึงข้อมูลการลงเวลาทั้งหมดของพนักงานในบริษัท
@router.get("/company/{companyId}", response_model=List[EmployeeTimestampResponse])
async def get_all_timestamps_route(companyId: UUID, db: AsyncSession = Depends(get_db)):
    return await get_all_timestamps(companyId, db)

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
    db: AsyncSession = Depends(get_db),
):
    """Empty query strings (from Angular) are treated as omitted filters."""

    def _blank(v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v or None

    def _parse_dt(v: Optional[str]) -> Optional[datetime]:
        v = _blank(v)
        if not v:
            return None
        # Accept date-only or ISO datetime
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

    return await search_timestamps(
        companyId,
        _blank(company_employeeId),
        _parse_dt(startDate),
        _parse_dt(endDate),
        _parse_int(timestampType),
        _blank(approvalStatus),
        db,
    )


@router.post("/company/{companyId}/{timestampId}/approval", response_model=EmployeeTimestampResponse)
async def approve_timestamp_route(
    companyId: UUID,
    timestampId: UUID,
    action: TimestampApprovalAction,
    db: AsyncSession = Depends(get_db),
):
    return await approve_or_reject_timestamp(timestampId, companyId, action, db)
