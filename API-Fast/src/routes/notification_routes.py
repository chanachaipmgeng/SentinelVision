"""Notification settings, outbox / dead-letter, templates, prefs, in-app center (D3)."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.database import get_db
from ..models.notification_platform import (
    InAppNotification,
    NotificationPreference,
    NotificationTemplate,
)
from ..models.system_setting import SystemSetting
from ..security.deps import assert_company_access, get_current_member
from ..services.notification_service import NotificationOutbox, enqueue, retry_dead_letter
from ..services.notification_templates import DEFAULT_TEMPLATES, EVENT_I18N_KEYS
from ..services.outbox_crypto import encrypt_secret, redact_payload_for_api

router = APIRouter()


def _notify_key(company_id: str) -> str:
    return f"notify:{company_id}"


def _serialize_outbox(r: NotificationOutbox) -> dict:
    return {
        "id": str(r.id),
        "companyId": str(r.companyId) if r.companyId else None,
        "event": r.event,
        "channel": r.channel,
        "status": r.status,
        "attempts": int(r.attempts or 0),
        "lastError": r.lastError,
        "createdAt": r.createdAt.isoformat() if r.createdAt else None,
        "deadLetteredAt": r.deadLetteredAt.isoformat() if r.deadLetteredAt else None,
        "payload": redact_payload_for_api(r.payload if isinstance(r.payload, dict) else {}),
    }


@router.post("/system")
async def system_alert(request: Request, db: AsyncSession = Depends(get_db)):
    """Backup/ops hook. Requires X-Service-Token matching SERVICE_NOTIFY_TOKEN."""
    from ..config.settings import settings

    expected = (getattr(settings, "SERVICE_NOTIFY_TOKEN", "") or "").strip()
    if not expected or request.headers.get("x-service-token") != expected:
        raise HTTPException(status_code=401, detail="Service token required")
    body = await request.json()
    await enqueue(
        str(body.get("event") or "system.alert"),
        "line",
        {
            "body": str(body.get("body") or "system alert"),
            "lineUserId": body.get("lineUserId") or "",
            "lineToken": body.get("lineToken") or "",
        },
        company_id=body.get("companyId"),
    )
    return {"queued": True}


@router.get("/pending-count")
async def pending_count(
    companyId: Optional[UUID] = None,
    member=Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(func.count()).select_from(NotificationOutbox).where(
        NotificationOutbox.status == "pending"
    )
    if companyId is not None:
        await assert_company_access(db, member, companyId)
        stmt = stmt.where(NotificationOutbox.companyId == companyId)
    count = (await db.execute(stmt)).scalar_one()

    unread_stmt = select(func.count()).select_from(InAppNotification).where(
        InAppNotification.memberId == member.memberId,
        InAppNotification.readAt.is_(None),
    )
    if companyId is not None:
        unread_stmt = unread_stmt.where(InAppNotification.companyId == companyId)
    unread = (await db.execute(unread_stmt)).scalar_one()
    return {"pending": int(count or 0), "unreadInApp": int(unread or 0)}


@router.get("/company/{companyId}/settings")
async def get_notify_settings(
    companyId: UUID,
    member=Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    await assert_company_access(db, member, companyId)
    row = await db.get(SystemSetting, _notify_key(str(companyId)))
    default_cfg = {
        "email": "",
        "lineToken": "",
        "lineChannelAccessToken": "",
        "hasLineToken": False,
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
    line_tok = str(val.get("lineChannelAccessToken") or val.get("lineToken") or "")
    return {
        **default_cfg,
        **val,
        "lineToken": "",  # never echo secret
        "lineChannelAccessToken": "",
        "webhookSecret": "",
        "hasWebhookSecret": bool(secret),
        "hasLineToken": bool(line_tok),
    }


@router.put("/company/{companyId}/settings")
async def put_notify_settings(
    companyId: UUID,
    body: dict,
    member=Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    await assert_company_access(db, member, companyId)
    key = _notify_key(str(companyId))
    row = await db.get(SystemSetting, key)
    existing = row.value if (row and isinstance(row.value, dict)) else {}
    raw_secret = (body or {}).get("webhookSecret")
    webhook_secret = (
        str(raw_secret).strip()
        if raw_secret is not None and str(raw_secret).strip() != ""
        else str(existing.get("webhookSecret") or "")
    )
    raw_line = (body or {}).get("lineChannelAccessToken") or (body or {}).get("lineToken")
    line_token = (
        str(raw_line).strip()
        if raw_line is not None and str(raw_line).strip() != ""
        else str(existing.get("lineChannelAccessToken") or existing.get("lineToken") or "")
    )
    # Store sealed at rest in system_setting when OUTBOX_ENCRYPTION_KEY is set.
    sealed_line = encrypt_secret(line_token) if line_token else ""
    sealed_webhook = encrypt_secret(webhook_secret) if webhook_secret else ""
    value = {
        "email": (body or {}).get("email") or "",
        "lineToken": sealed_line,
        "lineChannelAccessToken": sealed_line,
        "webhookUrl": (body or {}).get("webhookUrl") or "",
        "webhookSecret": sealed_webhook,
        "cutoff": (body or {}).get("cutoff") or "09:30",
        "events": (body or {}).get("events")
        or [
            "attendance.checked_in",
            "attendance.checked_out",
            "attendance.approved",
            "attendance.missing",
            "import.finished",
        ],
    }
    if row:
        row.value = value
    else:
        db.add(SystemSetting(key=key, value=value))
    await db.commit()
    return {
        "email": value["email"],
        "webhookUrl": value["webhookUrl"],
        "cutoff": value["cutoff"],
        "events": value["events"],
        "hasWebhookSecret": bool(webhook_secret),
        "hasLineToken": bool(line_token),
        "lineToken": "",
        "lineChannelAccessToken": "",
        "webhookSecret": "",
    }


@router.post("/company/{companyId}/test")
async def test_notify(
    companyId: UUID,
    member=Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    await assert_company_access(db, member, companyId)
    from ..services.outbox_crypto import decrypt_secret

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
    line_tok = decrypt_secret(
        str(value.get("lineChannelAccessToken") or value.get("lineToken") or "")
    )
    pref = (
        await db.execute(
            select(NotificationPreference).where(
                NotificationPreference.companyId == companyId,
                NotificationPreference.memberId == member.memberId,
            )
        )
    ).scalar_one_or_none()
    line_user = (pref.lineUserId if pref else None) or ""
    if line_tok and line_user:
        await enqueue(
            "system.test",
            "line",
            {
                "lineChannelAccessToken": line_tok,
                "lineUserId": line_user,
                "body": "DPU notification test",
            },
            company_id=cid_str,
        )
        queued_channels.append("line")
    if value.get("webhookUrl"):
        await enqueue(
            "attendance.test",
            "webhook",
            {
                "webhookUrl": value["webhookUrl"],
                "webhookSecret": decrypt_secret(str(value.get("webhookSecret") or "")),
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
    await enqueue(
        "system.test",
        "in_app",
        {
            "memberId": str(member.memberId),
            "subject": "ทดสอบการแจ้งเตือน",
            "body": "ข้อความทดสอบใน Notification Center",
        },
        company_id=cid_str,
    )
    queued_channels.append("in_app")
    return {"queued": True, "channels": queued_channels}


@router.get("/company/{companyId}/outbox")
async def list_company_outbox(
    companyId: UUID,
    limit: int = 50,
    status: Optional[str] = None,
    member=Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    await assert_company_access(db, member, companyId)
    safe_limit = min(max(1, int(limit or 50)), 200)
    stmt = (
        select(NotificationOutbox)
        .where(NotificationOutbox.companyId == companyId)
        .order_by(NotificationOutbox.createdAt.desc())
        .limit(safe_limit)
    )
    if status:
        stmt = stmt.where(NotificationOutbox.status == status)
    rows = (await db.execute(stmt)).scalars().all()
    return [_serialize_outbox(r) for r in rows]


@router.get("/company/{companyId}/dead-letter")
async def list_dead_letter(
    companyId: UUID,
    limit: int = 50,
    member=Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    await assert_company_access(db, member, companyId)
    safe_limit = min(max(1, int(limit or 50)), 200)
    rows = (
        await db.execute(
            select(NotificationOutbox)
            .where(
                NotificationOutbox.companyId == companyId,
                NotificationOutbox.status == "failed",
            )
            .order_by(NotificationOutbox.deadLetteredAt.desc().nullslast())
            .limit(safe_limit)
        )
    ).scalars().all()
    return [_serialize_outbox(r) for r in rows]


@router.post("/company/{companyId}/dead-letter/{outboxId}/retry")
async def retry_dead_letter_row(
    companyId: UUID,
    outboxId: UUID,
    member=Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    await assert_company_access(db, member, companyId)
    row = await db.get(NotificationOutbox, outboxId)
    if not row or row.companyId != companyId:
        raise HTTPException(status_code=404, detail="Outbox row not found")
    ok = await retry_dead_letter(outboxId)
    if not ok:
        raise HTTPException(status_code=400, detail="Row is not in failed/dead-letter state")
    return {"retried": True, "id": str(outboxId)}


# ---------------------------------------------------------------------------
# Templates + i18n key catalog
# ---------------------------------------------------------------------------
@router.get("/i18n-keys")
async def list_i18n_keys(member=Depends(get_current_member)):
    return {"events": EVENT_I18N_KEYS, "builtins": DEFAULT_TEMPLATES}


@router.get("/company/{companyId}/templates")
async def list_templates(
    companyId: UUID,
    member=Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    await assert_company_access(db, member, companyId)
    rows = (
        await db.execute(
            select(NotificationTemplate).where(
                (NotificationTemplate.companyId == companyId)
                | (NotificationTemplate.companyId.is_(None))
            )
        )
    ).scalars().all()
    custom = [
        {
            "templateId": str(r.templateId),
            "companyId": str(r.companyId) if r.companyId else None,
            "eventKey": r.eventKey,
            "locale": r.locale,
            "channel": r.channel,
            "subject": r.subject,
            "bodyTemplate": r.bodyTemplate,
        }
        for r in rows
    ]
    return {"builtins": DEFAULT_TEMPLATES, "custom": custom, "i18nKeys": EVENT_I18N_KEYS}


@router.put("/company/{companyId}/templates")
async def upsert_template(
    companyId: UUID,
    body: dict,
    member=Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    await assert_company_access(db, member, companyId)
    event_key = str((body or {}).get("eventKey") or "").strip()
    locale = str((body or {}).get("locale") or "th")[:10]
    channel = str((body or {}).get("channel") or "line")[:20]
    if not event_key:
        raise HTTPException(status_code=400, detail="eventKey required")
    existing = (
        await db.execute(
            select(NotificationTemplate).where(
                NotificationTemplate.companyId == companyId,
                NotificationTemplate.eventKey == event_key,
                NotificationTemplate.locale == locale,
                NotificationTemplate.channel == channel,
            )
        )
    ).scalar_one_or_none()
    if existing:
        existing.subject = (body or {}).get("subject")
        existing.bodyTemplate = str((body or {}).get("bodyTemplate") or existing.bodyTemplate)
        row = existing
    else:
        row = NotificationTemplate(
            companyId=companyId,
            eventKey=event_key,
            locale=locale,
            channel=channel,
            subject=(body or {}).get("subject"),
            bodyTemplate=str((body or {}).get("bodyTemplate") or ""),
        )
        db.add(row)
    await db.commit()
    return {
        "templateId": str(row.templateId),
        "eventKey": row.eventKey,
        "locale": row.locale,
        "channel": row.channel,
        "subject": row.subject,
        "bodyTemplate": row.bodyTemplate,
    }


# ---------------------------------------------------------------------------
# User preferences
# ---------------------------------------------------------------------------
@router.get("/company/{companyId}/preferences/me")
async def get_my_preferences(
    companyId: UUID,
    member=Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    await assert_company_access(db, member, companyId)
    row = (
        await db.execute(
            select(NotificationPreference).where(
                NotificationPreference.companyId == companyId,
                NotificationPreference.memberId == member.memberId,
            )
        )
    ).scalar_one_or_none()
    if not row:
        return {
            "companyId": str(companyId),
            "memberId": str(member.memberId),
            "channelEmail": True,
            "channelLine": True,
            "channelInApp": True,
            "lineUserId": "",
            "mutedEvents": [],
            "locale": "th",
        }
    return {
        "preferenceId": str(row.preferenceId),
        "companyId": str(row.companyId),
        "memberId": str(row.memberId),
        "channelEmail": bool(row.channelEmail),
        "channelLine": bool(row.channelLine),
        "channelInApp": bool(row.channelInApp),
        "lineUserId": row.lineUserId or "",
        "mutedEvents": row.mutedEvents or [],
        "locale": row.locale or "th",
    }


@router.put("/company/{companyId}/preferences/me")
async def put_my_preferences(
    companyId: UUID,
    body: dict,
    member=Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    await assert_company_access(db, member, companyId)
    row = (
        await db.execute(
            select(NotificationPreference).where(
                NotificationPreference.companyId == companyId,
                NotificationPreference.memberId == member.memberId,
            )
        )
    ).scalar_one_or_none()
    muted = (body or {}).get("mutedEvents")
    if not isinstance(muted, list):
        muted = []
    if row:
        row.channelEmail = bool((body or {}).get("channelEmail", row.channelEmail))
        row.channelLine = bool((body or {}).get("channelLine", row.channelLine))
        row.channelInApp = bool((body or {}).get("channelInApp", row.channelInApp))
        if "lineUserId" in (body or {}):
            row.lineUserId = str(body.get("lineUserId") or "") or None
        row.mutedEvents = muted
        row.locale = str((body or {}).get("locale") or row.locale or "th")[:10]
    else:
        row = NotificationPreference(
            companyId=companyId,
            memberId=member.memberId,
            channelEmail=bool((body or {}).get("channelEmail", True)),
            channelLine=bool((body or {}).get("channelLine", True)),
            channelInApp=bool((body or {}).get("channelInApp", True)),
            lineUserId=str((body or {}).get("lineUserId") or "") or None,
            mutedEvents=muted,
            locale=str((body or {}).get("locale") or "th")[:10],
        )
        db.add(row)
    await db.commit()
    return await get_my_preferences(companyId, member, db)


# ---------------------------------------------------------------------------
# In-app notification center
# ---------------------------------------------------------------------------
@router.get("/company/{companyId}/inbox")
async def list_inbox(
    companyId: UUID,
    limit: int = 50,
    unreadOnly: bool = False,
    member=Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    await assert_company_access(db, member, companyId)
    safe_limit = min(max(1, int(limit or 50)), 200)
    stmt = (
        select(InAppNotification)
        .where(
            InAppNotification.companyId == companyId,
            InAppNotification.memberId == member.memberId,
        )
        .order_by(InAppNotification.createdAt.desc())
        .limit(safe_limit)
    )
    if unreadOnly:
        stmt = stmt.where(InAppNotification.readAt.is_(None))
    rows = (await db.execute(stmt)).scalars().all()
    return [
        {
            "notificationId": str(r.notificationId),
            "event": r.event,
            "title": r.title,
            "body": r.body,
            "readAt": r.readAt.isoformat() if r.readAt else None,
            "createdAt": r.createdAt.isoformat() if r.createdAt else None,
        }
        for r in rows
    ]


@router.post("/company/{companyId}/inbox/{notificationId}/read")
async def mark_inbox_read(
    companyId: UUID,
    notificationId: UUID,
    member=Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    await assert_company_access(db, member, companyId)
    from datetime import datetime, timezone

    row = await db.get(InAppNotification, notificationId)
    if (
        not row
        or row.companyId != companyId
        or row.memberId != member.memberId
    ):
        raise HTTPException(status_code=404, detail="Notification not found")
    if row.readAt is None:
        row.readAt = datetime.now(timezone.utc)
        await db.commit()
    return {"notificationId": str(notificationId), "readAt": row.readAt.isoformat()}


@router.post("/company/{companyId}/inbox/read-all")
async def mark_all_inbox_read(
    companyId: UUID,
    member=Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    await assert_company_access(db, member, companyId)
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    rows = (
        await db.execute(
            select(InAppNotification).where(
                InAppNotification.companyId == companyId,
                InAppNotification.memberId == member.memberId,
                InAppNotification.readAt.is_(None),
            )
        )
    ).scalars().all()
    for r in rows:
        r.readAt = now
    await db.commit()
    return {"marked": len(rows)}
