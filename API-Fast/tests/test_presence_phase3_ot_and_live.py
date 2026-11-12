"""Phase 3 OT evidence + Phase 4 live-by-camera + retention."""
from __future__ import annotations

import os
import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("SECRET_KEY", "unit-test-secret-key-32chars-min!!")
os.environ.setdefault("AUTH_FAIL_FAST", "false")

import pytest

from src.services import presence_service as presence  # noqa: E402


class _Scalars:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)

    def scalars(self):
        return self

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None


@pytest.mark.asyncio
async def test_ot_evidence_three_statuses(monkeypatch):
    company_id = uuid.uuid4()
    m_aligned = uuid.uuid4()
    m_punch_only = uuid.uuid4()
    m_cam_only = uuid.uuid4()
    ot_cam = uuid.uuid4()
    day = date(2026, 11, 12)
    tz = presence.bangkok_tz()
    shift_end = datetime(2026, 11, 12, 18, 0, tzinfo=tz).astimezone(timezone.utc)

    ot_camera = MagicMock()
    ot_camera.cameraId = ot_cam
    ot_camera.companyId = company_id
    ot_camera.deletedAt = None
    ot_camera.aiConfig = {"presenceRole": "OT_AREA"}

    locate_cam = MagicMock()
    locate_cam.cameraId = uuid.uuid4()
    locate_cam.companyId = company_id
    locate_cam.deletedAt = None
    locate_cam.aiConfig = {"presenceRole": "LOCATE"}

    sess_aligned = MagicMock()
    sess_aligned.memberId = m_aligned
    sess_aligned.cameraId = ot_cam
    sess_aligned.presenceRole = "OT_AREA"
    sess_aligned.startedAt = shift_end + timedelta(minutes=10)
    sess_aligned.endedAt = shift_end + timedelta(minutes=70)
    sess_aligned.lastSeenAt = shift_end + timedelta(minutes=70)

    sess_cam_only = MagicMock()
    sess_cam_only.memberId = m_cam_only
    sess_cam_only.cameraId = ot_cam
    sess_cam_only.presenceRole = "OT_AREA"
    sess_cam_only.startedAt = shift_end + timedelta(minutes=5)
    sess_cam_only.endedAt = shift_end + timedelta(minutes=35)
    sess_cam_only.lastSeenAt = shift_end + timedelta(minutes=35)

    # Outside OT_AREA must not count even if after shift end.
    sess_locate = MagicMock()
    sess_locate.memberId = m_punch_only
    sess_locate.cameraId = locate_cam.cameraId
    sess_locate.presenceRole = "LOCATE"
    sess_locate.startedAt = shift_end + timedelta(minutes=5)
    sess_locate.endedAt = shift_end + timedelta(minutes=60)
    sess_locate.lastSeenAt = shift_end + timedelta(minutes=60)

    shift = MagicMock()
    shift.endTime = "18:00"
    shift.deletedAt = None
    shift.isDefault = True
    shift.companyId = company_id

    def make_ts(member_id, ot_minutes):
        emp = MagicMock()
        emp.memberId = member_id
        emp.company_employeeId = uuid.uuid4()
        ts = MagicMock()
        ts.company_employee = emp
        ts.overtimeMinutes = ot_minutes
        ts.timestamp = shift_end + timedelta(hours=1)
        return ts

    members = {
        m_aligned: MagicMock(memberId=m_aligned, firstName="A", lastName="One", username="a"),
        m_punch_only: MagicMock(memberId=m_punch_only, firstName="B", lastName="Two", username="b"),
        m_cam_only: MagicMock(memberId=m_cam_only, firstName="C", lastName="Three", username="c"),
    }

    seq = [
        _Scalars([ot_camera, locate_cam]),  # cameras
        _Scalars([sess_aligned, sess_cam_only]),  # OT sessions only (query filters role)
        _Scalars([shift]),  # shift
        _Scalars([make_ts(m_aligned, 60), make_ts(m_punch_only, 45)]),  # punches
        _Scalars(list(members.values())),  # names
    ]
    idx = {"i": 0}

    async def seq_execute(stmt):
        i = idx["i"]
        idx["i"] += 1
        return seq[i]

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=seq_execute)

    report = await presence.ot_evidence_report(db, company_id, work_date=day)
    by_status = {i["status"]: i for i in report["items"]}
    assert "aligned" in by_status
    assert "punch_without_camera" in by_status
    assert "camera_without_punch" in by_status
    assert by_status["aligned"]["memberId"] == str(m_aligned)
    assert by_status["punch_without_camera"]["memberId"] == str(m_punch_only)
    assert by_status["camera_without_punch"]["memberId"] == str(m_cam_only)
    assert by_status["camera_without_punch"]["cameraOtMinutes"] == 30


