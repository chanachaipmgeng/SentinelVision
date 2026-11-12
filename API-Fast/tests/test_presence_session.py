"""Phase 1: presence session fold (extend / gap close / camera switch)."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("SECRET_KEY", "unit-test-secret-key-32chars-min!!")
os.environ.setdefault("AUTH_FAIL_FAST", "false")

import pytest

from src.services import presence_service as presence  # noqa: E402


def _cam(camera_id=None, company_id=None, role="LOCATE", event_id=None):
    cam = MagicMock()
    cam.cameraId = camera_id or uuid.uuid4()
    cam.companyId = company_id or uuid.uuid4()
    cam.zoneId = None
    cam.siteFloorId = None
    cam.aiConfig = {"presenceRole": role}
    if event_id:
        cam.aiConfig["eventId"] = str(event_id)
    return cam


class _Result:
    def __init__(self, value=None, values=None):
        self._value = value
        self._values = values or []

    def scalar_one_or_none(self):
        return self._value

    def scalars(self):
        return self

    def all(self):
        return list(self._values)


@pytest.mark.asyncio
async def test_record_sighting_extends_open_session_within_gap(monkeypatch):
    monkeypatch.setattr(presence.settings, "PRESENCE_SESSION_GAP_SECONDS", 90)
    company_id = uuid.uuid4()
    member_id = uuid.uuid4()
    cam = _cam(company_id=company_id)
    now = datetime.now(timezone.utc)
    open_sess = MagicMock()
    open_sess.cameraId = cam.cameraId
    open_sess.lastSeenAt = now - timedelta(seconds=30)
    open_sess.sampleCount = 2
    open_sess.open = True
    open_sess.zoneId = None
    open_sess.siteFloorId = None
    open_sess.eventId = None
    open_sess.presenceRole = "LOCATE"
    open_sess.sessionId = uuid.uuid4()

    calls = {"n": 0}

    async def fake_execute(stmt):
        calls["n"] += 1
        # 1) other-open cameras  2) open-same-camera
        if calls["n"] == 1:
            return _Result(values=[])
        return _Result(value=open_sess)

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=fake_execute)
    db.add = MagicMock()
    db.flush = AsyncMock()

    out = await presence.record_sighting(
        db,
        company_id=company_id,
        member_id=member_id,
        camera=cam,
        seen_at=now,
        distance=0.2,
    )
    assert out["sessionCreated"] is False
    assert open_sess.sampleCount == 3
    assert open_sess.lastSeenAt == now
    assert out["sessionId"] == str(open_sess.sessionId)


@pytest.mark.asyncio
async def test_record_sighting_closes_when_gap_exceeded(monkeypatch):
    monkeypatch.setattr(presence.settings, "PRESENCE_SESSION_GAP_SECONDS", 90)
    company_id = uuid.uuid4()
    member_id = uuid.uuid4()
    cam = _cam(company_id=company_id)
    now = datetime.now(timezone.utc)
    stale = MagicMock()
    stale.cameraId = cam.cameraId
    stale.lastSeenAt = now - timedelta(seconds=120)
    stale.sampleCount = 4
    stale.open = True
    stale.endedAt = None
    stale.zoneId = None
    stale.siteFloorId = None
    stale.eventId = None
    stale.presenceRole = "LOCATE"
    stale.sessionId = uuid.uuid4()

    calls = {"n": 0}

    async def fake_execute(stmt):
        calls["n"] += 1
        if calls["n"] == 1:
            return _Result(values=[])
        return _Result(value=stale)

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=fake_execute)
    added = []
    db.add = MagicMock(side_effect=lambda obj: added.append(obj))
    db.flush = AsyncMock()

    out = await presence.record_sighting(
        db,
        company_id=company_id,
        member_id=member_id,
        camera=cam,
        seen_at=now,
        distance=0.15,
    )
    assert stale.open is False
    assert stale.endedAt == stale.lastSeenAt
    assert out["sessionCreated"] is True
    # sighting + new session
    assert len(added) >= 2


@pytest.mark.asyncio
async def test_record_sighting_camera_switch_closes_previous(monkeypatch):
    monkeypatch.setattr(presence.settings, "PRESENCE_SESSION_GAP_SECONDS", 90)
    company_id = uuid.uuid4()
    member_id = uuid.uuid4()
    cam_a = _cam(company_id=company_id)
    cam_b = _cam(company_id=company_id)
    now = datetime.now(timezone.utc)

    other = MagicMock()
    other.cameraId = cam_a.cameraId
    other.open = True
    other.lastSeenAt = now - timedelta(seconds=10)
    other.endedAt = None

    calls = {"n": 0}

    async def fake_execute(stmt):
        calls["n"] += 1
        if calls["n"] == 1:
            return _Result(values=[other])
        return _Result(value=None)

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=fake_execute)
    db.add = MagicMock()
    db.flush = AsyncMock()

    out = await presence.record_sighting(
        db,
        company_id=company_id,
        member_id=member_id,
        camera=cam_b,
        seen_at=now,
        distance=0.1,
    )
    assert other.open is False
    assert other.endedAt == other.lastSeenAt
    assert out["sessionCreated"] is True
    assert out["cameraId"] == str(cam_b.cameraId)


def test_camera_presence_meta_booth_requires_event():
    cam = _cam(role="BOOTH")
    meta = presence.camera_presence_meta(cam)
    assert meta["presenceRole"] == "LOCATE"
    assert meta["eventId"] is None

    eid = uuid.uuid4()
    cam2 = _cam(role="BOOTH", event_id=eid)
    meta2 = presence.camera_presence_meta(cam2)
    assert meta2["presenceRole"] == "BOOTH"
    assert meta2["eventId"] == eid
