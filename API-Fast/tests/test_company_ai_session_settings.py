"""Company AI + session settings blobs (ai:{id}, session:{id})."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.services import company_ai_settings_service as ai  # noqa: E402
from src.services import company_session_settings_service as session  # noqa: E402

COMPANY_ID = uuid4()


@pytest.mark.asyncio
async def test_ai_defaults_when_missing(monkeypatch):
    monkeypatch.setattr(ai.settings, "FACE_RECOGNITION_THRESHOLD", 0.40)
    monkeypatch.setattr(ai.settings, "WORKER_CCTV_CAMERA_INTERVAL_SECONDS", 30)
    db = AsyncMock()
    db.get = AsyncMock(return_value=None)
    out = await ai.get_ai_settings(db, COMPANY_ID)
    assert out["faceMatchThreshold"] == 0.40
    assert out["cctvCameraIntervalSeconds"] == 30
    assert out["faceMatchThresholdOverride"] is False
    assert out["cctvCameraIntervalOverride"] is False


@pytest.mark.asyncio
async def test_ai_put_clamps_threshold(monkeypatch):
    monkeypatch.setattr(ai.settings, "FACE_RECOGNITION_THRESHOLD", 0.40)
    monkeypatch.setattr(ai.settings, "WORKER_CCTV_CAMERA_INTERVAL_SECONDS", 30)
    db = AsyncMock()
    stored = MagicMock()
    stored.value = {}
    db.get = AsyncMock(return_value=stored)
    db.commit = AsyncMock()

    out = await ai.put_ai_settings(
        db, COMPANY_ID, {"faceMatchThreshold": 0.99, "faceMatchThresholdOverride": True}
    )
    assert out["faceMatchThreshold"] == ai.FACE_THRESHOLD_MAX
    assert out["faceMatchThresholdOverride"] is True
    assert stored.value["faceMatchThreshold"] == ai.FACE_THRESHOLD_MAX

    out2 = await ai.put_ai_settings(
        db, COMPANY_ID, {"faceMatchThreshold": 0.01, "faceMatchThresholdOverride": True}
    )
    assert out2["faceMatchThreshold"] == ai.FACE_THRESHOLD_MIN


@pytest.mark.asyncio
async def test_ai_clear_override_restores_env(monkeypatch):
    monkeypatch.setattr(ai.settings, "FACE_RECOGNITION_THRESHOLD", 0.40)
    monkeypatch.setattr(ai.settings, "WORKER_CCTV_CAMERA_INTERVAL_SECONDS", 30)
    db = AsyncMock()
    stored = MagicMock()
    stored.value = {
        "faceMatchThreshold": 0.25,
        "faceMatchThresholdOverride": True,
    }
    db.get = AsyncMock(return_value=stored)
    db.commit = AsyncMock()

    out = await ai.put_ai_settings(db, COMPANY_ID, {"faceMatchThresholdOverride": False})
    assert out["faceMatchThresholdOverride"] is False
    assert out["faceMatchThreshold"] == 0.40
    assert "faceMatchThreshold" not in stored.value


@pytest.mark.asyncio
async def test_resolve_face_threshold_honours_override(monkeypatch):
    monkeypatch.setattr(ai.settings, "FACE_RECOGNITION_THRESHOLD", 0.40)
    monkeypatch.setattr(ai.settings, "WORKER_CCTV_CAMERA_INTERVAL_SECONDS", 30)
    db = AsyncMock()
    stored = MagicMock()
    stored.value = {
        "faceMatchThreshold": 0.22,
        "faceMatchThresholdOverride": True,
    }
    db.get = AsyncMock(return_value=stored)
    assert await ai.resolve_face_match_threshold(db, COMPANY_ID) == 0.22
    assert await ai.resolve_face_match_threshold(db, None) == 0.40


@pytest.mark.asyncio
async def test_session_idle_clamp():
    db = AsyncMock()
    stored = MagicMock()
    stored.value = {"idleTimeoutMinutes": 15}
    db.get = AsyncMock(return_value=stored)
    db.commit = AsyncMock()

    out = await session.put_session_settings(
        db, COMPANY_ID, {"idleTimeoutMinutes": 9999}
    )
    assert out["idleTimeoutMinutes"] == session.IDLE_TIMEOUT_MAX

    out2 = await session.put_session_settings(
        db, COMPANY_ID, {"idleTimeoutMinutes": -3}
    )
    assert out2["idleTimeoutMinutes"] == 0


@pytest.mark.asyncio
async def test_session_default_zero():
    db = AsyncMock()
    db.get = AsyncMock(return_value=None)
    out = await session.get_session_settings(db, COMPANY_ID)
    assert out == {"idleTimeoutMinutes": 0}
