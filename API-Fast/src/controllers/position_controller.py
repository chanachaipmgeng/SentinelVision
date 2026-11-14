from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from ..models.position import Position
from ..models.company import Company
from fastapi import HTTPException, status

# ดึงข้อมูล position ทั้งหมด
async def get_all_positions(db: AsyncSession):
    result = await db.execute(
        select(Position).where(Position.deletedAt.is_(None)).options(joinedload(Position.company))
    )
    return result.scalars().all()

# ดึงข้อมูล position ตาม ID
async def get_position_by_id(positionId: str, db: AsyncSession):
    result = await db.execute(
        select(Position)
        .where(Position.positionId == positionId, Position.deletedAt.is_(None))
        .options(joinedload(Position.company))
    )
    position = result.scalar_one_or_none()
    if not position:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
    return position

# ดึงข้อมูล positions โดยใช้ companyId
async def get_positions_by_companyId(companyId: str, db: AsyncSession):
    result = await db.execute(
        select(Position).where(Position.companyId == companyId, Position.deletedAt.is_(None))
    )
    return result.scalars().all()

# สร้าง position ใหม่
async def create_position(position_data: dict, db: AsyncSession):
    # ตรวจสอบว่ามี companyId ที่อ้างอิงถึงอยู่หรือไม่
    companyId = position_data["companyId"]
    company = await db.get(Company, companyId)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    new_position = Position(**position_data)
    db.add(new_position)
    await db.commit()
    await db.refresh(new_position)
    return new_position

# อัปเดต position
async def update_position(positionId: str, position_data: dict, db: AsyncSession):
    position = await db.get(Position, positionId)
    if not position or position.deletedAt is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")

    # อัปเดตข้อมูล position
    for key, value in position_data.items():
        setattr(position, key, value)

    await db.commit()
    await db.refresh(position)
    return position

# ลบ position
async def delete_position(positionId: str, db: AsyncSession):
    from ..utils.soft_delete import mark_deleted

    position = await db.get(Position, positionId)
    if not position or position.deletedAt is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
    mark_deleted(position)
    await db.commit()
