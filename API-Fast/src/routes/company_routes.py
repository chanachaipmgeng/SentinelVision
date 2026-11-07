from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..config.database import get_db
from ..controllers.company_controller import (
    get_all_companies,
    get_company_by_id,
    create_company,
    update_company,
)
from ..models.member import Member
from ..schemas.company_schema import CompanyUpdate, CompanyResponse, CompanyBase
from ..security.deps import (
    assert_request_company_access,
    require_permission,
    require_system_admin,
)
from ..services.audit_service import AuditLog
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
    _: Member = Depends(require_system_admin),
):
    rows = await get_all_companies(db)
    return [_company_public(c) for c in rows]


@router.get("/{companyId}")
async def get_company_by_id_route(
    companyId: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: Member = Depends(require_permission("company.read")),
):
    await assert_request_company_access(request, db, companyId)
    company = await get_company_by_id(companyId, db)
    return _company_public(company)


@router.post("", response_model=CompanyResponse)
async def create_company_route(
    company: CompanyBase,
    db: AsyncSession = Depends(get_db),
    _: Member = Depends(require_system_admin),
):
    return await create_company(company.dict(), db)


@router.put("/{companyId}", response_model=CompanyResponse)
async def update_company_route(
    companyId: str,
    company_update: CompanyUpdate,
    db: AsyncSession = Depends(get_db),
    _: Member = Depends(require_permission("company.settings")),
):
    return await update_company(companyId, company_update.dict(exclude_unset=True), db)


@router.get("/{companyId}/audit-logs")
async def list_audit_logs(
    companyId: str,
    request: Request,
    limit: int = 100,
    offset: int = 0,
    q: Optional[str] = None,
    actor: Optional[str] = None,
    action: Optional[str] = None,
    resource: Optional[str] = None,
    entityType: Optional[str] = None,
    dateFrom: Optional[str] = None,
    dateTo: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: Member = Depends(require_permission("audit.read")),
):
    """Searchable audit log: actor / action / resource / date range / free-text."""
    from datetime import datetime, timezone

    from sqlalchemy import and_, or_

    await assert_request_company_access(request, db, companyId)
    clauses = [AuditLog.companyId == companyId]
    actor_q = (actor or "").strip()
    if actor_q:
        try:
            clauses.append(AuditLog.actorMemberId == UUID(actor_q))
        except ValueError:
            clauses.append(AuditLog.actorRole.ilike(f"%{actor_q}%"))
    action_q = (action or "").strip()
    if action_q:
        clauses.append(AuditLog.action.ilike(f"%{action_q}%"))
    resource_q = (resource or entityType or "").strip()
    if resource_q:
        clauses.append(
            or_(
                AuditLog.entityType.ilike(f"%{resource_q}%"),
                AuditLog.entityId.ilike(f"%{resource_q}%"),
                AuditLog.path.ilike(f"%{resource_q}%"),
            )
        )
    free = (q or "").strip()
    if free:
        clauses.append(
            or_(
                AuditLog.action.ilike(f"%{free}%"),
                AuditLog.path.ilike(f"%{free}%"),
                AuditLog.entityType.ilike(f"%{free}%"),
                AuditLog.entityId.ilike(f"%{free}%"),
                AuditLog.actorRole.ilike(f"%{free}%"),
                AuditLog.ip.ilike(f"%{free}%"),
            )
        )

    def _parse_dt(raw: Optional[str], *, end: bool = False) -> Optional[datetime]:
        if not raw:
            return None
        text = raw.strip()
        try:
            if len(text) == 10:
                text = f"{text}T23:59:59.999Z" if end else f"{text}T00:00:00Z"
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    df = _parse_dt(dateFrom, end=False)
    dt = _parse_dt(dateTo, end=True)
    if df is not None:
        clauses.append(AuditLog.occurredAt >= df)
    if dt is not None:
        clauses.append(AuditLog.occurredAt <= dt)

    lim = min(max(int(limit or 100), 1), 500)
    off = max(int(offset or 0), 0)
    rows = (
        await db.execute(
            select(AuditLog)
            .where(and_(*clauses))
            .order_by(AuditLog.occurredAt.desc())
            .offset(off)
            .limit(lim)
        )
    ).scalars().all()
    return [
        {
            "id": str(r.id),
            "occurredAt": r.occurredAt.isoformat() if r.occurredAt else None,
            "actorMemberId": str(r.actorMemberId) if r.actorMemberId else None,
            "actorRole": r.actorRole,
            "action": r.action,
            "entityType": r.entityType,
            "entityId": r.entityId,
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
