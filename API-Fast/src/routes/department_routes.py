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
from ..security.deps import assert_request_company_access

router = APIRouter()

@router.get("", response_model=List[DepartmentResponse])
async def get_departments_route(db: AsyncSession = Depends(get_db)):
    return await get_all_departments(db)

@router.get("/{departmentId}", response_model=DepartmentResponse)
async def get_department_by_id_route(departmentId: str, db: AsyncSession = Depends(get_db)):
    return await get_department_by_id(departmentId, db)

@router.get("/company/{companyId}", response_model=List[DepartmentResponse])
async def get_departments_by_companyId_route(companyId: str, db: AsyncSession = Depends(get_db)):
    return await get_departments_by_companyId(companyId, db)

@router.post("", response_model=DepartmentResponse)
async def create_department_route(request: Request, department: DepartmentCreate, db: AsyncSession = Depends(get_db)):
    await assert_request_company_access(request, db, department.companyId)
    return await create_department(department.dict(), db)

@router.put("/{departmentId}", response_model=DepartmentResponse)
async def update_department_route(request: Request, departmentId: str, department: DepartmentUpdate, db: AsyncSession = Depends(get_db)):
    existing = await get_department_by_id(departmentId, db)
    await assert_request_company_access(request, db, existing.companyId)
    return await update_department(departmentId, department.dict(exclude_unset=True), db)

@router.delete("/{departmentId}")
async def delete_department_route(request: Request, departmentId: str, db: AsyncSession = Depends(get_db)):
    existing = await get_department_by_id(departmentId, db)
    await assert_request_company_access(request, db, existing.companyId)
    await delete_department(departmentId, db)
    return {"detail": "Department deleted successfully"}
