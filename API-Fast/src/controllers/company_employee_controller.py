from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from datetime import datetime

from ..schemas.company_employee_schema import CompanyEmployeePost, CompanyEmployeeUpdate
from ..models.company_employee import CompanyEmployee
from ..models.member import Member, RoleType, StatusType
from ..models.company import Company
from ..models.position import Position
from ..models.department import Department
from fastapi import Depends, HTTPException, status
from ..config.database import get_db
from ..schemas.member_schema import MemberCreate, MemberResponse
from uuid import UUID, uuid4

def _member_dict(member: Member) -> dict:
    return {
        "memberId": member.memberId,
        "username": member.username,
        "email": member.email,
        "firstName": member.firstName,
        "lastName": member.lastName,
        "picture": member.picture,
        "phoneNumber": member.phoneNumber,
        "birthDate": member.birthDate,
        "address": member.address,
        "emergencyContactName": member.emergencyContactName,
        "emergencyContactPhone": member.emergencyContactPhone,
        "attachmentUrls": member.attachmentUrls,
    }

# ดึงข้อมูล CompanyEmployee ทั้งหมดตาม companyId
async def get_all_companyEmployees(companyId: str, db: AsyncSession, limit: int | None = None, offset: int = 0):
    stmt = (
        select(CompanyEmployee)
        .where(CompanyEmployee.companyId == companyId, CompanyEmployee.deletedAt.is_(None))
        .options(
            selectinload(CompanyEmployee.member),
            selectinload(CompanyEmployee.position),
            selectinload(CompanyEmployee.department)
        )
    )
    if limit:
        stmt = stmt.offset(max(0, offset)).limit(min(int(limit), 500))
    result = await db.execute(stmt)
    employees = result.scalars().all()

    # จัดรูปแบบ response
    response = []
    for employee in employees:
        response.append({
            "member": _member_dict(employee.member),
            "companyId": employee.companyId,
            "employeeId": employee.employeeId or "",
            "position": {
                "positionId": employee.position.positionId,
                "thName": employee.position.thName,
                "engName": employee.position.engName
            } if employee.position else None,
            "department": {
                "departmentId": employee.department.departmentId,
                "thName": employee.department.thName,
                "engName": employee.department.engName
            } if employee.department else None,
            "company_employeeId": employee.company_employeeId,
            "salary": employee.salary if employee.salary is not None else 0,
            "startDate": employee.startDate,
            "companyRoleType": employee.companyRoleType,
            "empType": employee.empType,
            "bossId": employee.bossId or "",
        })

    return response

