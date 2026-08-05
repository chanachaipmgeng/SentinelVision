from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import io

from ..schemas.company_schema import CompanyResponse
from ..config.database import get_db
from ..controllers.company_employee_controller import (
    get_all_companyEmployees,
    get_company_employee_by_id,
    get_company_sub_employee_by_id,
    update_company_employee,
    delete_company_employee,
    register_member,
    get_companies_by_member,
    get_companies_admin,
    get_company_member_by_id,
)
from ..controllers.employee_import_controller import (
    build_employee_import_template,
    import_employees_from_excel,
)
from ..schemas.company_employee_schema import (
    CompanyEmployeePost,
    CompanyEmployeeUpdate,
    CompanyEmployeeResponse,
    EmployeeImportResult,
)
router = APIRouter()

# ดึงข้อมูลพนักงานในบริษัททั้งหมดตาม companyId
@router.get("/company/{companyId}", response_model=List[CompanyEmployeeResponse])
async def get_companyEmployees_route(companyId: str, db: AsyncSession = Depends(get_db)):
    return await get_all_companyEmployees(companyId, db)


# Excel import template (must be registered before /{company_employeeId})
@router.get("/company/{companyId}/import-template")
async def download_employee_import_template_route(
    companyId: str, db: AsyncSession = Depends(get_db)
):
    data = await build_employee_import_template(companyId, db)
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="employee-import-template.xlsx"'
        },
    )


@router.post("/company/{companyId}/import", response_model=EmployeeImportResult)
async def import_employees_excel_route(
    companyId: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    return await import_employees_from_excel(companyId, file, db)


# ดึงข้อมูลพนักงานในบริษัทตาม company_employeeId และ companyId
@router.get("/company/{companyId}/{company_employeeId}", response_model=CompanyEmployeeResponse)
async def get_company_employee_by_id_route(companyId: str, company_employeeId: str, db: AsyncSession = Depends(get_db)):
    return await get_company_employee_by_id(company_employeeId, companyId, db)

# ดึงข้อมูลพนักงานในบริษัทตาม memberId และ companyId
@router.get("/company/{companyId}/member/{memberId}", response_model=CompanyEmployeeResponse)
async def get_company_member_by_id_route(companyId: str, memberId: str, db: AsyncSession = Depends(get_db)):
    return await get_company_member_by_id(memberId, companyId, db)

# ดึงลูกน้อง company_employeeId และ companyId
@router.get("/company/sub/{companyId}/{company_employeeId}", response_model=List[CompanyEmployeeResponse])
async def get_company_sub_employee_by_id_route(companyId: str, company_employeeId: str, db: AsyncSession = Depends(get_db)):
    return await get_company_sub_employee_by_id(company_employeeId, companyId, db)

# เพิ่มสมาชิกใหม่หรือนำสมาชิกที่มีอยู่แล้วเข้าสู่บริษัท
@router.post("/company/{companyId}", response_model=CompanyEmployeeResponse)
async def register_member_route(
    companyId: str, 
    member_data: CompanyEmployeePost, 
    db: AsyncSession = Depends(get_db)
):
    return await register_member(member_data, companyId, db)

# แก้ไขข้อมูลพนักงานในบริษัทตาม company_employeeId และ companyId
@router.put("/company/{companyId}", response_model=CompanyEmployeeResponse)
async def update_company_employee_route(companyId: str, company_employee: CompanyEmployeeUpdate, db: AsyncSession = Depends(get_db)):
    return await update_company_employee(company_employee, companyId,db)

# ลบพนักงานออกจากบริษัทตาม company_employeeId และ companyId
@router.delete("/company/{companyId}/{company_employeeId}")
async def delete_company_employee_route(companyId: str, company_employeeId: str, db: AsyncSession = Depends(get_db)):
    await delete_company_employee(company_employeeId, companyId, db)
    return {"detail": "Company Employee deleted successfully"}

@router.get("/member/{memberId}/companies", response_model=List[CompanyResponse])
async def get_companies_by_member_route(memberId: str, db: AsyncSession = Depends(get_db)):
    return await get_companies_by_member(memberId, db)

@router.get("/member/{memberId}/companies-admin", response_model=List[CompanyResponse])
async def get_companies_by_admin_route(memberId: str, db: AsyncSession = Depends(get_db)):
    return await get_companies_admin(memberId, db)
