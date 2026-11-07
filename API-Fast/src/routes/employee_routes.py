from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import io
# Request used by mutating routes for actor + AuthzMiddleware state.

from ..schemas.company_schema import CompanyResponse
from ..config.database import get_db
from ..models.member import Member
from ..security.deps import current_member_var, require_permission
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
from ..services.idempotency_service import idempotent_json
from ..services.rate_limit_service import rate_limit_import

router = APIRouter()

# ดึงข้อมูลพนักงานในบริษัททั้งหมดตาม companyId
@router.get("/company/{companyId}", response_model=List[CompanyEmployeeResponse])
async def get_companyEmployees_route(
    companyId: str,
    limit: int | None = None,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _: Member = Depends(require_permission("employees.read")),
):
    return await get_all_companyEmployees(companyId, db, limit=limit, offset=offset)


# Excel import template (must be registered before /{company_employeeId})
@router.get("/company/{companyId}/import-template")
async def download_employee_import_template_route(
    companyId: str,
    db: AsyncSession = Depends(get_db),
    _: Member = Depends(require_permission("employees.write")),
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
    request: Request,
    companyId: str,
    file: UploadFile = File(...),
    photos: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
    _: Member = Depends(require_permission("employees.write")),
    _rl=Depends(rate_limit_import),
):
    async def _run():
        return await import_employees_from_excel(companyId, file, db, photos=photos)

    return await idempotent_json(
        request, scope="employees.import", company_id=companyId, compute=_run
    )


# ดึงข้อมูลพนักงานในบริษัทตาม company_employeeId และ companyId
@router.get("/company/{companyId}/{company_employeeId}", response_model=CompanyEmployeeResponse)
async def get_company_employee_by_id_route(
    companyId: str,
    company_employeeId: str,
    db: AsyncSession = Depends(get_db),
    _: Member = Depends(require_permission("employees.read")),
):
    return await get_company_employee_by_id(company_employeeId, companyId, db)

# ดึงข้อมูลพนักงานในบริษัทตาม memberId และ companyId
@router.get("/company/{companyId}/member/{memberId}", response_model=CompanyEmployeeResponse)
async def get_company_member_by_id_route(
    companyId: str,
    memberId: str,
    db: AsyncSession = Depends(get_db),
    _: Member = Depends(require_permission("employees.read")),
):
    return await get_company_member_by_id(memberId, companyId, db)

# ดึงลูกน้อง company_employeeId และ companyId
@router.get("/company/sub/{companyId}/{company_employeeId}", response_model=List[CompanyEmployeeResponse])
async def get_company_sub_employee_by_id_route(
    companyId: str,
    company_employeeId: str,
    db: AsyncSession = Depends(get_db),
    _: Member = Depends(require_permission("employees.read")),
):
    return await get_company_sub_employee_by_id(company_employeeId, companyId, db)

# เพิ่มสมาชิกใหม่หรือนำสมาชิกที่มีอยู่แล้วเข้าสู่บริษัท
@router.post("/company/{companyId}", response_model=CompanyEmployeeResponse)
async def register_member_route(
    companyId: str,
    member_data: CompanyEmployeePost,
    db: AsyncSession = Depends(get_db),
    _: Member = Depends(require_permission("employees.write")),
):
    return await register_member(member_data, companyId, db)

# แก้ไขข้อมูลพนักงานในบริษัทตาม company_employeeId และ companyId
@router.put("/company/{companyId}", response_model=CompanyEmployeeResponse)
async def update_company_employee_route(
    request: Request,
    companyId: str,
    company_employee: CompanyEmployeeUpdate,
    db: AsyncSession = Depends(get_db),
    _: Member = Depends(require_permission("employees.write")),
):
    actor = getattr(request.state, "member", None) or current_member_var.get()
    return await update_company_employee(company_employee, companyId, db, actor=actor)

# ลบพนักงานออกจากบริษัทตาม company_employeeId และ companyId
@router.delete("/company/{companyId}/{company_employeeId}")
async def delete_company_employee_route(
    companyId: str,
    company_employeeId: str,
    db: AsyncSession = Depends(get_db),
    _: Member = Depends(require_permission("employees.write")),
):
    await delete_company_employee(company_employeeId, companyId, db)
    return {"detail": "Company Employee deleted successfully"}

@router.get("/member/{memberId}/companies", response_model=List[CompanyResponse])
async def get_companies_by_member_route(memberId: str, db: AsyncSession = Depends(get_db)):
    return await get_companies_by_member(memberId, db)

@router.get("/member/{memberId}/companies-admin", response_model=List[CompanyResponse])
async def get_companies_by_admin_route(memberId: str, db: AsyncSession = Depends(get_db)):
    return await get_companies_admin(memberId, db)


# B7: the API only validates + persists the upload; the `worker` service processes the job
# (or this process does when RUN_BACKGROUND_JOBS_IN_API=true). UI polls GET .../import-jobs/{jobId}.
@router.post("/company/{companyId}/import-jobs")
async def start_import_job(
    request: Request,
    companyId: str,
    file: UploadFile = File(...),
    photos: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
    _: Member = Depends(require_permission("employees.write")),
    _rl=Depends(rate_limit_import),
):
    from fastapi import HTTPException

    from ..models.company import Company
    from ..services.import_job_service import create_import_job

    if not await db.get(Company, companyId):
        raise HTTPException(status_code=404, detail="Company not found")
    filename = (file.filename or "").lower()
    if not filename.endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="กรุณาอัปโหลดไฟล์ Excel (.xlsx)")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="ไฟล์ว่าง")
    photos_data = None
    if photos is not None and photos.filename:
        if not photos.filename.lower().endswith(".zip"):
            raise HTTPException(status_code=400, detail="ไฟล์รูปต้องเป็น ZIP (.zip) รวมรูป jpg/png")
        photos_data = await photos.read()

    actor = getattr(request.state, "member", None) or current_member_var.get()

    async def _run():
        job = await create_import_job(
            companyId,
            file_name=file.filename,
            data=data,
            photos_name=getattr(photos, "filename", None),
            photos_data=photos_data,
            requested_by=getattr(actor, "memberId", None),
        )
        return {"jobId": str(job.id), "status": job.status, "progress": job.progress}

    return await idempotent_json(
        request, scope="employees.import_job", company_id=companyId, compute=_run
    )


@router.get("/company/{companyId}/import-jobs/{jobId}")
async def get_import_job_route(companyId: str, jobId: str, db: AsyncSession = Depends(get_db)):
    from fastapi import HTTPException

    from ..services.import_job_service import get_import_job

    job = await get_import_job(db, jobId)
    if not job or str(job.companyId) != companyId:
        raise HTTPException(status_code=404, detail="Import job not found")
    return job.to_public()
