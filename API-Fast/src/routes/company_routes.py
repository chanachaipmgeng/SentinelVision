from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from ..config.database import get_db
from ..controllers.company_controller import (
    get_all_companies,
    get_company_by_id,
    create_company,
    update_company,
    delete_company
)
from ..schemas.company_schema import CompanyUpdate, CompanyResponse , CompanyBase
from typing import List

router = APIRouter()

@router.get("/", response_model=List[CompanyResponse])
async def get_companies_route(db: AsyncSession = Depends(get_db)):
    return await get_all_companies(db)

@router.get("/{companyId}", response_model=CompanyResponse)
async def get_company_by_id_route(companyId: str, db: AsyncSession = Depends(get_db)):
    return await get_company_by_id(companyId, db)

@router.post("/", response_model=CompanyResponse)
async def create_company_route(company: CompanyBase, db: AsyncSession = Depends(get_db)):
    return await create_company(company.dict(), db)

@router.put("/{companyId}", response_model=CompanyResponse)
async def update_company_route(
    companyId: str, company_update: CompanyUpdate, db: AsyncSession = Depends(get_db)
):
    return await update_company(companyId, company_update.dict(exclude_unset=True), db)

@router.delete("/{companyId}")
async def delete_company_route(companyId: str, db: AsyncSession = Depends(get_db)):
    return await delete_company(companyId, db)
