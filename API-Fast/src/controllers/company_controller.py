from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from ..models.company import Company
from fastapi import HTTPException, status
import bcrypt

# ฟังก์ชันเพื่อดึงข้อมูลบริษัททั้งหมด
async def get_all_companies(db: AsyncSession, include_deleted: bool = False):
    stmt = select(Company)
    if not include_deleted:
        stmt = stmt.where(Company.deletedAt.is_(None))
    result = await db.execute(stmt)
    return result.scalars().all()

# ฟังก์ชันเพื่อดึงข้อมูลบริษัทตาม ID
async def get_company_by_id(companyId: str, db: AsyncSession):
    result = await db.execute(
        select(Company).where(Company.companyId == companyId, Company.deletedAt.is_(None))
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company

# ฟังก์ชันเพื่อสร้างบริษัทใหม่
async def create_company(company_data: dict, db: AsyncSession):
    new_company = Company(**company_data)
    db.add(new_company)
    await db.commit()
    await db.refresh(new_company)
    return new_company

# ฟังก์ชันเพื่ออัปเดตข้อมูลบริษัท
async def update_company(companyId: str, company_data: dict, db: AsyncSession):
    company = await get_company_by_id(companyId, db)
    for key, value in company_data.items():
        setattr(company, key, value)
    await db.commit()
    await db.refresh(company)
    return company

# ฟังก์ชันเพื่อการลบบริษัท
async def delete_company(companyId: str, db: AsyncSession):
    from ..utils.soft_delete import mark_deleted

    company = await get_company_by_id(companyId, db)
    mark_deleted(company)
    await db.commit()
    return {
        "actionStatus": "Success",
        "message": "Company deleted",
        "statusCode": 200,
    }
