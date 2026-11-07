from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ..config.database import get_db
from ..controllers.department_controller import (
    get_all_departments,
    get_department_by_id,
    get_departments_by_companyId,
    create_department,
    update_department,
    delete_department
)
from ..schemas.department_schema import DepartmentCreate, DepartmentUpdate, DepartmentResponse
from ..models.member import Member
from ..security.deps import (
    assert_request_permission,
    require_permission,
    require_request_system_admin,
)

router = APIRouter()

@router.get("", response_model=List[DepartmentResponse])
async def get_departments_route(request: Request, db: AsyncSession = Depends(get_db)):
    """Cross-tenant listing — system admin only (Web-Manage uses /company/{companyId})."""
    require_request_system_admin(request)
    return await get_all_departments(db)

@router.get("/{departmentId}", response_model=DepartmentResponse)
async def get_department_by_id_route(request: Request, departmentId: str, db: AsyncSession = Depends(get_db)):
    department = await get_department_by_id(departmentId, db)
    await assert_request_permission(request, db, "departments.read", department.companyId)
    return department

@router.get("/company/{companyId}", response_model=List[DepartmentResponse])
async def get_departments_by_companyId_route(
    companyId: str,
    db: AsyncSession = Depends(get_db),
    _: Member = Depends(require_permission("departments.read")),
):
    return await get_departments_by_companyId(companyId, db)

@router.post("", response_model=DepartmentResponse)
async def create_department_route(request: Request, department: DepartmentCreate, db: AsyncSession = Depends(get_db)):
    await assert_request_permission(request, db, "departments.write", department.companyId)
    return await create_department(department.dict(), db)

@router.put("/{departmentId}", response_model=DepartmentResponse)
async def update_department_route(request: Request, departmentId: str, department: DepartmentUpdate, db: AsyncSession = Depends(get_db)):
    existing = await get_department_by_id(departmentId, db)
    await assert_request_permission(request, db, "departments.write", existing.companyId)
    if department.companyId is not None and department.companyId != existing.companyId:
        await assert_request_permission(request, db, "departments.write", department.companyId)
    return await update_department(departmentId, department.dict(exclude_unset=True), db)

@router.delete("/{departmentId}")
async def delete_department_route(request: Request, departmentId: str, db: AsyncSession = Depends(get_db)):
    existing = await get_department_by_id(departmentId, db)
    await assert_request_permission(request, db, "departments.write", existing.companyId)
    await delete_department(departmentId, db)
    return {"detail": "Department deleted successfully"}
