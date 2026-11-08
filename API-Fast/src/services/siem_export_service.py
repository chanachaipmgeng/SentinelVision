"""F4: SIEM webhook export via notification_outbox channel ``siem``.

Company settings live in ``system_setting`` under key ``siem:{companyId}``
(JSON: ``siemWebhookUrl`` + Fernet-sealed ``siemWebhookSecret``).
"""
from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.system_setting import SystemSetting
from .notification_service import NotificationOutbox, enqueue
from .outbox_crypto import decrypt_secret, encrypt_secret

logger = logging.getLogger("dpu.siem_export")


def siem_settings_key(company_id: str | UUID) -> str:
    return f"siem:{company_id}"


def default_siem_settings() -> dict[str, Any]:
    return {
        "siemWebhookUrl": "",
        "siemWebhookSecret": "",
        "hasSiemWebhookSecret": False,
    }


def public_siem_settings(raw: dict[str, Any] | None) -> dict[str, Any]:
    """API-safe view: never echo the secret."""
    val = dict(raw or {})
    secret = str(val.get("siemWebhookSecret") or "")
    return {
        "siemWebhookUrl": str(val.get("siemWebhookUrl") or ""),
        "siemWebhookSecret": "",
        "hasSiemWebhookSecret": bool(secret),
    }


async def get_siem_settings(db: AsyncSession, company_id: UUID) -> dict[str, Any]:
    row = await db.get(SystemSetting, siem_settings_key(company_id))
    if not row or not isinstance(row.value, dict):
        return default_siem_settings()
    return public_siem_settings(row.value)


async def save_siem_settings(
    db: AsyncSession, company_id: UUID, body: dict[str, Any] | None
) -> dict[str, Any]:
    key = siem_settings_key(company_id)
    row = await db.get(SystemSetting, key)
    existing = row.value if (row and isinstance(row.value, dict)) else {}
    raw_secret = (body or {}).get("siemWebhookSecret")
    secret = (
        str(raw_secret).strip()
        if raw_secret is not None and str(raw_secret).strip() != ""
        else str(existing.get("siemWebhookSecret") or "")
    )
    sealed = encrypt_secret(secret) if secret else ""
    value = {
        "siemWebhookUrl": str((body or {}).get("siemWebhookUrl") or "").strip(),
        "siemWebhookSecret": sealed,
    }
    if row:
        row.value = value
    else:
        db.add(SystemSetting(key=key, value=value))
    await db.commit()
    return public_siem_settings(value)


def _incident_payload_data(incident: Any) -> dict[str, Any]:
    """Build a JSON-friendly incident dict from a model or mapping."""
    if isinstance(incident, dict):
        return dict(incident)

    def _id(val: Any) -> Optional[str]:
        return str(val) if val is not None else None

    occurred = getattr(incident, "occurredAt", None)
    ack_at = getattr(incident, "acknowledgedAt", None)
    return {
        "incidentId": _id(getattr(incident, "incidentId", None)),
        "companyId": _id(getattr(incident, "companyId", None)),
        "eventType": getattr(incident, "eventType", None),
        "severity": getattr(incident, "severity", None),
        "identityId": _id(getattr(incident, "identityId", None)),
        "memberId": _id(getattr(incident, "memberId", None)),
        "subjectName": getattr(incident, "subjectName", None),
        "identityType": getattr(incident, "identityType", None),
        "zoneId": _id(getattr(incident, "zoneId", None)),
        "zoneName": getattr(incident, "zoneName", None),
        "eventId": _id(getattr(incident, "eventId", None)),
        "confidencePercent": getattr(incident, "confidencePercent", None),
        "distance": getattr(incident, "distance", None),
        "snapshotUrl": getattr(incident, "snapshotUrl", None),
        "actionTaken": getattr(incident, "actionTaken", None),
        "acknowledgedBy": _id(getattr(incident, "acknowledgedBy", None)),
        "acknowledgedAt": ack_at.isoformat() if ack_at is not None else None,
        "occurredAt": occurred.isoformat() if occurred is not None else None,
    }


async def queue_siem_incident_export(
    db: AsyncSession,
    company_id: UUID,
    incident: Any,
    *,
    event: str = "sentinel.incident.created",
) -> bool:
    """If SIEM webhook is configured, add a ``siem`` outbox row (caller commits).

    Uses the same session so the export shares the incident transaction.
    """
    row = await db.get(SystemSetting, siem_settings_key(company_id))
    if not row or not isinstance(row.value, dict):
        return False
    url = str(row.value.get("siemWebhookUrl") or "").strip()
    if not url.startswith(("http://", "https://")):
        return False
    secret = decrypt_secret(str(row.value.get("siemWebhookSecret") or ""))
    data = _incident_payload_data(incident)
    subject = data.get("subjectName") or data.get("eventType") or "SentinelVision incident"
    db.add(
        NotificationOutbox(
            companyId=company_id,
            event=event,
            channel="siem",
            payload={
                "webhookUrl": url,
                "webhookSecret": encrypt_secret(secret) if secret else "",
                "subject": f"SIEM: {subject}",
                "body": f"{data.get('eventType') or event} · {subject}",
                "companyId": str(company_id),
                "data": data,
            },
        )
    )
    return True


async def enqueue_siem_test(company_id: UUID) -> dict[str, Any]:
    """Queue a test ping using the worker ``enqueue`` helper (own session/commit)."""
    from ..config.database import async_session

    async with async_session() as db:
        row = await db.get(SystemSetting, siem_settings_key(company_id))
        value = row.value if (row and isinstance(row.value, dict)) else {}
        url = str(value.get("siemWebhookUrl") or "").strip()
        if not url.startswith(("http://", "https://")):
            return {"queued": False, "reason": "siemWebhookUrl not configured"}
        secret = decrypt_secret(str(value.get("siemWebhookSecret") or ""))

    await enqueue(
        "sentinel.siem.test",
        "siem",
        {
            "webhookUrl": url,
            "webhookSecret": secret,
            "subject": "SentinelVision SIEM test",
            "body": "HMAC-SHA256 signed SIEM webhook test event",
            "data": {"sample": True, "channel": "siem"},
        },
        company_id=str(company_id),
    )
    return {"queued": True, "channel": "siem"}
