"""Notification outbox (email / LINE) with retry."""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Integer, String, select
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.sql import func

from ..config.database import Base, async_session
from ..config.settings import settings

logger = logging.getLogger("dpu.notify")


class NotificationOutbox(Base):
    __tablename__ = "notification_outbox"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    companyId = Column(PGUUID(as_uuid=True), nullable=True)
    event = Column(String, nullable=False)
    channel = Column(String, nullable=False)
    payload = Column(JSONB, nullable=False)
    status = Column(String, nullable=False, default="pending")
    attempts = Column(Integer, nullable=False, default=0)
    lastError = Column(String, nullable=True)
    createdAt = Column(DateTime(timezone=True), server_default=func.now())


class ImportJob(Base):
    __tablename__ = "import_job"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    companyId = Column(PGUUID(as_uuid=True), nullable=False)
    status = Column(String, nullable=False, default="pending")
    result = Column(JSONB, nullable=True)
    error = Column(String, nullable=True)
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    finishedAt = Column(DateTime(timezone=True), nullable=True)


async def enqueue(
    event: str,
    channel: str,
    payload: dict[str, Any],
    *,
    company_id: Optional[str] = None,
) -> None:
    async with async_session() as db:
        db.add(
            NotificationOutbox(
                companyId=UUID(str(company_id)) if company_id else None,
                event=event,
                channel=channel,
                payload=payload,
                status="pending",
                attempts=0,
            )
        )
        await db.commit()


def _send_email(payload: dict) -> None:
    if not settings.SMTP_HOST:
        logger.info("notify email skipped (SMTP_HOST empty): %s", payload.get("subject"))
        return
    msg = EmailMessage()
    msg["Subject"] = payload.get("subject") or "DPU Attendance"
    msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
    msg["To"] = payload["to"]
    msg.set_content(payload.get("body") or "")
    with smtplib.SMTP(settings.SMTP_HOST, int(settings.SMTP_PORT), timeout=20) as smtp:
        if settings.SMTP_TLS:
            smtp.starttls()
        if settings.SMTP_USER:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        smtp.send_message(msg)


def _send_line(payload: dict) -> None:
    token = payload.get("lineToken") or settings.LINE_CHANNEL_ACCESS_TOKEN
    if not token:
        logger.info("notify line skipped (no token)")
        return
    import urllib.request

    data = json_bytes({"message": payload.get("body") or payload.get("subject") or ""})
    req = urllib.request.Request(
        "https://notify-api.line.me/api/notify",
        data=data,
        headers={"Authorization": f"Bearer {token}"},
        method="POST",
    )
    # LINE Notify expects form body; Messaging API is different. Use form.
    form = urllib.parse.urlencode({"message": payload.get("body") or ""}).encode()
    req = urllib.request.Request(
        "https://notify-api.line.me/api/notify",
        data=form,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        if resp.status >= 300:
            raise RuntimeError(f"LINE notify HTTP {resp.status}")


def json_bytes(obj) -> bytes:
    import json

    return json.dumps(obj).encode()


import urllib.parse  # noqa: E402


_cutoff_sent: set[str] = set()


async def attendance_cutoff_tick() -> int:
    """Enqueue one late/missing notice per company per day after notify:{id}.cutoff (HH:MM)."""
    from datetime import datetime

    from sqlalchemy import text

    from ..config.database import async_session

    now = datetime.now()
    day = now.date().isoformat()
    queued = 0
    async with async_session() as db:
        rows = (
            await db.execute(text("SELECT key, value FROM system_setting WHERE key LIKE 'notify:%'"))
        ).all()
        for key, value in rows:
            if not isinstance(value, dict):
                continue
            cutoff = str(value.get("cutoff") or "")
            if len(cutoff) < 4 or ":" not in cutoff:
                continue
            hour, minute = cutoff.split(":", 1)
            try:
                if (now.hour, now.minute) < (int(hour), int(minute)):
                    continue
            except ValueError:
                continue
            company_id = str(key).split(":", 1)[-1]
            marker = f"{day}:{company_id}"
            if marker in _cutoff_sent:
                continue
            missing = (
                await db.execute(
                    text(
                        """
                        SELECT count(*) FROM company_employee ce
                        WHERE ce."companyId" = :cid AND ce.deleted_at IS NULL
                          AND NOT EXISTS (
                            SELECT 1 FROM employee_timestamp t
                            WHERE t."company_employeeId" = ce."company_employeeId"
                              AND t."timestamp"::date = CURRENT_DATE
                          )
                        """
                    ),
                    {"cid": company_id},
                )
            ).scalar_one()
            _cutoff_sent.add(marker)
            if int(missing or 0) <= 0:
                continue
            await enqueue(
                "attendance.missing",
                "line" if value.get("lineToken") else "email",
                {
                    "to": value.get("email") or "",
                    "lineToken": value.get("lineToken") or "",
                    "subject": "DPU missing check-in",
                    "body": f"{missing} employees have no check-in today",
                },
                company_id=company_id,
            )
            queued += 1
    return queued


async def drain_outbox(limit: int = 20) -> int:
    sent = 0
    async with async_session() as db:
        rows = (
            await db.execute(
                select(NotificationOutbox)
                .where(NotificationOutbox.status == "pending")
                .order_by(NotificationOutbox.createdAt)
                .limit(limit)
            )
        ).scalars().all()
        for row in rows:
            row.attempts = int(row.attempts or 0) + 1
            try:
                if row.channel == "email":
                    _send_email(row.payload or {})
                elif row.channel == "line":
                    _send_line(row.payload or {})
                else:
                    raise RuntimeError(f"unknown channel {row.channel}")
                row.status = "sent"
                row.lastError = None
                sent += 1
            except Exception as exc:
                row.lastError = str(exc)[:500]
                if row.attempts >= 5:
                    row.status = "failed"
                logger.warning("notify %s failed: %s", row.id, exc)
        await db.commit()
    return sent
