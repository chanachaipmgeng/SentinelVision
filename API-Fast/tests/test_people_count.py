"""Phase 6D people counting — tracker, analytics, CSV, kiosk pause gate."""
from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("SECRET_KEY", "unit-test-secret-key-32chars-min!!")
os.environ.setdefault("AUTH_FAIL_FAST", "false")

for _mod in ("insightface", "insightface.app", "cv2", "onnxruntime"):
    sys.modules.setdefault(_mod, MagicMock())

from src.services import people_analytics as analytics  # noqa: E402
from src.services import people_count_service as pcs  # noqa: E402
from src.services.people_tracker import CentroidIoUTracker  # noqa: E402


def test_normalize_ai_config_disabled_without_roi():
    cfg = analytics.normalize_ai_config({"peopleEnabled": True})
    assert cfg["peopleEnabled"] is False
    assert cfg["hasRoi"] is False


def test_normalize_ai_config_enabled_with_line():
    cfg = analytics.normalize_ai_config(
        {"peopleEnabled": True, "line": [[0, 0], [100, 0]], "modes": ["line_crossing"]}
    )
    assert cfg["peopleEnabled"] is True
    assert "line_crossing" in cfg["modes"]


def test_line_crossing_triggers_on_segment_cross():
    state: dict = {}
    # First frame — establish center above the line.
    analytics.line_crossing(
        [{"bbox": [40, 10, 60, 30], "track_id": 1, "label": "person"}],
        state,
        {"line": [[0, 50], [100, 50]]},
    )
    # Second frame — center below the line → crossing.
    hits = analytics.line_crossing(
        [{"bbox": [40, 70, 60, 90], "track_id": 1, "label": "person"}],
        state,
        {"line": [[0, 50], [100, 50]]},
    )
    assert len(hits) == 1
    assert hits[0]["algorithm_code"] == "line_crossing"
    assert hits[0]["direction"] in ("in", "out")


def test_zone_count_crowd_flag():
    poly = [[0, 0], [100, 0], [100, 100], [0, 100]]
    dets = [
        {"bbox": [10, 10, 20, 20], "label": "person"},
        {"bbox": [30, 30, 40, 40], "label": "person"},
        {"bbox": [50, 50, 60, 60], "label": "person"},
    ]
    z = analytics.zone_count(dets, {"zone_polygon": poly, "crowd_min_count": 3})
    assert z["count"] == 3
    assert z["crowd"] is True


def test_loitering_after_min_seconds(monkeypatch):
    poly = [[0, 0], [100, 0], [100, 100], [0, 100]]
    state: dict = {}
    clock = {"t": 1000.0}

    def _mono():
        return clock["t"]

    monkeypatch.setattr(analytics.time, "monotonic", _mono)
    det = {"bbox": [10, 10, 20, 20], "track_id": 7, "label": "person"}
    assert analytics.loitering([det], state, {"loiter_polygon": poly, "loiter_min_seconds": 5}) == []
    clock["t"] = 1006.0
    hits = analytics.loitering([det], state, {"loiter_polygon": poly, "loiter_min_seconds": 5})
    assert len(hits) == 1
    assert hits[0]["algorithm_code"] == "loitering"


def test_tracker_assigns_stable_id():
    tr = CentroidIoUTracker(iou_threshold=0.3)
    a = tr.update([{"bbox": [10, 10, 50, 80], "confidence": 0.9, "label": "person"}])
    assert len(a) == 1
    tid = a[0]["track_id"]
    b = tr.update([{"bbox": [12, 12, 52, 82], "confidence": 0.88, "label": "person"}])
    assert b[0]["track_id"] == tid


def test_parse_camera_csv_with_header():
    text = "name,rtsp_url,protocol\nGate A,rtsp://cam/1,rtsp\nLobby,rtsp://cam/2,rtsp\n"
    rows = pcs.parse_camera_csv(text)
    assert len(rows) == 2
    assert rows[0]["name"] == "Gate A"
    assert rows[0]["streamUrl"].startswith("rtsp://")


def test_parse_kiosk_pending_from_metrics():
    text = (
        '# HELP dpu_face_gpu_queue_pending\n'
        'dpu_face_gpu_queue_pending{kind="checkin"} 3\n'
        'dpu_face_gpu_queue_pending{kind="identify"} 2\n'
        'dpu_face_gpu_queue_pending{kind="cctv"} 10\n'
    )
    by = pcs.parse_kiosk_pending_from_metrics(text)
    assert by["checkin"] == 3
    assert by["identify"] == 2


def test_should_pause_for_kiosk(monkeypatch):
    monkeypatch.setattr(pcs.settings, "WORKER_PEOPLE_PAUSE_WHEN_KIOSK_PENDING", 4)
    monkeypatch.setattr(pcs.settings, "WORKER_PEOPLE_MAX_QUEUE_PENDING", 24)
    assert pcs.should_pause_for_kiosk({"kioskPending": 2, "pending": 5}) is False
    assert pcs.should_pause_for_kiosk({"kioskPending": 4, "pending": 5}) is True
    assert pcs.should_pause_for_kiosk({"kioskPending": 0, "pending": 30}) is True


def test_filter_detections_by_roi_polygon():
    poly = [[0, 0], [50, 0], [50, 50], [0, 50]]
    dets = [
        {"bbox": [10, 10, 20, 20], "label": "person"},
        {"bbox": [80, 80, 90, 90], "label": "person"},
    ]
    kept = analytics.filter_detections_by_roi(dets, {"roi_polygon": poly})
    assert len(kept) == 1
