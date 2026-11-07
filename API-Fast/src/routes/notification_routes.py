from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.database import get_db
from ..models.system_setting import SystemSetting
from ..security.deps import assert_company_access, get_current_member
from ..services.notification_service import NotificationOutbox, enqueue
from ..services import rbac_service

router = APIRouter()


def _notify_key(company_id: str) -> str:
    return f"notify:{company_id}"


@router.post("/system")
async def system_alert(request: Request, db: AsyncSession = Depends(get_db)):
    """Backup/ops hook. Requires X-Service-Token matching SERVICE_NOTIFY_TOKEN."""
    from ..config.settings import settings

    expected = (getattr(settings, "SERVICE_NOTIFY_TOKEN", "") or "").strip()
    if not expected or request.headers.get("x-service-token") != expected:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Service token required")
    body = await request.json()
    await enqueue(
        str(body.get("event") or "system.alert"),
        "line",
        {"body": str(body.get("body") or "system alert")},
        company_id=body.get("companyId"),
    )
    return {"queued": True}


@router.get("/pending-count")
async def pending_count(
    companyId: Optional[UUID] = None,
    member=Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(func.count()).select_from(NotificationOutbox).where(NotificationOutbox.status == "pending")
    if companyId is not None:
        await assert_company_access(db, member, companyId)
        stmt = stmt.where(NotificationOutbox.companyId == companyId)
    count = (await db.execute(stmt)).scalar_one()
    return {"pending": int(count or 0)}


@router.get("/company/{companyId}/settings")
async def get_notify_settings(
    companyId: UUID,
    request: Request,
    member=Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    await rbac_service.assert_permission(
        db, member, rbac_service.PERM_NOTIFICATIONS_MANAGE, companyId
    )
    row = await db.get(SystemSetting, _notify_key(str(companyId)))
    default_cfg = {
        "email": "",
        "lineToken": "",
        "webhookUrl": "",
        "webhookSecret": "",
        "hasWebhookSecret": False,
        "cutoff": "09:30",
        "events": [
            "attendance.checked_in",
            "attendance.checked_out",
            "attendance.approved",
            "attendance.missing",
            "import.finished",
        ],
    }
    if not row or not isinstance(row.value, dict):
        return default_cfg
    val = dict(row.value)
    secret = str(val.get("webhookSecret") or "")
    return {
        **default_cfg,
        **val,
        "hasWebhookSecret": bool(secret),
    }


@router.put("/company/{companyId}/settings")
async def put_notify_settings(
    companyId: UUID,
    body: dict,
    member=Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    await rbac_service.assert_permission(
        db, member, rbac_service.PERM_NOTIFICATIONS_MANAGE, companyId
    )
    key = _notify_key(str(companyId))
    row = await db.get(SystemSetting, key)
    existing = row.value if (row and isinstance(row.value, dict)) else {}
    raw_secret = (body or {}).get("webhookSecret")
    webhook_secret = (
        str(raw_secret).strip()
        if raw_secret is not None and str(raw_secret).strip() != ""
        else str(existing.get("webhookSecret") or "")
    )
    value = {
        "email": (body or {}).get("email") or "",
        "lineToken": (body or {}).get("lineToken") or "",
        "webhookUrl": (body or {}).get("webhookUrl") or "",
        "webhookSecret": webhook_secret,
        "cutoff": (body or {}).get("cutoff") or "09:30",
        "events": (body or {}).get("events")
        or [
            "attendance.checked_in",
            "attendance.checked_out",
            "attendance.approved",
            "attendance.missing",
        ],
    }
    if row:
        row.value = value
    else:
        db.add(SystemSetting(key=key, value=value))
    await db.commit()
    return {**value, "hasWebhookSecret": bool(webhook_secret)}


@router.post("/company/{companyId}/test")
async def test_notify(
    companyId: UUID,
    member=Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    await rbac_service.assert_permission(
        db, member, rbac_service.PERM_NOTIFICATIONS_MANAGE, companyId
    )
    cid_str = str(companyId)
    row = await db.get(SystemSetting, _notify_key(cid_str))
    value = row.value if (row and isinstance(row.value, dict)) else {}
    queued_channels = []
    if value.get("email"):
        await enqueue(
            "system.test",
            "email",
            {"to": value["email"], "subject": "DPU test", "body": "Notification test"},
            company_id=cid_str,
        )
        queued_channels.append("email")
    if value.get("lineToken"):
        await enqueue(
            "system.test",
            "line",
            {"lineToken": value["lineToken"], "body": "DPU notification test"},
            company_id=cid_str,
        )
        queued_channels.append("line")
    if value.get("webhookUrl"):
        await enqueue(
            "attendance.test",
            "webhook",
            {
                "webhookUrl": value["webhookUrl"],
                "webhookSecret": value.get("webhookSecret") or "",
                "subject": "DPU Signed Payroll Webhook Test",
                "body": "DPU HMAC-SHA256 signed webhook test event",
                "data": {
                    "sample": True,
                    "employeeId": "EMP-001",
                    "punchType": "CHECK_IN",
                    "shiftName": "กะปกติ (09:00-18:00)",
                    "isLate": False,
                    "lateMinutes": 0,
                    "overtimeMinutes": 0,
                },
            },
            company_id=cid_str,
        )
        queued_channels.append("webhook")
    return {"queued": True, "channels": queued_channels}


@router.get("/company/{companyId}/outbox")
async def list_company_outbox(
    companyId: UUID,
    limit: int = 50,
    member=Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    await rbac_service.assert_permission(
        db, member, rbac_service.PERM_NOTIFICATIONS_MANAGE, companyId
    )
    safe_limit = min(max(1, int(limit or 50)), 200)
    rows = (
        await db.execute(
            select(NotificationOutbox)
            .where(NotificationOutbox.companyId == companyId)
            .order_by(NotificationOutbox.createdAt.desc())
            .limit(safe_limit)
        )
    ).scalars().all()
    return [
        {
            "id": str(r.id),
            "companyId": str(r.companyId) if r.companyId else None,
            "event": r.event,
            "channel": r.channel,
            "status": r.status,
            "attempts": int(r.attempts or 0),
            "lastError": r.lastError,
            "createdAt": r.createdAt.isoformat() if r.createdAt else None,
        }
        for r in rows
    ]
