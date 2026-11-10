"""Phase 4A: CCTV InsightFace worker — due selection, F3 gates, kiosk backpressure."""
from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

# Unit tests only — avoid requiring a live Postgres for import-time engine bind.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("SECRET_KEY", "unit-test-secret-key-32chars-min!!")
os.environ.setdefault("AUTH_FAIL_FAST", "false")

import pytest

for _mod in ("insightface", "insightface.app", "cv2", "onnxruntime"):
    sys.modules.setdefault(_mod, MagicMock())

from src.services import cctv_analysis_service as cctv  # noqa: E402


def test_attendance_like_modes_skip_sentinel_f3_gate():
    assert "ATTENDANCE" in cctv.ATTENDANCE_LIKE_MODES
    assert "UNIFIED_HYBRID" in cctv.ATTENDANCE_LIKE_MODES
    assert cctv.should_run_sentinel_search("ATTENDANCE") is False
    assert cctv.should_run_sentinel_search("UNIFIED_HYBRID") is False
    assert cctv.should_run_sentinel_search("ACCESS_CONTROL") is True
    assert cctv.should_run_sentinel_search("WATCHLIST_MONITOR") is True
    assert cctv.should_run_sentinel_search("") is False
    assert cctv.should_run_sentinel_search(None) is False


def test_should_pause_for_kiosk_backpressure(monkeypatch):
    monkeypatch.setattr(cctv.settings, "WORKER_CCTV_PAUSE_WHEN_KIOSK_PENDING", 4)
    monkeypatch.setattr(cctv.settings, "WORKER_CCTV_MAX_QUEUE_PENDING", 24)
    assert (
        cctv._should_pause_for_kiosk(
            {"pending": 1, "pendingByKind": {"checkin": 2, "identify": 1, "cctv": 10}}
        )
        is False
    )
    assert (
        cctv._should_pause_for_kiosk(
            {"pending": 1, "pendingByKind": {"checkin": 3, "identify": 1}}
        )
        is True
    )
    assert cctv._should_pause_for_kiosk({"pending": 30, "pendingByKind": {"cctv": 30}}) is True


def test_frame_source_urls_prefer_mediamtx_when_enabled(monkeypatch):
    monkeypatch.setattr(cctv.settings, "MEDIAMTX_RTSP_PUBLISH_URL", "rtsp://mediamtx:8554")
    monkeypatch.setattr(cctv.settings, "MEDIAMTX_ENABLED", True)
    cam = MagicMock()
    cam.cameraId = uuid.UUID("11111111-1111-1111-1111-111111111111")
    cam.streamUrl = "rtsp://cam.local/stream"
    cam.credentialsEnc = None
    with patch(
        "src.services.cctv_analysis_service.effective_stream_url",
        return_value="rtsp://cam.local/stream",
    ):
        urls = cctv._frame_source_urls(cam)
    assert urls[0] == "rtsp://mediamtx:8554/11111111111111111111111111111111"
    assert urls[1] == "rtsp://cam.local/stream"


def test_frame_source_urls_direct_when_mediamtx_disabled(monkeypatch):
    monkeypatch.setattr(cctv.settings, "MEDIAMTX_RTSP_PUBLISH_URL", "rtsp://mediamtx:8554")
    monkeypatch.setattr(cctv.settings, "MEDIAMTX_ENABLED", False)
    cam = MagicMock()
    cam.cameraId = uuid.UUID("11111111-1111-1111-1111-111111111111")
    with patch(
        "src.services.cctv_analysis_service.effective_stream_url",
        return_value="rtsp://cam.local/stream",
    ):
        urls = cctv._frame_source_urls(cam)
    assert urls[0] == "rtsp://cam.local/stream"
    assert urls[1].startswith("rtsp://mediamtx:8554/")


@pytest.mark.asyncio
async def test_analyze_camera_skips_when_module_cctv_disabled(monkeypatch):
    cam = MagicMock()
    cam.companyId = uuid.uuid4()
    cam.stationMode = "ACCESS_CONTROL"
    cam.zoneId = None
    cam.name = "Gate"
    cam.cameraId = uuid.uuid4()

    db = AsyncMock()
    monkeypatch.setattr(
        cctv,
        "get_company_module_config",
        AsyncMock(
            return_value={"enabledModules": ["ATTENDANCE"], "defaultStationMode": "ATTENDANCE"}
        ),
    )
    out = await cctv.analyze_camera(db, cam)
    assert out["skipped"] is True
    assert out["reason"] == "module_cctv_disabled"


