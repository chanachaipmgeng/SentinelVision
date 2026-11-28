"""AI core vision cutover (mocked :8090 vision process) for people YOLO."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.config import settings as settings_mod
from src.services.ai_core.flags import ai_core_vision_enabled
from src.services.ai_core.vision_client import reset_vision_ai_core_client
from src.services import people_yolo


@pytest.fixture(autouse=True)
def _reset_vision_ai_core(monkeypatch: pytest.MonkeyPatch):
    reset_vision_ai_core_client()
    monkeypatch.setattr(settings_mod.settings, "AI_CORE_VISION_URL", "")
    monkeypatch.setattr(settings_mod.settings, "AI_CORE_API_KEY", "")
    people_yolo.reset_session_for_tests()
    yield
    reset_vision_ai_core_client()
    people_yolo.reset_session_for_tests()


def test_ai_core_vision_disabled_by_default() -> None:
    assert ai_core_vision_enabled() is False


def test_ai_core_vision_requires_both(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings_mod.settings, "AI_CORE_VISION_URL", "http://127.0.0.1:8090")
    monkeypatch.setattr(settings_mod.settings, "AI_CORE_API_KEY", "")
    assert ai_core_vision_enabled() is False
    monkeypatch.setattr(settings_mod.settings, "AI_CORE_API_KEY", "dev-key")
    assert ai_core_vision_enabled() is True


def test_model_available_when_vision_flagged(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings_mod.settings, "AI_CORE_VISION_URL", "http://127.0.0.1:8090")
    monkeypatch.setattr(settings_mod.settings, "AI_CORE_API_KEY", "dev-key")
    monkeypatch.setattr(settings_mod.settings, "PEOPLE_YOLO_ONNX_PATH", "/no/such/yolo.onnx")
    assert people_yolo.model_available() is True


def test_detect_persons_jpeg_uses_ai_core(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings_mod.settings, "AI_CORE_VISION_URL", "http://127.0.0.1:8090")
    monkeypatch.setattr(settings_mod.settings, "AI_CORE_API_KEY", "dev-key")

    fake = MagicMock()
    fake.detect.return_value = {
        "width": 640,
        "height": 480,
        "modelId": "yolov8n",
        "detections": [
            {
                "bbox": [10.0, 20.0, 110.0, 220.0],
                "confidence": 0.91,
                "label": "person",
                "classId": 0,
            },
            {
                "bbox": [1.0, 2.0, 3.0, 4.0],
                "confidence": 0.8,
                "label": "car",
                "classId": 2,
            },
        ],
    }
    monkeypatch.setattr(
        "src.services.ai_core.vision_client.get_vision_ai_core_client",
        lambda: fake,
    )

    dets = people_yolo.detect_persons_jpeg(b"\xff\xd8fakejpeg", confidence=0.4)
    assert len(dets) == 1
    assert dets[0]["label"] == "person"
    assert dets[0]["bbox"] == [10.0, 20.0, 110.0, 220.0]
    fake.detect.assert_called_once()
    kwargs = fake.detect.call_args.kwargs
    assert kwargs.get("classes") == "person"


def test_detect_persons_jpeg_falls_back_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings_mod.settings, "AI_CORE_VISION_URL", "http://127.0.0.1:8090")
    monkeypatch.setattr(settings_mod.settings, "AI_CORE_API_KEY", "dev-key")

    fake = MagicMock()
    fake.detect.side_effect = RuntimeError("vision down")
    monkeypatch.setattr(
        "src.services.ai_core.vision_client.get_vision_ai_core_client",
        lambda: fake,
    )

    # Force local ONNX missing so fallback returns []
    monkeypatch.setattr(people_yolo, "_ensure_session", lambda: False)
    # Minimal JPEG SOI/EOI markers — remote fails first, then decode may fail → []
    # Avoid cv2.imencode (OpenCV 5.x CI wheel return shape differs).
    dets = people_yolo.detect_persons_jpeg(b"\xff\xd8\xff\xd9")
    assert dets == []
    fake.detect.assert_called()
