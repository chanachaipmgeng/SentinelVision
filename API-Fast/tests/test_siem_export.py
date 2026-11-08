"""F4: SIEM outbox enqueue on incident create + settings helpers."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.sentinel import SentinelIncidentLog
from src.services.notification_service import NotificationOutbox
from src.services import siem_export_service as siem


COMPANY_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


@pytest.mark.asyncio
async def test_queue_siem_skips_when_no_settings():
    db = AsyncMock()
    db.get = AsyncMock(return_value=None)
    db.add = MagicMock()
    inc = SentinelIncidentLog(
        companyId=COMPANY_ID,
        eventType="BLACKLIST_ALERT",
        severity="CRITICAL",
        subjectName="Target",
        identityType="BLACKLIST",
    )
    ok = await siem.queue_siem_incident_export(db, COMPANY_ID, inc)
    assert ok is False
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_queue_siem_enqueues_outbox_with_hmac_payload_fields(monkeypatch):
    monkeypatch.setattr(siem, "encrypt_secret", lambda v: f"sealed:{v}" if v else "")
    monkeypatch.setattr(siem, "decrypt_secret", lambda v: v.replace("sealed:", "") if v else "")

    settings_row = MagicMock()
    settings_row.value = {
        "siemWebhookUrl": "https://siem.example/hooks/dpu",
        "siemWebhookSecret": "sealed:super-secret",
    }
    db = AsyncMock()
    db.get = AsyncMock(return_value=settings_row)
    db.add = MagicMock()

    inc = SentinelIncidentLog(
        companyId=COMPANY_ID,
        eventType="ACCESS_DENIED",
        severity="WARNING",
        subjectName="Unknown Person",
        identityType="UNKNOWN",
        zoneName="Gate A",
    )
    ok = await siem.queue_siem_incident_export(db, COMPANY_ID, inc)
    assert ok is True

    added = [c.args[0] for c in db.add.call_args_list]
    assert len(added) == 1
    row = added[0]
    assert isinstance(row, NotificationOutbox)
    assert row.channel == "siem"
    assert row.event == "sentinel.incident.created"
    assert row.companyId == COMPANY_ID
    assert row.payload["webhookUrl"] == "https://siem.example/hooks/dpu"
    assert row.payload["webhookSecret"] == "sealed:super-secret"
    assert row.payload["data"]["eventType"] == "ACCESS_DENIED"
    assert row.payload["data"]["subjectName"] == "Unknown Person"
    assert row.payload["data"]["zoneName"] == "Gate A"


@pytest.mark.asyncio
async def test_evaluate_kiosk_also_queues_siem_when_configured(monkeypatch):
    """Incident create path in evaluate_kiosk_sentinel_match should SIEM-enqueue."""
    from src.models.sentinel import SentinelIdentity
    from src.services import sentinel_incident_service as incident_svc

    company_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    identity_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    ident = SentinelIdentity(
        identityId=identity_id,
        companyId=company_id,
        identityType="VIP",
        fullName="VIP Guest",
        severity="INFO",
        allowedZoneIds=[],
        status="ACTIVE",
    )
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    # No open dedupe match
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute.return_value = result

    queued = AsyncMock(return_value=True)
    monkeypatch.setattr(incident_svc, "queue_siem_incident_export", queued)

    with patch.object(
        incident_svc,
        "search_sentinel_identity_pgvector",
        AsyncMock(return_value=(ident, 0.05)),
    ):
        meta = await incident_svc.evaluate_kiosk_sentinel_match(
            db, company_id, [0.01] * 512, 0.4
        )

    assert meta["accessGranted"] is True
    queued.assert_awaited_once()
    assert queued.await_args.args[1] == company_id
    assert isinstance(queued.await_args.args[2], SentinelIncidentLog)


@pytest.mark.asyncio
async def test_enqueue_siem_test_requires_url(monkeypatch):
    settings_row = MagicMock()
    settings_row.value = {"siemWebhookUrl": "", "siemWebhookSecret": ""}

    class _Sess:
        async def __aenter__(self):
            db = AsyncMock()
            db.get = AsyncMock(return_value=settings_row)
            return db

        async def __aexit__(self, *a):
            return False

    monkeypatch.setattr(
        "src.config.database.async_session",
        lambda: _Sess(),
    )
    result = await siem.enqueue_siem_test(COMPANY_ID)
    assert result["queued"] is False
    assert "siemWebhookUrl" in result["reason"]


def test_public_siem_settings_redacts_secret():
    out = siem.public_siem_settings(
        {"siemWebhookUrl": "https://x", "siemWebhookSecret": "fernet:abc"}
    )
    assert out["siemWebhookUrl"] == "https://x"
    assert out["siemWebhookSecret"] == ""
    assert out["hasSiemWebhookSecret"] is True
