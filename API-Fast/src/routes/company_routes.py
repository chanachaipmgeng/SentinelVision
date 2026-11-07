from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..config.database import get_db
from ..controllers.company_controller import (
    get_all_companies,
    get_company_by_id,
    create_company,
    update_company
)
from ..schemas.company_schema import CompanyUpdate, CompanyResponse , CompanyBase
from typing import List

from sqlalchemy import select
from ..services.audit_service import AuditLog

router = APIRouter()

@router.get("", response_model=List[CompanyResponse])
async def get_companies_route(db: AsyncSession = Depends(get_db)):
    return await get_all_companies(db)

@router.get("/{companyId}", response_model=CompanyResponse)
async def get_company_by_id_route(companyId: str, db: AsyncSession = Depends(get_db)):
    return await get_company_by_id(companyId, db)

@router.post("", response_model=CompanyResponse)
async def create_company_route(company: CompanyBase, db: AsyncSession = Depends(get_db)):
    return await create_company(company.dict(), db)

@router.put("/{companyId}", response_model=CompanyResponse)
async def update_company_route(
    companyId: str, company_update: CompanyUpdate, db: AsyncSession = Depends(get_db)
):
    return await update_company(companyId, company_update.dict(exclude_unset=True), db)

@router.get("/{companyId}/audit-logs")
async def list_audit_logs(
    companyId: str,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(AuditLog)
            .where(AuditLog.companyId == companyId)
            .order_by(AuditLog.occurredAt.desc())
            .limit(min(max(limit, 1), 500))
        )
    ).scalars().all()
    return [
        {
            "id": str(r.id),
            "occurredAt": r.occurredAt.isoformat() if r.occurredAt else None,
            "actorMemberId": str(r.actorMemberId) if r.actorMemberId else None,
            "actorRole": r.actorRole,
            "action": r.action,
            "path": r.path,
            "statusCode": r.statusCode,
            "ip": r.ip,
        }
        for r in rows
    ]
