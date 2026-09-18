from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.database import get_db
from ..models.system_setting import SystemSetting
from ..security.deps import get_current_member
from ..services.notification_service import NotificationOutbox, enqueue

router = APIRouter()


def _notify_key(company_id: str) -> str:
    return f"notify:{company_id}"


@router.get("/pending-count")
async def pending_count(_member=Depends(get_current_member), db: AsyncSession = Depends(get_db)):
    count = (
        await db.execute(
            select(func.count()).select_from(NotificationOutbox).where(NotificationOutbox.status == "pending")
        )
    ).scalar_one()
    return {"pending": int(count or 0)}


@router.get("/company/{companyId}/settings")
async def get_notify_settings(companyId: str, db: AsyncSession = Depends(get_db)):
    row = await db.get(SystemSetting, _notify_key(companyId))
    return row.value if row else {"email": "", "lineToken": "", "events": ["import.finished", "approval.pending"]}


@router.put("/company/{companyId}/settings")
async def put_notify_settings(companyId: str, body: dict, db: AsyncSession = Depends(get_db)):
    key = _notify_key(companyId)
    row = await db.get(SystemSetting, key)
    value = {
        "email": (body or {}).get("email") or "",
        "lineToken": (body or {}).get("lineToken") or "",
        "events": (body or {}).get("events") or [],
    }
    if row:
        row.value = value
    else:
        db.add(SystemSetting(key=key, value=value))
    await db.commit()
    return value


@router.post("/company/{companyId}/test")
async def test_notify(companyId: str, db: AsyncSession = Depends(get_db)):
    row = await db.get(SystemSetting, _notify_key(companyId))
    value = row.value if row else {}
    if value.get("email"):
        await enqueue(
            "system.test",
            "email",
            {"to": value["email"], "subject": "DPU test", "body": "Notification test"},
            company_id=companyId,
        )
    if value.get("lineToken"):
        await enqueue(
            "system.test",
            "line",
            {"lineToken": value["lineToken"], "body": "DPU notification test"},
            company_id=companyId,
        )
    return {"queued": True}
