from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from ..models.department import Department
from ..models.company import Company
from ..models.company_employee import CompanyEmployee
from fastapi import HTTPException, status

# ดึงข้อมูล department ทั้งหมด
async def get_all_departments(db: AsyncSession):
    result = await db.execute(
        select(Department).where(Department.deletedAt.is_(None)).options(joinedload(Department.company))
    )
    return result.scalars().all()

# ดึงข้อมูล department ตาม ID
async def get_department_by_id(departmentId: str, db: AsyncSession):
    result = await db.execute(
        select(Department)
        .where(Department.departmentId == departmentId, Department.deletedAt.is_(None))
        .options(joinedload(Department.company))
    )
    department = result.scalar_one_or_none()
    if not department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    return department

# ดึงข้อมูล departments โดยใช้ companyId พร้อมจำนวนพนักงานที่ใช้งานอยู่
async def get_departments_by_companyId(companyId: str, db: AsyncSession):
    result = await db.execute(
        select(Department).where(Department.companyId == companyId, Department.deletedAt.is_(None))
    )
    departments = result.scalars().all()
    if not departments:
        return departments
    count_rows = await db.execute(
        select(CompanyEmployee.departmentId, func.count(CompanyEmployee.company_employeeId))
        .where(CompanyEmployee.companyId == companyId, CompanyEmployee.deletedAt.is_(None))
        .group_by(CompanyEmployee.departmentId)
    )
    counts = {row[0]: int(row[1]) for row in count_rows.all()}
    for dept in departments:
        setattr(dept, "employeeCount", counts.get(dept.departmentId, 0))
    return departments

# สร้าง department ใหม่
async def create_department(department_data: dict, db: AsyncSession):
    # ตรวจสอบว่ามี companyId ที่อ้างอิงถึงอยู่หรือไม่
    companyId = department_data["companyId"]
    company = await db.get(Company, companyId)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    new_department = Department(**department_data)
    db.add(new_department)
    await db.commit()
    await db.refresh(new_department)
    return new_department

# อัปเดต department
async def update_department(departmentId: str, department_data: dict, db: AsyncSession):
    department = await db.get(Department, departmentId)
    if not department or department.deletedAt is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    # อัปเดตข้อมูล department
    for key, value in department_data.items():
        setattr(department, key, value)

    await db.commit()
    await db.refresh(department)
    return department

# ลบ department
async def delete_department(departmentId: str, db: AsyncSession, force: bool = False):
    from ..utils.soft_delete import mark_deleted

    department = await db.get(Department, departmentId)
    if not department or department.deletedAt is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    if not force:
        active_count = await db.scalar(
            select(func.count(CompanyEmployee.company_employeeId)).where(
                CompanyEmployee.departmentId == departmentId,
                CompanyEmployee.deletedAt.is_(None),
            )
        )
        if active_count and int(active_count) > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot delete department with {int(active_count)} active employee(s)",
            )
    mark_deleted(department)
    await db.commit()
