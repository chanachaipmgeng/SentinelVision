"""Notification outbox (email / LINE / Telegram / Discord / HMAC webhook) with multi-replica locking & non-blocking I/O."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
import hashlib
import hmac
import json
import logging
import smtplib
import time
from typing import Any, Optional
import urllib.parse
import urllib.request
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, Integer, String, and_, or_, select, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from ..config.database import Base, async_session
from ..config.settings import settings
from ..models.import_job import ImportJob  # noqa: F401  re-exported for existing importers (B7 moved it)
from ..models.system_setting import SystemSetting
from .notification_templates import builtin_template, render_template
from .observability import (
    outbox_claims_total,
    outbox_deliveries_total,
    outbox_delivery_duration_seconds,
    set_outbox_backlog,
)
from .outbox_crypto import seal_payload_secrets, unseal_payload_secrets

logger = logging.getLogger("dpu.notify")


class NotificationOutbox(Base):
    __tablename__ = "notification_outbox"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    companyId: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    event: Mapped[str] = mapped_column(String, nullable=False)
    channel: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[Any] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lastError: Mapped[str | None] = mapped_column(String, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deadLetteredAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    nextAttemptAt: Mapped[datetime | None] = mapped_column("next_attempt_at", DateTime(timezone=True), nullable=True)
    leaseUntil: Mapped[datetime | None] = mapped_column("lease_until", DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("notification_outbox_status_created_idx", "status", "createdAt"),
        Index("notification_outbox_dead_letter_idx", "status", "deadLetteredAt"),
        Index("notification_outbox_pending_due_idx", "status", "next_attempt_at", "lease_until"),
    )


def compute_webhook_signature(secret: str, timestamp_str: str, body_bytes: bytes) -> str:
    """
    Compute HMAC-SHA256 webhook signature over `<timestamp>.<raw_json_body>`.
    Returns `v1=<hex_digest>`.
    """
    key = (secret or "").encode("utf-8")
    msg = f"{timestamp_str}.".encode("utf-8") + (body_bytes or b"")
    digest = hmac.new(key, msg, hashlib.sha256).hexdigest()
    return f"v1={digest}"


def verify_webhook_signature(
    secret: str,
    timestamp_str: str,
    body_bytes: bytes,
    signature_header: str,
    *,
    tolerance_seconds: int = 300,
    now_ts: Optional[int] = None,
) -> bool:
    """Constant-time verification of `X-DPU-Signature-256` and replay timestamp window."""
    if not secret or not timestamp_str or not signature_header:
        return False
    try:
        ts_val = int(timestamp_str)
    except ValueError:
        return False
    ref_now = int(now_ts if now_ts is not None else time.time())
    if tolerance_seconds > 0 and abs(ref_now - ts_val) > tolerance_seconds:
        return False
    expected = compute_webhook_signature(secret, timestamp_str, body_bytes)
    return hmac.compare_digest(expected, signature_header.strip())


def _prepare_payload(
    event: str,
    payload: dict[str, Any] | None,
    *,
    company_id: Optional[str] = None,
) -> dict[str, Any]:
    """Merge metadata, render template body when missing, and Fernet-seal secrets."""
    raw = {**(payload or {}), "event": event, "companyId": str(company_id) if company_id else None}
    if not raw.get("body"):
        locale = str(raw.get("locale") or "th")
        channel_hint = str(raw.get("templateChannel") or "line")
        tmpl = builtin_template(event, locale=locale, channel=channel_hint)
        if tmpl:
            data = raw.get("data") if isinstance(raw.get("data"), dict) else raw
            raw["subject"] = raw.get("subject") or tmpl.get("subject")
            raw["body"] = render_template(tmpl["bodyTemplate"], data)  # type: ignore[arg-type]
            raw["i18nKey"] = f"notify.{event}"
    return seal_payload_secrets(raw)


async def enqueue(
    event: str,
    channel: str,
    payload: dict[str, Any],
    *,
    company_id: Optional[str] = None,
) -> None:
    sealed = _prepare_payload(event, payload, company_id=company_id)
    async with async_session() as db:
        db.add(
            NotificationOutbox(
                companyId=UUID(str(company_id)) if company_id else None,
                event=event,
                channel=channel,
                payload=sealed,
                status="pending",
                attempts=0,
            )
        )
        await db.commit()


async def emit_company_webhook_event(
    company_id: UUID | str,
    event: str,
    data: dict[str, Any],
) -> bool:
    """
    If the company has configured a webhookUrl in `notify:{companyId}` and subscribed to `event`
    (or `*`), enqueue a signed outbound webhook event for Payroll / ERP integration.
    """
    cid_str = str(company_id)
    async with async_session() as db:
        row = await db.get(SystemSetting, f"notify:{cid_str}")
        cfg = row.value if (row and isinstance(row.value, dict)) else {}
        webhook_url = str(cfg.get("webhookUrl") or "").strip()
        if not webhook_url:
            return False
        subscribed = cfg.get("events")
        if isinstance(subscribed, list) and subscribed:
            if event not in subscribed and "*" not in subscribed:
                return False
        webhook_secret = str(cfg.get("webhookSecret") or settings.WEBHOOK_SIGNING_SECRET or "").strip()
        sealed = _prepare_payload(
            event,
            {
                "webhookUrl": webhook_url,
                "webhookSecret": webhook_secret,
                "subject": f"DPU Attendance Event: {event}",
                "body": f"Event {event} triggered for company {cid_str}",
                "data": data,
            },
            company_id=cid_str,
        )
        db.add(
            NotificationOutbox(
                companyId=UUID(cid_str),
                event=event,
                channel="webhook",
                payload=sealed,
                status="pending",
                attempts=0,
            )
        )
        await db.commit()
        return True


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
    """Deliver via LINE Messaging API push (replaces retired LINE Notify).

    Expects ``lineUserId`` (LINE user mid) and a channel access token
    (``lineToken`` / ``lineChannelAccessToken`` / ``LINE_CHANNEL_ACCESS_TOKEN``).
    """
    token = (
        payload.get("lineChannelAccessToken")
        or payload.get("lineToken")
        or settings.LINE_CHANNEL_ACCESS_TOKEN
    )
    if not token:
        logger.info("notify line skipped (no channel access token)")
        return
    to_user = str(payload.get("lineUserId") or payload.get("to") or "").strip()
    if not to_user:
        # Company-level token without a user id: skip rather than hit Notify API.
        logger.info("notify line skipped (no lineUserId for Messaging API push)")
        return
    base = (settings.LINE_MESSAGING_API_BASE or "https://api.line.me/v2/bot").rstrip("/")
    body = json_bytes(
        {
            "to": to_user,
            "messages": [
                {
                    "type": "text",
                    "text": (payload.get("body") or payload.get("subject") or "DPU Attendance")[:5000],
                }
            ],
        }
    )
    req = urllib.request.Request(
        f"{base}/message/push",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        if resp.status >= 300:
            raise RuntimeError(f"LINE Messaging API HTTP {resp.status}")


def _send_webhook(payload: dict, *, delivery_id: str = "") -> None:
    url = (payload.get("webhookUrl") or "").strip()
    if not url:
        logger.info("notify webhook skipped (no webhookUrl)")
        return
    from ..security.ssrf import urlopen_no_redirect, validate_outbound_url

    url = validate_outbound_url(url, allow_private_lan=False)
    event_name = str(payload.get("event") or "notification")
    ts_str = str(int(time.time()))
    body = json_bytes(
        {
            "event": event_name,
            "subject": payload.get("subject") or "DPU Attendance",
            "text": payload.get("body") or payload.get("subject") or "",
            "companyId": payload.get("companyId"),
            "timestamp": int(ts_str),
            "data": payload.get("data") or {},
        }
    )
    headers = {
        "Content-Type": "application/json",
        "X-DPU-Event": event_name,
        "X-DPU-Timestamp": ts_str,
    }
    if delivery_id:
        headers["X-DPU-Delivery-Id"] = delivery_id

    secret = str(payload.get("webhookSecret") or settings.WEBHOOK_SIGNING_SECRET or "").strip()
    if secret:
        headers["X-DPU-Signature-256"] = compute_webhook_signature(secret, ts_str, body)

    req = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method="POST",
    )
    with urlopen_no_redirect(req, timeout=20) as resp:
        if resp.status >= 300:
            raise RuntimeError(f"Webhook HTTP {resp.status}")


def _send_telegram(payload: dict) -> None:
    """Deliver via Telegram Bot API ``sendMessage``.

    Expects ``telegramBotToken`` and ``telegramChatId`` (group/channel/user id).
    """
    token = str(payload.get("telegramBotToken") or "").strip()
    chat_id = str(payload.get("telegramChatId") or payload.get("to") or "").strip()
    if not token:
        logger.info("notify telegram skipped (no bot token)")
        return
    if not chat_id:
        logger.info("notify telegram skipped (no chat id)")
        return
    text = (payload.get("body") or payload.get("subject") or "DPU Attendance")[:4096]
    api_base = (getattr(settings, "TELEGRAM_API_BASE", None) or "https://api.telegram.org").rstrip("/")
    url = f"{api_base}/bot{token}/sendMessage"
    body = json_bytes(
        {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }
    )
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        if resp.status >= 300:
            raise RuntimeError(f"Telegram Bot API HTTP {resp.status}")


def _send_discord(payload: dict) -> None:
    """Deliver via Discord Incoming Webhook (URL is the secret)."""
    url = str(payload.get("discordWebhookUrl") or "").strip()
    if not url:
        logger.info("notify discord skipped (no webhook url)")
        return
    from ..security.ssrf import urlopen_no_redirect, validate_outbound_url

    url = validate_outbound_url(url, allow_private_lan=False)
    content = (payload.get("body") or payload.get("subject") or "DPU Attendance")[:2000]
    body = json_bytes({"content": content})
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen_no_redirect(req, timeout=20) as resp:
        # Discord returns 204 No Content on success.
        if resp.status >= 300:
            raise RuntimeError(f"Discord webhook HTTP {resp.status}")


def json_bytes(obj) -> bytes:
    return json.dumps(obj, default=str, separators=(",", ":")).encode("utf-8")


_cutoff_sent: set[str] = set()


def _bangkok_tz():
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo("Asia/Bangkok")
    except Exception:
        return timezone(timedelta(hours=7))


async def attendance_cutoff_tick() -> int:
    """Enqueue one late/missing notice per company per day after notify:{id}.cutoff (HH:MM)."""
    from .redis_client import get_redis

    redis = get_redis()
    lock_key = "sv:lock:attendance_cutoff"
    lock_token = str(uuid4())
    lock_acquired = False
    if redis is not None:
        try:
            lock_acquired = bool(await redis.set(lock_key, lock_token, nx=True, ex=55))
            if not lock_acquired:
                return 0
        except Exception:
            lock_acquired = False

    now = datetime.now(_bangkok_tz())
    day = now.date().isoformat()
    queued = 0
    try:
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
                marker_key = f"cutoff_sent:{company_id}"
                existing_marker = await db.get(SystemSetting, marker_key)
                if existing_marker and isinstance(existing_marker.value, dict):
                    if existing_marker.value.get("day") == day:
                        _cutoff_sent.add(marker)
                        continue

                # Skip missing check-in alerts on company holidays
                is_holiday = (
                    await db.execute(
                        text(
                            """
                            SELECT 1 FROM company_holiday
                            WHERE "companyId" = :cid
                              AND holiday_date = :bkk_day
                              AND deleted_at IS NULL
                            LIMIT 1
                            """
                        ),
                        {"cid": company_id, "bkk_day": now.date()},
                    )
                ).first()
                if is_holiday:
                    if existing_marker:
                        existing_marker.value = {"day": day}
                    else:
                        db.add(SystemSetting(key=marker_key, value={"day": day}))
                    await db.commit()
                    _cutoff_sent.add(marker)
                    continue

                # Exclude employees on APPROVED leave today
                missing = (
                    await db.execute(
                        text(
                            """
                            SELECT count(*) FROM company_employee ce
                            WHERE ce."companyId" = :cid AND ce.deleted_at IS NULL
                              AND NOT EXISTS (
                                SELECT 1 FROM employee_timestamp t
                                WHERE t."company_employeeId" = ce."company_employeeId"
                                  AND (t."timestamp" AT TIME ZONE 'Asia/Bangkok')::date = :bkk_day
                              )
                              AND NOT EXISTS (
                                SELECT 1 FROM leave_request lr
                                WHERE lr."company_employeeId" = ce."company_employeeId"
                                  AND lr.status IN ('APPROVED', '1')
                                  AND lr.start_date <= :bkk_day
                                  AND lr.end_date >= :bkk_day
                              )
                            """
                        ),
                        {"cid": company_id, "bkk_day": now.date()},
                    )
                ).scalar_one()
                if existing_marker:
                    existing_marker.value = {"day": day}
                else:
                    db.add(SystemSetting(key=marker_key, value={"day": day}))
                await db.commit()
                _cutoff_sent.add(marker)
                if int(missing or 0) <= 0:
                    continue
                from .outbox_crypto import decrypt_secret

                line_tok = ""
                try:
                    line_tok = decrypt_secret(
                        str(value.get("lineChannelAccessToken") or value.get("lineToken") or "")
                    )
                except RuntimeError:
                    line_tok = ""
                webhook_secret = ""
                try:
                    webhook_secret = decrypt_secret(str(value.get("webhookSecret") or ""))
                except RuntimeError:
                    webhook_secret = str(value.get("webhookSecret") or "")
                channel = (
                    "webhook"
                    if value.get("webhookUrl")
                    else ("line" if line_tok else "email")
                )
                await enqueue(
                    "attendance.missing",
                    channel,
                    {
                        "to": value.get("email") or "",
                        "lineToken": line_tok,
                        "lineChannelAccessToken": line_tok,
                        "webhookUrl": value.get("webhookUrl") or "",
                        "webhookSecret": webhook_secret,
                        "subject": "DPU missing check-in",
                        "data": {"missingCount": int(missing), "date": day},
                    },
                    company_id=company_id,
                )
                queued += 1
        return queued
    finally:
        if redis is not None and lock_acquired:
            try:
                if await redis.get(lock_key) == lock_token:
                    await redis.delete(lock_key)
            except Exception:
                pass


def _outbox_wait_seconds(attempts: int) -> int:
    return min(300, (2 ** max(0, attempts - 1)) * 15)


def _backoff_ready(row: NotificationOutbox, now_utc: datetime) -> bool:
    """Exponential backoff gate: 0s on attempt 0, then 15s, 30s, 60s, 120s (max 300s)."""
    attempts = int(row.attempts or 0)
    if attempts <= 0:
        return True
    next_at = getattr(row, "nextAttemptAt", None)
    if next_at is not None:
        if next_at.tzinfo is None:
            next_at = next_at.replace(tzinfo=timezone.utc)
        return now_utc >= next_at
    if not row.createdAt:
        return True
    created = row.createdAt
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    wait_seconds = _outbox_wait_seconds(attempts)
    return (now_utc - created).total_seconds() >= wait_seconds


OUTBOX_MAX_ATTEMPTS = 5
OUTBOX_LEASE_SECONDS = 120


async def refresh_outbox_backlog() -> tuple[int, Optional[datetime]]:
    """Publish pending count + oldest pending age (dispatcher lag) to Prometheus."""
    async with async_session() as db:
        pending, oldest = (
            await db.execute(
                select(func.count(), func.min(NotificationOutbox.createdAt)).where(
                    NotificationOutbox.status == "pending"
                )
            )
        ).one()
    set_outbox_backlog(int(pending or 0), oldest)
    return int(pending or 0), oldest


async def _deliver_in_app(db, row: NotificationOutbox, payload: dict) -> None:
    from ..models.notification_platform import InAppNotification

    member_raw = payload.get("memberId")
    if not member_raw:
        raise RuntimeError("in_app channel requires memberId")
    company_raw = row.companyId or payload.get("companyId")
    if not company_raw:
        raise RuntimeError("in_app channel requires companyId")
    db.add(
        InAppNotification(
            companyId=UUID(str(company_raw)),
            memberId=UUID(str(member_raw)),
            event=row.event,
            title=str(payload.get("subject") or row.event)[:255],
            body=str(payload.get("body") or ""),
        )
    )


async def retry_dead_letter(outbox_id: UUID) -> bool:
    """Re-queue a failed outbox row (dead-letter UI)."""
    async with async_session() as db:
        row = await db.get(NotificationOutbox, outbox_id)
        if not row or row.status != "failed":
            return False
        row.status = "pending"
        row.attempts = 0
        row.lastError = None
        row.deadLetteredAt = None
        row.nextAttemptAt = None
        row.leaseUntil = None
        await db.commit()
        return True


def _deliver_external_channel(channel: str, delivery_payload: dict, delivery_id: str) -> None:
    if channel == "email":
        _send_email(delivery_payload)
    elif channel == "line":
        _send_line(delivery_payload)
    elif channel == "telegram":
        _send_telegram(delivery_payload)
    elif channel == "discord":
        _send_discord(delivery_payload)
    elif channel in ("webhook", "siem"):
        # F4: SIEM export reuses HMAC-signed webhook delivery.
        _send_webhook(delivery_payload, delivery_id=delivery_id)
    else:
        raise RuntimeError(f"unknown channel {channel}")


async def drain_outbox(limit: int = 20, concurrency: int = 5) -> int:
    """Lock-free 3-phase outbox drain (claim+lease -> concurrent I/O -> persist result).

    Releases DB locks before external HTTP/SMTP calls so long-running webhooks never
    hold database connections or row locks across workers.
    """
    now_utc = datetime.now(timezone.utc)
    lease_deadline = now_utc + timedelta(seconds=OUTBOX_LEASE_SECONDS)
    claimed: list[dict[str, Any]] = []

    # Phase 1: Claim due rows with short FOR UPDATE SKIP LOCKED transaction.
    async with async_session() as db:
        due_filter = or_(
            and_(
                NotificationOutbox.status == "pending",
                or_(NotificationOutbox.leaseUntil.is_(None), NotificationOutbox.leaseUntil <= now_utc),
            ),
            and_(
                NotificationOutbox.status == "processing",
                NotificationOutbox.leaseUntil.isnot(None),
                NotificationOutbox.leaseUntil <= now_utc,
            ),
        )
        rows = (
            await db.execute(
                select(NotificationOutbox)
                .where(due_filter)
                .order_by(NotificationOutbox.createdAt)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        ).scalars().all()
        outbox_claims_total.inc(len(rows))
        for row in rows:
            if not _backoff_ready(row, now_utc):
                outbox_deliveries_total.labels(channel=row.channel, result="skipped").inc()
                continue
            row.status = "processing"
            row.leaseUntil = lease_deadline
            claimed.append(
                {
                    "id": row.id,
                    "channel": row.channel,
                    "payload": dict(row.payload or {}),
                }
            )
        if claimed:
            await db.commit()

    if not claimed:
        return 0

    # Phase 2: Deliver external channels concurrently without holding any DB session/lock.
    sem = asyncio.Semaphore(max(1, int(concurrency or 1)))
    outcomes: dict[UUID, tuple[bool, Optional[str], float]] = {}

    async def _deliver_one(item: dict[str, Any]) -> None:
        item_id: UUID = item["id"]
        channel: str = item["channel"]
        if channel == "in_app":
            return
        t0 = time.perf_counter()
        async with sem:
            try:
                delivery_payload = unseal_payload_secrets(item["payload"])
                await asyncio.to_thread(
                    _deliver_external_channel, channel, delivery_payload, str(item_id)
                )
                outcomes[item_id] = (True, None, time.perf_counter() - t0)
            except Exception as exc:
                outcomes[item_id] = (False, str(exc)[:500], time.perf_counter() - t0)

    await asyncio.gather(*(_deliver_one(item) for item in claimed))

    # Phase 3: Persist status, nextAttemptAt backoff, and handle DB-backed in_app deliveries.
    sent = 0
    finish_utc = datetime.now(timezone.utc)
    claimed_ids = [item["id"] for item in claimed]
    async with async_session() as db:
        locked_rows = (
            await db.execute(
                select(NotificationOutbox).where(NotificationOutbox.id.in_(claimed_ids))
            )
        ).scalars().all()
        row_map = {r.id: r for r in locked_rows}
        for item in claimed:
            db_row = row_map.get(item["id"])
            if db_row is None:
                continue
            if db_row.channel == "in_app":
                t0 = time.perf_counter()
                try:
                    delivery_payload = unseal_payload_secrets(db_row.payload or {})
                    await _deliver_in_app(db, db_row, delivery_payload)
                    ok, err_msg, dur = True, None, time.perf_counter() - t0
                except Exception as exc:
                    ok, err_msg, dur = False, str(exc)[:500], time.perf_counter() - t0
            else:
                ok, err_msg, dur = outcomes.get(db_row.id, (False, "missing outcome", 0.0))

            db_row.attempts = int(db_row.attempts or 0) + 1
            db_row.leaseUntil = None
            outbox_delivery_duration_seconds.labels(channel=db_row.channel).observe(dur)

            if ok:
                db_row.status = "sent"
                db_row.lastError = None
                db_row.deadLetteredAt = None
                db_row.nextAttemptAt = None
                sent += 1
                outbox_deliveries_total.labels(channel=db_row.channel, result="sent").inc()
            else:
                db_row.lastError = err_msg or "delivery failed"
                if db_row.attempts >= OUTBOX_MAX_ATTEMPTS:
                    db_row.status = "failed"
                    db_row.deadLetteredAt = finish_utc
                    db_row.nextAttemptAt = None
                    outbox_deliveries_total.labels(channel=db_row.channel, result="failed").inc()
                else:
                    db_row.status = "pending"
                    db_row.nextAttemptAt = finish_utc + timedelta(
                        seconds=_outbox_wait_seconds(db_row.attempts)
                    )
                    outbox_deliveries_total.labels(channel=db_row.channel, result="retry").inc()
                logger.warning("notify %s failed: %s", db_row.id, db_row.lastError)
        await db.commit()
    return sent
