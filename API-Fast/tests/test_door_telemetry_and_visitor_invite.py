"""Unit tests for Bidirectional Door Telemetry (DFO/DHO) & Guest Visitor Invite tokens."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.controllers import sentinel_controller as ctrl
from src.models.sentinel import SentinelAccessZone
from src.services import visitor_invite_service as vis_svc


@pytest.mark.asyncio
async def test_door_telemetry_dfo_dho_and_close(monkeypatch):
    cid = uuid4()
    zid = uuid4()
    zone = SentinelAccessZone(
        zoneId=zid,
        companyId=cid,
        name="Main Server Room",
        doorHeldMaxSeconds=15,
        doorOpenSince=None,
    )
    db = MagicMock()
    db.get = AsyncMock(return_value=zone)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    rec_mock = AsyncMock(return_value=(MagicMock(), True))
    monkeypatch.setattr(ctrl, "record_incident", rec_mock)
    monkeypatch.setattr(ctrl, "cache_delete", AsyncMock(return_value=True))

    # 1. Forced entry triggers DOOR_FORCED_OPEN
    res_forced = await ctrl.report_door_telemetry(db, cid, zid, {"state": "FORCED"})
    assert res_forced["alarmTriggered"] == "DOOR_FORCED_OPEN"
    assert rec_mock.await_count == 1
    assert rec_mock.call_args.kwargs["event_type"] == "DOOR_FORCED_OPEN"

    # 2. Door held open > 15s triggers DOOR_HELD_OPEN
    zone.doorOpenSince = datetime.now(timezone.utc) - timedelta(seconds=25)
    res_held = await ctrl.report_door_telemetry(db, cid, zid, {"state": "OPEN"})
    assert res_held["alarmTriggered"] == "DOOR_HELD_OPEN"
    assert res_held["heldSeconds"] >= 25.0
    assert rec_mock.call_args.kwargs["event_type"] == "DOOR_HELD_OPEN"

    # 3. Closing door resets doorOpenSince
    res_closed = await ctrl.report_door_telemetry(db, cid, zid, {"state": "CLOSED"})
    assert res_closed["alarmTriggered"] is None
    assert zone.doorOpenSince is None


def test_visitor_invite_token_roundtrip_and_tamper_rejection():
    cid = uuid4()
    out = vis_svc.create_visitor_invite_token(
        company_id=cid,
        visitor_name="Somchai Guest",
        host_name="Khun A",
        purpose="Enterprise Demo",
        valid_hours=8,
    )
    assert out["inviteToken"].startswith("sv_vis_")

    parsed = vis_svc.verify_visitor_invite_token(out["inviteToken"])
    assert parsed["companyId"] == cid
    assert parsed["visitorName"] == "Somchai Guest"
    assert parsed["hostName"] == "Khun A"
    assert parsed["validHours"] == 8

    # Tampered token must fail signature check (401)
    tampered = out["inviteToken"][:-4] + "XXXX"
    with pytest.raises(HTTPException) as exc:
        vis_svc.verify_visitor_invite_token(tampered)
    assert exc.value.status_code == 401
