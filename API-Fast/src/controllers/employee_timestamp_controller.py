from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from typing import Optional, List
from datetime import datetime

from ..schemas.employee_timestamp_schema import EmployeeTimestampUpdate
from ..models.employee_timestamp import EmployeeTimestamp, TimestampType
from uuid import UUID
from ..models.company_employee import CompanyEmployee

# ดึงข้อมูลการลงเวลาทั้งหมดของพนักงานในบริษัท
async def get_all_timestamps(companyId: str, db: AsyncSession):
    result = await db.execute(
        select(EmployeeTimestamp).where(EmployeeTimestamp.companyId == companyId).options(
            selectinload(EmployeeTimestamp.company_employee).joinedload(CompanyEmployee.member),
            selectinload(EmployeeTimestamp.company_employee).joinedload(CompanyEmployee.position),
            selectinload(EmployeeTimestamp.company_employee).joinedload(CompanyEmployee.department)
        )
    )
    timestamps = result.scalars().all()

    # จัดรูปแบบ response
    response = []
    for time in timestamps:
        response.append({
            "employee" : time.company_employee,
            "company_employeeId": time.company_employeeId,
            "timestampType": time.timestampType,
            "locationName" : time.locationName,
            "latitude": time.latitude,
            "longitude": time.longitude,
            "photoTimestamp": time.photoTimestamp,
            "timestampId": time.timestampId,
            "companyId": time.companyId,
            "timestamp": time.timestamp,
            "createdAt": time.createdAt,
            "updatedAt": time.updatedAt
        })

    return response

# ดึงข้อมูลการลงเวลาของพนักงานจาก timestampId
async def get_timestamp_by_id(timestampId: UUID, companyId: UUID, db: AsyncSession):
    result = await db.execute(
        select(EmployeeTimestamp).where(
            EmployeeTimestamp.timestampId == timestampId,
            EmployeeTimestamp.companyId == companyId
        )
    )
    timestamp = result.scalar_one_or_none()
    if not timestamp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timestamp not found")
    return timestamp

# สร้างข้อมูลการลงเวลาของพนักงานใหม่
async def create_timestamp(data: dict, companyId: UUID, db: AsyncSession):
    data["companyId"] = companyId
    new_timestamp = EmployeeTimestamp(**data)
    db.add(new_timestamp)
    await db.commit()
    await db.refresh(new_timestamp)
    result = await db.execute(
        select(CompanyEmployee)
        .where(
            CompanyEmployee.company_employeeId == new_timestamp.company_employeeId,
            CompanyEmployee.companyId == companyId
        )
        .options(
            selectinload(CompanyEmployee.member),
            selectinload(CompanyEmployee.company),
            selectinload(CompanyEmployee.position),
            selectinload(CompanyEmployee.department)
        )
    )
    company_employee = result.scalar_one_or_none()
    if not company_employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company Employee not found")
    return {
                "employee": company_employee,
                "company_employeeId": new_timestamp.company_employeeId,
                "timestampType": new_timestamp.timestampType,
                "locationName" : new_timestamp.locationName,
                "latitude": new_timestamp.latitude,
                "longitude": new_timestamp.longitude,
                "photoTimestamp": new_timestamp.photoTimestamp,
                "timestampId": new_timestamp.timestampId,
                "companyId": new_timestamp.companyId,
                "timestamp": new_timestamp.timestamp,
                "createdAt": new_timestamp.createdAt,
                "updatedAt": new_timestamp.updatedAt
            }

# อัปเดตข้อมูลการลงเวลาของพนักงาน
async def update_timestamp(timestampId: UUID, companyId: UUID, data: EmployeeTimestampUpdate, db: AsyncSession):
    timestamp = await get_timestamp_by_id(timestampId, companyId, db)
    if data.timestampType:
        timestamp.timestampType = data.timestampType
    if data.locationName:
        timestamp.locationName = data.locationName
    await db.commit()
    await db.refresh(timestamp)
    return timestamp

# ลบข้อมูลการลงเวลาของพนักงาน
async def delete_timestamp(timestampId: UUID, companyId: UUID, db: AsyncSession):
    timestamp = await get_timestamp_by_id(timestampId, companyId, db)
    await db.delete(timestamp)
    await db.commit()

# ค้นหาการลงเวลาตามเงื่อนไข
async def search_timestamps(
    companyId: str,
    company_employeeId: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    timestampType: Optional[int] = None,
    db: AsyncSession = None
):
    query = select(EmployeeTimestamp).where(EmployeeTimestamp.companyId == companyId)

    if start_date:
        query = query.where(EmployeeTimestamp.timestamp >= start_date)
    if end_date:
        query = query.where(EmployeeTimestamp.timestamp <= end_date)
    if company_employeeId:
        query = query.where(EmployeeTimestamp.company_employeeId == company_employeeId)
    if timestampType:
        query = query.where(EmployeeTimestamp.timestampType == timestampType)

    result = await db.execute(query.options(
        selectinload(EmployeeTimestamp.company_employee).joinedload(CompanyEmployee.member),
        selectinload(EmployeeTimestamp.company_employee).joinedload(CompanyEmployee.position),
        selectinload(EmployeeTimestamp.company_employee).joinedload(CompanyEmployee.department)
    ))

    timestamps = result.scalars().all()

    # จัดรูปแบบ response
    response = []
    for time in timestamps:
        response.append({
            "employee": time.company_employee,
            "company_employeeId": time.company_employeeId,
            "timestampType": time.timestampType,
            "locationName" : time.locationName,
            "latitude": time.latitude,
            "longitude": time.longitude,
            "photoTimestamp": time.photoTimestamp,
            "timestampId": time.timestampId,
            "companyId": time.companyId,
            "timestamp": time.timestamp,
            "createdAt": time.createdAt,
            "updatedAt": time.updatedAt
        })

    return response