@pytest.mark.asyncio
async def test_live_excludes_closed_and_foreign_camera():
    company_id = uuid.uuid4()
    other_company = uuid.uuid4()
    cam_id = uuid.uuid4()

    open_sess = MagicMock()
    open_sess.sessionId = uuid.uuid4()
    open_sess.memberId = uuid.uuid4()
    open_sess.cameraId = cam_id
    open_sess.siteFloorId = None
    open_sess.open = True
    open_sess.lastSeenAt = datetime.now(timezone.utc)
    open_sess.startedAt = datetime.now(timezone.utc) - timedelta(minutes=2)

    cam = MagicMock()
    cam.cameraId = cam_id
    cam.companyId = company_id
    cam.deletedAt = None
    cam.name = "Lobby"
    cam.mapPosX = 0.4
    cam.mapPosY = 0.6
    cam.siteFloorId = None

    foreign = MagicMock()
    foreign.cameraId = uuid.uuid4()
    foreign.companyId = other_company
    foreign.deletedAt = None

    member = MagicMock()
    member.memberId = open_sess.memberId
    member.firstName = "Pat"
    member.lastName = "Lee"
    member.username = "pat"

    with patch(
        "src.services.presence_service.resolve_cctv_camera_interval",
        AsyncMock(return_value=30),
    ):
        # Foreign camera → found False
        db = AsyncMock()
        db.get = AsyncMock(return_value=foreign)
        out = await presence.live_by_camera(db, company_id, camera_id=foreign.cameraId)
        assert out["found"] is False
        assert out["items"] == []

        # Open session on owned camera
        seq = [
            _Scalars([open_sess]),
            _Scalars([member]),
            _Scalars([cam]),
        ]
        idx = {"i": 0}

        async def seq_execute(stmt):
            i = idx["i"]
            idx["i"] += 1
            return seq[i]

        db2 = AsyncMock()
        db2.get = AsyncMock(return_value=cam)
        db2.execute = AsyncMock(side_effect=seq_execute)
        out2 = await presence.live_by_camera(db2, company_id, camera_id=cam_id)
        assert out2["found"] is True
        assert len(out2["items"]) == 1
        assert out2["items"][0]["fullName"] == "Pat Lee"
        assert out2["items"][0]["mapPosX"] == 0.4


@pytest.mark.asyncio
async def test_purge_retention_only_old_rows(monkeypatch):
    monkeypatch.setattr(presence.settings, "PRESENCE_SIGHTING_RETENTION_DAYS", 14)
    monkeypatch.setattr(presence.settings, "PRESENCE_SESSION_RETENTION_DAYS", 90)
    company_id = uuid.uuid4()

    class _DelResult:
        rowcount = 3

    class _DelResult2:
        rowcount = 1

    results = [_DelResult(), _DelResult2()]
    idx = {"i": 0}

    async def seq_execute(stmt):
        i = idx["i"]
        idx["i"] += 1
        return results[i]

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=seq_execute)
    stats = await presence.purge_presence_retention(db, company_id)
    assert stats == {"sightingsRemoved": 3, "sessionsRemoved": 1}
    assert db.execute.await_count == 2
