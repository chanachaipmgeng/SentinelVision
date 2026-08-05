from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status
from uuid import UUID
from ..models.company_location import CompanyLocation, LocationType

_ALLOWED_FIELDS = {
    "latitude",
    "longitude",
    "radius",
    "locationName",
    "startDate",
    "endDate",
    "locationType",
    "companyId",
}


def _clean_location_data(data: dict) -> dict:
    clean = {k: v for k, v in data.items() if k in _ALLOWED_FIELDS and v is not None}
    if "radius" not in clean or clean.get("radius") in ("", None):
        clean["radius"] = 0.5
    if "locationType" not in clean or clean.get("locationType") is None:
        clean["locationType"] = LocationType.PERMANENT
    now = datetime.now(timezone.utc)
    if "startDate" not in clean:
        clean["startDate"] = now
    if "endDate" not in clean:
        clean["endDate"] = now
    return clean


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
    clean = _clean_location_data(data)
    clean["companyId"] = companyId
    new_location = CompanyLocation(**clean)
    db.add(new_location)
    await db.commit()
    await db.refresh(new_location)
    return new_location

# อัปเดตข้อมูลสถานที่
async def update_location(locationId: UUID, companyId: UUID, data: dict, db: AsyncSession):
    location = await get_location_by_id(locationId, companyId, db)
    for key, value in data.items():
        if key not in _ALLOWED_FIELDS or key == "companyId":
            continue
        if value is None or (isinstance(value, str) and value.strip() == ""):
            continue
        setattr(location, key, value)
    await db.commit()
    await db.refresh(location)
    return location

# ลบสถานที่
async def delete_location(locationId: UUID, companyId: UUID, db: AsyncSession):
    location = await get_location_by_id(locationId, companyId, db)
    await db.delete(location)
    await db.commit()
