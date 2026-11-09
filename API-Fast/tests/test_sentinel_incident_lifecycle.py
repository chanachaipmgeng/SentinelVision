"""F1: sentinel incident dedupe window + acknowledge / assign / close transitions."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.models.sentinel import SentinelIncidentLog  # noqa: E402
from src.services import sentinel_incident_service as svc  # noqa: E402
from src.services.notification_service import NotificationOutbox  # noqa: E402


COMPANY_ID = uuid4()
IDENTITY_ID = uuid4()
ZONE_ID = uuid4()
ACTOR_ID = uuid4()
ASSIGNEE_ID = uuid4()


def _make_incident(**overrides) -> SentinelIncidentLog:
    now = datetime.now(timezone.utc)
    base = dict(
        incidentId=uuid4(),
        companyId=COMPANY_ID,
        eventType="BLACKLIST_ALERT",
        severity="CRITICAL",
        status=svc.STATUS_OPEN,
        identityId=IDENTITY_ID,
        zoneId=ZONE_ID,
        subjectName="Target",
        identityType="BLACKLIST",
        confidencePercent=90.0,
        distance=0.1,
        dedupeKey=svc.build_dedupe_key(COMPANY_ID, IDENTITY_ID, "BLACKLIST_ALERT", ZONE_ID),
        occurredAt=now,
    )
    base.update(overrides)
    return SentinelIncidentLog(**base)


@pytest.mark.asyncio
async def test_record_incident_dedupes_within_window_and_skips_outbox():
    existing = _make_incident(confidencePercent=80.0)
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=existing))
    )
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    outbox_calls = []

    def factory():
        outbox_calls.append(1)
        return NotificationOutbox(
            companyId=COMPANY_ID,
            event="sentinel.blacklist_detected",
            channel="webhook",
            payload={"x": 1},
        )

    inc, created = await svc.record_incident(
        db,
        company_id=COMPANY_ID,
        event_type="BLACKLIST_ALERT",
        severity="CRITICAL",
        identity_id=IDENTITY_ID,
        zone_id=ZONE_ID,
        subject_name="Target",
        identity_type="BLACKLIST",
        confidence_percent=95.5,
        distance=0.05,
        outbox_factory=factory,
    )

    assert created is False
    assert inc is existing
    assert existing.confidencePercent == 95.5
    assert existing.distance == 0.05
    assert outbox_calls == []
    db.add.assert_not_called()
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_record_incident_creates_new_and_enqueues_outbox_when_no_open_match(monkeypatch):
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    monkeypatch.setattr(svc, "queue_siem_incident_export", AsyncMock(return_value=False))

    def factory():
        return NotificationOutbox(
            companyId=COMPANY_ID,
            event="sentinel.blacklist_detected",
            channel="webhook",
            payload={"x": 1},
        )

    inc, created = await svc.record_incident(
        db,
        company_id=COMPANY_ID,
        event_type="BLACKLIST_ALERT",
        severity="CRITICAL",
        identity_id=IDENTITY_ID,
        zone_id=ZONE_ID,
        subject_name="Target",
        identity_type="BLACKLIST",
        confidence_percent=91.0,
        outbox_factory=factory,
    )

    assert created is True
    assert inc.status == svc.STATUS_OPEN
    assert inc.dedupeKey == svc.build_dedupe_key(
        COMPANY_ID, IDENTITY_ID, "BLACKLIST_ALERT", ZONE_ID
    )
    added = [c.args[0] for c in db.add.call_args_list]
    assert any(isinstance(o, SentinelIncidentLog) for o in added)
    assert any(isinstance(o, NotificationOutbox) for o in added)


@pytest.mark.asyncio
async def test_lifecycle_acknowledge_assign_close(monkeypatch):
    inc = _make_incident()
    db = AsyncMock()
    db.get = AsyncMock(return_value=inc)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    # Close path enqueues SIEM; stub so this test stays lifecycle-focused.
    monkeypatch.setattr(svc, "queue_siem_incident_export", AsyncMock(return_value=False))

    out = await svc.acknowledge_incident(db, COMPANY_ID, inc.incidentId, ACTOR_ID)
    assert out.status == svc.STATUS_ACKNOWLEDGED
    assert out.acknowledgedBy == ACTOR_ID
    assert out.acknowledgedAt is not None

    out = await svc.assign_incident(
        db, COMPANY_ID, inc.incidentId, actor_id=ACTOR_ID, assignee_id=ASSIGNEE_ID
    )
    assert out.status == svc.STATUS_ASSIGNED
    assert out.assignedTo == ASSIGNEE_ID
    assert out.assignedAt is not None

    out = await svc.close_incident(db, COMPANY_ID, inc.incidentId, ACTOR_ID)
    assert out.status == svc.STATUS_CLOSED
    assert out.closedBy == ACTOR_ID
    assert out.closedAt is not None

    with pytest.raises(HTTPException) as exc:
        await svc.acknowledge_incident(db, COMPANY_ID, inc.incidentId, ACTOR_ID)
    assert exc.value.status_code == 409

    with pytest.raises(HTTPException) as exc2:
        await svc.assign_incident(db, COMPANY_ID, inc.incidentId, actor_id=ACTOR_ID)
    assert exc2.value.status_code == 409


@pytest.mark.asyncio
async def test_closed_incident_not_deduped(monkeypatch):
    """A CLOSED row outside open statuses must not satisfy find_open_dedupe_match."""
    closed = _make_incident(status=svc.STATUS_CLOSED)
    # Simulate DB returning None because the query filters status IN open set.
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    monkeypatch.setattr(svc, "queue_siem_incident_export", AsyncMock(return_value=False))

    key = closed.dedupeKey
    found = await svc.find_open_dedupe_match(db, company_id=COMPANY_ID, dedupe_key=key)
    assert found is None

    inc, created = await svc.record_incident(
        db,
        company_id=COMPANY_ID,
        event_type="BLACKLIST_ALERT",
        identity_id=IDENTITY_ID,
        zone_id=ZONE_ID,
        subject_name="Target",
        identity_type="BLACKLIST",
    )
    assert created is True
    assert inc.status == svc.STATUS_OPEN


def test_build_dedupe_key_uses_member_when_no_identity():
    mid = uuid4()
    key = svc.build_dedupe_key(COMPANY_ID, None, "ACCESS_GRANTED", ZONE_ID, member_id=mid)
    assert str(mid) in key
    assert "ACCESS_GRANTED" in key


@pytest.mark.asyncio
async def test_record_incident_sets_sla_due_for_high_severity(monkeypatch):
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    monkeypatch.setattr(svc, "queue_siem_incident_export", AsyncMock(return_value=False))
    monkeypatch.setattr(
        svc,
        "get_incident_sla_settings",
        AsyncMock(return_value={"incidentSlaMinutesHigh": 15}),
    )

    inc, created = await svc.record_incident(
        db,
        company_id=COMPANY_ID,
        event_type="BLACKLIST_ALERT",
        severity="CRITICAL",
        identity_id=IDENTITY_ID,
        zone_id=ZONE_ID,
        subject_name="Target",
        identity_type="BLACKLIST",
    )
    assert created is True
    assert inc.slaDueAt is not None
    delta = (inc.slaDueAt - inc.occurredAt).total_seconds()
    assert 14 * 60 <= delta <= 16 * 60


@pytest.mark.asyncio
async def test_record_incident_skips_sla_for_info(monkeypatch):
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    monkeypatch.setattr(svc, "queue_siem_incident_export", AsyncMock(return_value=False))

    inc, created = await svc.record_incident(
        db,
        company_id=COMPANY_ID,
        event_type="ACCESS_GRANTED",
        severity="INFO",
        member_id=ACTOR_ID,
        zone_id=ZONE_ID,
        subject_name="Emp",
        identity_type="EMPLOYEE",
    )
    assert created is True
    assert inc.slaDueAt is None


@pytest.mark.asyncio
async def test_bulk_acknowledge_and_close(monkeypatch):
    open_a = _make_incident()
    open_b = _make_incident()
    closed = _make_incident(status=svc.STATUS_CLOSED)
    by_id = {
        open_a.incidentId: open_a,
        open_b.incidentId: open_b,
        closed.incidentId: closed,
    }

    db = AsyncMock()

    async def _get(_model, iid):
        return by_id.get(iid)

    db.get = AsyncMock(side_effect=_get)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    monkeypatch.setattr(svc, "queue_siem_incident_export", AsyncMock(return_value=False))

    ack = await svc.acknowledge_incidents_bulk(
        db,
        COMPANY_ID,
        [str(open_a.incidentId), str(closed.incidentId), "not-a-uuid"],
        ACTOR_ID,
    )
    assert ack["acknowledgedCount"] == 1
    assert ack["skippedCount"] == 1
    assert open_a.status == svc.STATUS_ACKNOWLEDGED

    closed_res = await svc.close_incidents_bulk(
        db,
        COMPANY_ID,
        [str(open_a.incidentId), str(open_b.incidentId)],
        ACTOR_ID,
    )
    assert closed_res["closedCount"] == 2
    assert open_a.status == svc.STATUS_CLOSED
    assert open_b.status == svc.STATUS_CLOSED



@pytest.mark.asyncio
async def test_evaluate_kiosk_uses_dedupe_on_repeat_hit():
    ident = MagicMock()
    ident.identityId = IDENTITY_ID
    ident.identityType = "BLACKLIST"
    ident.fullName = "Target"
    ident.severity = "CRITICAL"
    ident.alertNote = "stop"
    ident.seatNumber = None
    ident.pictureUrl = "/images/x.jpg"
    ident.eventId = None

    existing = _make_incident()
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    with (
        patch.object(
            svc,
            "search_sentinel_identity_pgvector",
            AsyncMock(return_value=(ident, 0.12)),
        ),
        patch.object(
            svc,
            "find_open_dedupe_match",
            AsyncMock(return_value=existing),
        ),
    ):
        meta = await svc.evaluate_kiosk_sentinel_match(db, COMPANY_ID, [0.01] * 512, 0.4)

    assert meta["accessGranted"] is False
    # Dedupe path: no new NotificationOutbox / incident insert.
    assert db.add.call_count == 0
    assert existing.confidencePercent == round(max(0.0, min(1.0, 1.0 - 0.12)) * 100.0, 2)