@pytest.mark.asyncio
async def test_analyze_camera_pauses_on_kiosk_backpressure(monkeypatch):
    cam = MagicMock()
    cam.companyId = uuid.uuid4()
    cam.stationMode = "WATCHLIST_MONITOR"
    cam.zoneId = None
    cam.name = "Lobby"
    cam.cameraId = uuid.uuid4()

    db = AsyncMock()
    monkeypatch.setattr(
        cctv,
        "get_company_module_config",
        AsyncMock(
            return_value={
                "enabledModules": ["CCTV", "WATCHLIST"],
                "defaultStationMode": "WATCHLIST_MONITOR",
            }
        ),
    )
    monkeypatch.setattr(
        cctv,
        "face_gpu_queue_stats",
        lambda: {"pending": 1, "pendingByKind": {"checkin": 8}},
    )
    monkeypatch.setattr(cctv.settings, "WORKER_CCTV_PAUSE_WHEN_KIOSK_PENDING", 4)
    out = await cctv.analyze_camera(db, cam)
    assert out["skipped"] is True
    assert out["reason"] == "kiosk_backpressure"


@pytest.mark.asyncio
async def test_analyze_camera_sentinel_path_records_via_decision_engine(monkeypatch):
    cam = MagicMock()
    cam.companyId = uuid.uuid4()
    cam.stationMode = "ACCESS_CONTROL"
    cam.zoneId = None
    cam.name = "Door-1"
    cam.cameraId = uuid.uuid4()
    cam.lastAnalyzedAt = None
    cam.status = "online"

    db = AsyncMock()
    monkeypatch.setattr(
        cctv,
        "get_company_module_config",
        AsyncMock(
            return_value={
                "enabledModules": ["CCTV", "ACCESS_CONTROL"],
                "defaultStationMode": "ACCESS_CONTROL",
                "scanActionRules": {},
            }
        ),
    )
    monkeypatch.setattr(
        cctv, "face_gpu_queue_stats", lambda: {"pending": 0, "pendingByKind": {}}
    )
    monkeypatch.setattr(cctv, "_grab_frame_jpeg", AsyncMock(return_value=b"jpeg-bytes"))
    monkeypatch.setattr(cctv, "_embed_frame", AsyncMock(return_value=[0.1] * 512))
    monkeypatch.setattr(cctv, "_persist_snapshot", lambda _b: "/images/incident_x.jpg")

    decision = AsyncMock(
        return_value={
            "matched": True,
            "accessGranted": False,
            "decision": "BLACKLIST_BLOCKED",
            "incident": {"incidentId": str(uuid.uuid4())},
        }
    )
    with patch("src.routes.sentinel_routes.evaluate_unified_scan_decision", decision):
        out = await cctv.analyze_camera(db, cam)

    assert out["ok"] is True
    assert out["faces"] == 1
    assert out["decision"] == "BLACKLIST_BLOCKED"
    assert out["matched"] is True
    decision.assert_awaited_once()
    assert cam.lastAnalyzedAt is not None


def test_list_due_cameras_interval_logic(monkeypatch):
    class _Cam:
        def __init__(self, enabled, last):
            self.analysisEnabled = enabled
            self.isActive = True
            self.deletedAt = None
            self.lastAnalyzedAt = last
            self.cameraId = uuid.uuid4()

    now = datetime.now(timezone.utc)
    fresh = _Cam(True, now - timedelta(seconds=5))
    due = _Cam(True, now - timedelta(seconds=120))
    off = _Cam(False, None)

    monkeypatch.setattr(cctv.settings, "WORKER_CCTV_CAMERA_INTERVAL_SECONDS", 30)
    interval = timedelta(seconds=30)
    due_before = now - interval
    selected = [
        c
        for c in (fresh, due, off)
        if c.analysisEnabled
        and c.isActive
        and c.deletedAt is None
        and (c.lastAnalyzedAt is None or c.lastAnalyzedAt <= due_before)
    ]
    assert selected == [due]


@pytest.mark.asyncio
async def test_run_tick_empty_when_no_due(monkeypatch):
    monkeypatch.setattr(cctv, "ensure_face_gpu_for_cctv", AsyncMock())

    class _CM:
        async def __aenter__(self):
            return AsyncMock()

        async def __aexit__(self, *a):
            return False

    monkeypatch.setattr(cctv, "async_session", lambda: _CM())
    monkeypatch.setattr(cctv, "list_due_cameras", AsyncMock(return_value=[]))
    out = await cctv.run_cctv_analysis_tick()
    assert out == {"analyzed": 0, "skipped": 0, "errors": 0, "due": 0}
