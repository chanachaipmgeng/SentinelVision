"""Phase 2: multi-face cap and booth dwell report."""
from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("SECRET_KEY", "unit-test-secret-key-32chars-min!!")
os.environ.setdefault("AUTH_FAIL_FAST", "false")

import numpy as np
import pytest

for _mod in ("insightface", "insightface.app", "cv2", "onnxruntime"):
    sys.modules.setdefault(_mod, MagicMock())

from src.services import presence_service as presence  # noqa: E402
from src.utils import face_engine  # noqa: E402


class _Scalars:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)

    def scalars(self):
        return self


def test_multi_face_caps_at_eight(monkeypatch):
    bboxes = []
    for i in range(10):
        size = 20 + i * 5
        bboxes.append([0, 0, size, size, 0.9])
    bboxes = np.asarray(bboxes, dtype=np.float32)

    det = MagicMock()
    det.det_model.detect.return_value = (bboxes, None)
    monkeypatch.setattr(face_engine, "get_face_app", lambda det_size=None: det)

    emb_calls = {"n": 0}

    def fake_embed(image, bbox, kps, score):
        emb_calls["n"] += 1
        return np.asarray([float(emb_calls["n"])] + [0.0] * 511, dtype=np.float32)

    monkeypatch.setattr(face_engine, "_embed_from_det", fake_embed)
    img = np.zeros((120, 120, 3), dtype=np.uint8)
    out = face_engine.extract_face_features_multi_bgr(img, max_faces=8, require_quality=False)
    assert len(out) == 8
    assert emb_calls["n"] == 8


def test_multi_face_three_returns_three(monkeypatch):
    bboxes = np.asarray(
        [
            [0, 0, 10, 10, 0.9],
            [0, 0, 30, 30, 0.9],
            [0, 0, 20, 20, 0.9],
        ],
        dtype=np.float32,
    )
    det = MagicMock()
    det.det_model.detect.return_value = (bboxes, None)
    monkeypatch.setattr(face_engine, "get_face_app", lambda det_size=None: det)
    monkeypatch.setattr(
        face_engine,
        "_embed_from_det",
        lambda *a, **k: np.asarray([0.1] * 512, dtype=np.float32),
    )
    img = np.zeros((80, 80, 3), dtype=np.uint8)
    out = face_engine.extract_face_features_multi_bgr(img, max_faces=8)
    assert len(out) == 3


@pytest.mark.asyncio
async def test_event_dwell_splits_booths():
    company_id = uuid.uuid4()
    event_id = uuid.uuid4()
    member_id = uuid.uuid4()
    cam_a = uuid.uuid4()
    cam_b = uuid.uuid4()
    now = datetime.now(timezone.utc)

    event = MagicMock()
    event.companyId = company_id
    event.deletedAt = None
    event.name = "Expo"

    s1 = MagicMock(
        memberId=member_id,
        cameraId=cam_a,
        eventId=event_id,
        presenceRole="BOOTH",
        startedAt=now - timedelta(minutes=10),
        endedAt=now - timedelta(minutes=5),
        lastSeenAt=now - timedelta(minutes=5),
    )
    s2 = MagicMock(
        memberId=member_id,
        cameraId=cam_b,
        eventId=event_id,
        presenceRole="BOOTH",
        startedAt=now - timedelta(minutes=4),
        endedAt=now,
        lastSeenAt=now,
    )
    member = MagicMock(
        memberId=member_id, firstName="Ada", lastName="Lovelace", username="ada"
    )

    seq = [
        _Scalars([s1, s2]),
        MagicMock(all=lambda: [(cam_a, "Booth A"), (cam_b, "Booth B")]),
        _Scalars([member]),
    ]
    idx = {"i": 0}

    async def seq_execute(stmt):
        i = idx["i"]
        idx["i"] += 1
        return seq[i]

    db = AsyncMock()
    db.get = AsyncMock(return_value=event)
    db.execute = AsyncMock(side_effect=seq_execute)

    report = await presence.event_dwell_report(db, company_id, event_id)
    assert report["found"] is True
    assert len(report["people"]) == 1
    person = report["people"][0]
    assert person["memberId"] == str(member_id)
    assert len(person["booths"]) == 2
    assert person["totalDwellMinutes"] == pytest.approx(9.0, abs=0.1)


@pytest.mark.asyncio
async def test_event_dwell_missing_event():
    db = AsyncMock()
    db.get = AsyncMock(return_value=None)
    report = await presence.event_dwell_report(db, uuid.uuid4(), uuid.uuid4())
    assert report["found"] is False
    assert report["people"] == []
