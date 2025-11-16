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
    search_timestamps
)
from ..schemas.employee_timestamp_schema import (
    EmployeeTimestampCreate,
    EmployeeTimestampUpdate,
    EmployeeTimestampResponse,
    EmployeeTimestampBase,
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
    startDate: Optional[datetime] = Query(None),
    endDate: Optional[datetime] = Query(None),
    timestampType: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    return await search_timestamps(companyId, company_employeeId, startDate, endDate, timestampType, db)
