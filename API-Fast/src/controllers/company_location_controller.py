from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status
from uuid import UUID
from ..models.company_location import CompanyLocation

# ดึงข้อมูลสถานที่ทั้งหมดของบริษัทตาม companyId
async def get_all_locations(companyId: UUID, db: AsyncSession):
    result = await db.execute(
        select(CompanyLocation).where(CompanyLocation.companyId == companyId)
    )
    return result.scalars().all()

# ดึงข้อมูลสถานที่ตาม locationId และ companyId
async def get_location_by_id(locationId: UUID, companyId: UUID, db: AsyncSession):
    result = await db.execute(
        select(CompanyLocation).where(
            CompanyLocation.locationId == locationId,
            CompanyLocation.companyId == companyId
        )
    )
    location = result.scalar_one_or_none()
    if not location:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
    return location

# สร้างสถานที่ใหม่
async def create_location(data: dict, companyId: UUID, db: AsyncSession):
    data["companyId"] = companyId
    new_location = CompanyLocation(**data)
    db.add(new_location)
    await db.commit()
    await db.refresh(new_location)
    return new_location

# อัปเดตข้อมูลสถานที่
async def update_location(locationId: UUID, companyId: UUID, data: dict, db: AsyncSession):
    location = await get_location_by_id(locationId, companyId, db)
    for key, value in data.items():
        setattr(location, key, value)
    await db.commit()
    await db.refresh(location)
    return location

# ลบสถานที่
async def delete_location(locationId: UUID, companyId: UUID, db: AsyncSession):
    location = await get_location_by_id(locationId, companyId, db)
    await db.delete(location)
    await db.commit()