# ดึงข้อมูล CompanyEmployee ตาม memberid และ companyId
async def get_company_member_by_id(memberId: str, companyId: str, db: AsyncSession):
    result = await db.execute(
        select(CompanyEmployee)
        .where(
            CompanyEmployee.memberId == memberId,
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
    return company_employee


# ดึงข้อมูล CompanyEmployee ตาม company_employeeId และ companyId
async def get_company_employee_by_id(company_employeeId: str, companyId: str, db: AsyncSession):
    result = await db.execute(
        select(CompanyEmployee)
        .where(
            CompanyEmployee.company_employeeId == company_employeeId,
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
    return company_employee

# ดึงข้อมูล CompanyEmployee ตาม company_employeeId และ companyId
async def get_company_sub_employee_by_id(company_employeeId: str, companyId: str, db: AsyncSession):
    result = await db.execute(
        select(CompanyEmployee)
        .where(CompanyEmployee.companyId == companyId , CompanyEmployee.bossId == company_employeeId)
        .options(
            selectinload(CompanyEmployee.member),
            selectinload(CompanyEmployee.position),
            selectinload(CompanyEmployee.department)
        )
    )
    employees = result.scalars().all()

    # จัดรูปแบบ response
    response = []
    for employee in employees:
        response.append({
            "member": {
                "memberId": employee.member.memberId,
                "username": employee.member.username,
                "email": employee.member.email,
                "firstName": employee.member.firstName,
                "lastName": employee.member.lastName,
                "picture": employee.member.picture
            },
            "companyId": employee.companyId,
            "employeeId": employee.employeeId or "",
            "position": {
                "positionId": employee.position.positionId,
                "thName": employee.position.thName,
                "engName": employee.position.engName
            } if employee.position else None,
            "department": {
                "departmentId": employee.department.departmentId,
                "thName": employee.department.thName,
                "engName": employee.department.engName
            } if employee.department else None,
            "company_employeeId": employee.company_employeeId,
            "salary": employee.salary if employee.salary is not None else 0,
            "startDate": employee.startDate,
            "companyRoleType": employee.companyRoleType,
            "empType": employee.empType,
            "bossId": employee.bossId or "",
        })

    return response

async def register_member(
    emp_data: CompanyEmployeePost, companyId: str ,db: AsyncSession
):
    # ตรวจสอบว่าบริษัทมีอยู่จริงหรือไม่
    company = await db.get(Company, companyId)
    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company not found"
        )

    # ตรวจสอบว่ามี Member ในระบบหรือไม่
    result = await db.execute(
        select(Member).where(Member.email == emp_data.member.email)
    )
    member = result.scalar_one_or_none()

    temporary_password = None
    if not member:
        # ถ้าไม่มี Member สร้างใหม่
        member = Member(
            username=emp_data.member.email,
            email=emp_data.member.email,
            firstName=emp_data.member.firstName,
            lastName=emp_data.member.lastName,
            picture=emp_data.member.picture,
            phoneNumber=emp_data.member.phoneNumber,
            birthDate=emp_data.member.birthDate,
            address=emp_data.member.address,
            emergencyContactName=emp_data.member.emergencyContactName,
            emergencyContactPhone=emp_data.member.emergencyContactPhone,
            attachmentUrls=emp_data.member.attachmentUrls,
            role=RoleType.MEMBER,
            status=StatusType.ENABLE,
        )
        from ..security.passwords import apply_temp_password
        temporary_password = apply_temp_password(member)
        db.add(member)
        await db.commit()
        await db.refresh(member)

    # ตรวจสอบว่าพนักงานมีอยู่ในบริษัทนี้แล้วหรือไม่
    result = await db.execute(
        select(CompanyEmployee).where(
            CompanyEmployee.memberId == member.memberId,
            CompanyEmployee.companyId == company.companyId
        )
    )
    existing_employee = result.scalar_one_or_none()

    if existing_employee:
        raise HTTPException(
            status_code=400,
            detail="Member is already registered in this company"
        )

    if not emp_data.position or not emp_data.department:
        raise HTTPException(
            status_code=400,
            detail="กรุณาเลือกแผนกและตำแหน่ง",
        )

    # เพิ่มพนักงานในบริษัท
    new_employee = CompanyEmployee(
        memberId=member.memberId,
        companyId=company.companyId,
        positionId=emp_data.position.positionId,
        departmentId=emp_data.department.departmentId,
        employeeId=emp_data.employeeId or "",
        bossId=emp_data.bossId or "",
        salary=emp_data.salary if emp_data.salary is not None else 0,
        companyRoleType=emp_data.companyRoleType,
        empType=emp_data.empType,
        startDate=emp_data.startDate or datetime.utcnow(),
    )
    db.add(new_employee)
    await db.commit()
    await db.refresh(new_employee)

    return {
        "member": {
            "memberId": str(member.memberId),
            "email": member.email,
            "firstName": member.firstName,
            "lastName": member.lastName,
            "picture": member.picture,
        },
        "position": emp_data.position.dict() if emp_data.position else None,
        "department": emp_data.department.dict() if emp_data.department else None,
        "companyId" : company.companyId,
        "company_employeeId": str(new_employee.company_employeeId),
        "employeeId": new_employee.employeeId,
        "salary": new_employee.salary,
        "bossId": new_employee.bossId,
        "companyRoleType": new_employee.companyRoleType,
        "empType": new_employee.empType,
        "startDate": new_employee.startDate,
        "temporaryPassword": temporary_password,
    }
    
async def update_company_employee(
    company_employee_data: CompanyEmployeeUpdate,
    companyId: str,
    db: AsyncSession
):
    # ดึงข้อมูล CompanyEmployee
    company_employee = await get_company_employee_by_id(company_employee_data.company_employeeId, companyId, db)

    # รับข้อมูลที่เกี่ยวข้อง
    member_info = company_employee_data.member
    position_info = company_employee_data.position
    department_info = company_employee_data.department

    # อัปเดตข้อมูล CompanyEmployee
    # for key, value in company_employee_data.items():
    #     if hasattr(company_employee, key) and value is not None:
    #         setattr(company_employee, key, value)
    if company_employee:
        # Frontend sends null for blank optional strings — store "" not NULL
        company_employee.employeeId = company_employee_data.employeeId or ""
        company_employee.salary = (
            company_employee_data.salary
            if company_employee_data.salary is not None
            else 0
        )
        company_employee.bossId = company_employee_data.bossId or ""
        company_employee.companyRoleType = company_employee_data.companyRoleType
        company_employee.empType = company_employee_data.empType
        if company_employee_data.startDate is not None:
            company_employee.startDate = company_employee_data.startDate
    # อัปเดตข้อมูล Member
    if member_info:
        member = await db.get(Member, company_employee.memberId)
        if member:
            if member_info.firstName is not None:
                member.firstName = member_info.firstName
            if member_info.lastName is not None:
                member.lastName = member_info.lastName
            if member_info.email is not None:
                member.email = member_info.email
            if member_info.picture is not None:
                member.picture = member_info.picture
            if member_info.phoneNumber is not None:
                member.phoneNumber = member_info.phoneNumber
            if member_info.birthDate is not None:
                member.birthDate = member_info.birthDate
            if member_info.address is not None:
                member.address = member_info.address
            if member_info.emergencyContactName is not None:
                member.emergencyContactName = member_info.emergencyContactName
            if member_info.emergencyContactPhone is not None:
                member.emergencyContactPhone = member_info.emergencyContactPhone
            if member_info.attachmentUrls is not None:
                member.attachmentUrls = member_info.attachmentUrls

    # อัปเดตข้อมูล Position
    if position_info:
        company_employee.positionId = position_info.positionId

    # อัปเดตข้อมูล Department
    if department_info:
        company_employee.departmentId = department_info.departmentId

    await db.commit()

    # Re-load with relationships (async session expires them after commit)
    company_employee = await get_company_employee_by_id(
        str(company_employee_data.company_employeeId), companyId, db
    )
    position = company_employee.position
    department = company_employee.department
    return {
        "member": _member_dict(company_employee.member),
        "companyId": company_employee.companyId,
        "position": {
            "positionId": position.positionId,
            "thName": position.thName,
            "engName": position.engName,
        }
        if position
        else None,
        "department": {
            "departmentId": department.departmentId,
            "thName": department.thName,
            "engName": department.engName,
        }
        if department
        else None,
        "company_employeeId": company_employee.company_employeeId,
        "employeeId": company_employee.employeeId or "",
        "salary": company_employee.salary if company_employee.salary is not None else 0,
        "bossId": company_employee.bossId or "",
        "companyRoleType": company_employee.companyRoleType,
        "empType": company_employee.empType,
        "startDate": company_employee.startDate,
    }



# ลบ CompanyEmployee ตาม company_employeeId และ companyId
async def delete_company_employee(company_employeeId: str, companyId: str, db: AsyncSession):
    from ..utils.soft_delete import mark_deleted

    company_employee = await get_company_employee_by_id(company_employeeId, companyId, db)
    mark_deleted(company_employee)
    await db.commit()

# ค้นหาบริษัทที่ memberId อยู่
async def get_companies_by_member(memberId: str, db: AsyncSession):
    result = await db.execute(
        select(Company)
        .join(CompanyEmployee, Company.companyId == CompanyEmployee.companyId)
        .where(CompanyEmployee.memberId == memberId),
    )
    companies = result.scalars().all()

    if not companies:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No companies found for the given memberId"
        )

    return companies

# ค้นหาบริษัทที่ memberId อยู่
async def get_companies_admin(memberId: str, db: AsyncSession):
    result = await db.execute(
        select(Company)
        .join(CompanyEmployee, Company.companyId == CompanyEmployee.companyId)
        .where(CompanyEmployee.memberId == memberId,
               CompanyEmployee.companyRoleType == 'ADMIN_COMPANY'
        ),
    )
    companies = result.scalars().all()

    if not companies:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No companies found for Admin"
        )

    return companies