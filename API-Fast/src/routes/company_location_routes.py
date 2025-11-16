from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
from ..config.database import get_db
from ..controllers.company_location_controller import (
    get_all_locations,
    get_location_by_id,
    create_location,
    update_location,
    delete_location
)
from ..schemas.company_location_schema import CompanyLocationCreate, CompanyLocationUpdate, CompanyLocationResponse

router = APIRouter()

# ดึงข้อมูลสถานที่ทั้งหมดของบริษัท
@router.get("/company/{companyId}", response_model=List[CompanyLocationResponse])
async def get_all_locations_route(companyId: UUID, db: AsyncSession = Depends(get_db)):
    return await get_all_locations(companyId, db)

# ดึงข้อมูลสถานที่ตาม locationId
@router.get("/company/{companyId}/{locationId}", response_model=CompanyLocationResponse)
async def get_location_by_id_route(companyId: UUID, locationId: UUID, db: AsyncSession = Depends(get_db)):
    return await get_location_by_id(locationId, companyId, db)

# สร้างสถานที่ใหม่
@router.post("/company/{companyId}", response_model=CompanyLocationResponse)
async def create_location_route(companyId: UUID, location: CompanyLocationCreate, db: AsyncSession = Depends(get_db)):
    return await create_location(location.dict(), companyId, db)

# อัปเดตข้อมูลสถานที่
@router.put("/company/{companyId}/{locationId}", response_model=CompanyLocationResponse)
async def update_location_route(companyId: UUID, locationId: UUID, location: CompanyLocationUpdate, db: AsyncSession = Depends(get_db)):
    return await update_location(locationId, companyId, location.dict(exclude_unset=True), db)

# ลบสถานที่
@router.delete("/company/{companyId}/{locationId}")
async def delete_location_route(companyId: UUID, locationId: UUID, db: AsyncSession = Depends(get_db)):
    await delete_location(locationId, companyId, db)
    return {"detail": "Location deleted successfully"}
