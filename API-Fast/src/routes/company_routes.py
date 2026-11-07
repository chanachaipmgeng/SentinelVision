from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from ..config.database import get_db
from ..controllers.company_controller import (
    get_all_companies,
    get_company_by_id,
    create_company,
    update_company,
)
from ..schemas.company_schema import CompanyUpdate, CompanyResponse, CompanyBase
from uuid import UUID

from sqlalchemy import select
from ..services.audit_service import AuditLog
from ..security.deps import require_system_admin, assert_request_company_access
from ..models.member import Member
from ..services import tenant_quota_service as tenant_svc

router = APIRouter()


def _company_public(company) -> dict:
    """Serialize company including D5 lifecycle/quota fields for admin UI."""
    return {
        "companyId": company.companyId,
        "companyName": company.companyName,
        "companyCode": company.companyCode,
        "companyInfo": company.companyInfo,
        "address": company.address,
        "latitude": company.latitude,
        "longitude": company.longitude,
        "picture": company.picture or "",
        "status": getattr(company.status, "value", company.status),
        "ownerName": company.ownerName or "",
        "contact": company.contact or "",
        "createdAt": company.createdAt,
        "updatedAt": company.updatedAt,
        "lifecycleStatus": getattr(company, "lifecycleStatus", None) or "ACTIVE",
        "suspendedAt": getattr(company, "suspendedAt", None),
        "offboardedAt": getattr(company, "offboardedAt", None),
        "packageCode": getattr(company, "packageCode", None),
        "maxDevices": getattr(company, "maxDevices", None),
        "maxEmployees": getattr(company, "maxEmployees", None),
        "gpuPriority": int(getattr(company, "gpuPriority", 0) or 0),
    }


@router.get("")
async def get_companies_route(
    db: AsyncSession = Depends(get_db),
    _admin: Member = Depends(require_system_admin),
):
    rows = await get_all_companies(db)
    return [_company_public(c) for c in rows]


@router.get("/{companyId}")
async def get_company_by_id_route(
    companyId: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    company = await get_company_by_id(companyId, db)
    return _company_public(company)


@router.post("", response_model=CompanyResponse)
async def create_company_route(
    company: CompanyBase,
    db: AsyncSession = Depends(get_db),
    _admin: Member = Depends(require_system_admin),
):
    return await create_company(company.dict(), db)


@router.put("/{companyId}", response_model=CompanyResponse)
async def update_company_route(
    companyId: str,
    company_update: CompanyUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: Member = Depends(require_system_admin),
):
    return await update_company(companyId, company_update.dict(exclude_unset=True), db)


@router.get("/{companyId}/audit-logs")
async def list_audit_logs(
    companyId: str,
    request: Request,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
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


# ---------------------------------------------------------------------------
# D5 tenant lifecycle + quotas (system admin)
# ---------------------------------------------------------------------------
@router.get("/{companyId}/tenant")
async def get_tenant_admin(
    companyId: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Member = Depends(require_system_admin),
):
    company = await get_company_by_id(str(companyId), db)
    usage = await tenant_svc.get_usage(db, company)
    return tenant_svc.serialize_tenant_admin(company, usage=usage)


@router.post("/{companyId}/suspend")
async def suspend_company(
    companyId: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Member = Depends(require_system_admin),
):
    company = await get_company_by_id(str(companyId), db)
    company = await tenant_svc.suspend_company(db, company)
    usage = await tenant_svc.get_usage(db, company)
    return tenant_svc.serialize_tenant_admin(company, usage=usage)


@router.post("/{companyId}/resume")
async def resume_company(
    companyId: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Member = Depends(require_system_admin),
):
    company = await get_company_by_id(str(companyId), db)
    company = await tenant_svc.resume_company(db, company)
    usage = await tenant_svc.get_usage(db, company)
    return tenant_svc.serialize_tenant_admin(company, usage=usage)


@router.post("/{companyId}/offboard")
async def offboard_company(
    companyId: UUID,
    body: dict | None = None,
    db: AsyncSession = Depends(get_db),
    _admin: Member = Depends(require_system_admin),
):
    company = await get_company_by_id(str(companyId), db)
    purge = True if not body else bool((body or {}).get("purgeDevices", True))
    company = await tenant_svc.offboard_company(db, company, purge_devices=purge)
    usage = await tenant_svc.get_usage(db, company)
    return tenant_svc.serialize_tenant_admin(company, usage=usage)


@router.get("/{companyId}/quotas")
async def get_quotas(
    companyId: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Member = Depends(require_system_admin),
):
    company = await get_company_by_id(str(companyId), db)
    usage = await tenant_svc.get_usage(db, company)
    return tenant_svc.serialize_tenant_admin(company, usage=usage)


@router.put("/{companyId}/quotas")
async def put_quotas(
    companyId: UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    _admin: Member = Depends(require_system_admin),
):
    company = await get_company_by_id(str(companyId), db)
    company = await tenant_svc.update_quotas(db, company, body or {})
    # Mirror package allowedModules into modules:{companyId} when package applied.
    if body and body.get("packageCode"):
        from ..services.company_module_service import (
            get_company_module_config,
            save_company_module_config,
            PACKAGE_PRESETS_MODULES,
        )
        code = str(body["packageCode"]).strip().upper()
        allowed = PACKAGE_PRESETS_MODULES.get(code)
        if allowed is not None:
            cfg = await get_company_module_config(db, companyId)
            cfg["enabledModules"] = [m for m in cfg.get("enabledModules", []) if m in allowed]
            cfg["packageCode"] = code
            cfg["quotas"] = {
                "maxDevices": company.maxDevices,
                "maxEmployees": company.maxEmployees,
                "gpuPriority": company.gpuPriority,
            }
            await save_company_module_config(db, companyId, cfg)
    usage = await tenant_svc.get_usage(db, company)
    return tenant_svc.serialize_tenant_admin(company, usage=usage)
