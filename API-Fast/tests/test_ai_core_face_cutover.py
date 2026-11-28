"""AI core face cutover (mocked :8089 face process)."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

# Avoid requiring InsightFace weights in unit tests.
sys.modules.setdefault("insightface", MagicMock())
sys.modules.setdefault("insightface.app", MagicMock())
sys.modules.setdefault("insightface.app.common", MagicMock())

import numpy as np  # noqa: E402
import pytest  # noqa: E402

from src.config import settings as settings_mod  # noqa: E402
from src.services.ai_core.face_client import reset_face_ai_core_client  # noqa: E402
from src.services.ai_core.flags import ai_core_face_enabled  # noqa: E402
from src.utils import face_engine  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_face_ai_core(monkeypatch: pytest.MonkeyPatch):
    reset_face_ai_core_client()
    monkeypatch.setattr(settings_mod.settings, "AI_CORE_FACE_URL", "")
    monkeypatch.setattr(settings_mod.settings, "AI_CORE_API_KEY", "")
    yield
    reset_face_ai_core_client()


def _unit512(seed: float = 0.1) -> list[float]:
    arr = np.full(512, seed, dtype=np.float64)
    arr = arr / np.linalg.norm(arr)
    return arr.tolist()


def test_ai_core_face_disabled_by_default() -> None:
    assert ai_core_face_enabled() is False


def test_ai_core_face_requires_both(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings_mod.settings, "AI_CORE_FACE_URL", "http://127.0.0.1:8089")
    monkeypatch.setattr(settings_mod.settings, "AI_CORE_API_KEY", "")
    assert ai_core_face_enabled() is False
    monkeypatch.setattr(settings_mod.settings, "AI_CORE_API_KEY", "dev-key")
    assert ai_core_face_enabled() is True


def test_detect_bytes_uses_ai_core(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings_mod.settings, "AI_CORE_FACE_URL", "http://127.0.0.1:8089")
    monkeypatch.setattr(settings_mod.settings, "AI_CORE_API_KEY", "dev-key")

    fake = MagicMock()
    fake.detect.return_value = {
        "width": 640,
        "height": 480,
        "faces": [{"x": 10, "y": 20, "width": 100, "height": 120, "score": 0.9}],
    }
    monkeypatch.setattr(
        "src.services.ai_core.face_client.get_face_ai_core_client",
        lambda: fake,
    )

    out = face_engine.detect_faces_bytes(b"\xff\xd8fakejpeg", for_enrollment=False)
    assert out["frameWidth"] == 640
    assert out["faces"][0]["width"] == 100
    fake.detect.assert_called_once()


def test_embed_bgr_uses_ai_core(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings_mod.settings, "AI_CORE_FACE_URL", "http://127.0.0.1:8089")
    monkeypatch.setattr(settings_mod.settings, "AI_CORE_API_KEY", "dev-key")

    emb = _unit512(0.2)
    fake = MagicMock()
    fake.embed.return_value = {
        "modelVersion": "buffalo_l",
        "faces": [
            {
                "bbox": {"x": 1, "y": 2, "width": 50, "height": 60, "score": 0.95},
                "embedding": emb,
                "score": 0.95,
            }
        ],
    }
    monkeypatch.setattr(
        "src.services.ai_core.face_client.get_face_ai_core_client",
        lambda: fake,
    )

    img = np.zeros((120, 100, 3), dtype=np.uint8)
    result = face_engine.extract_face_features_bgr(img, require_quality=False)
    assert result is not None
    vec, bbox = result
    assert len(vec) == 512
    assert bbox.shape == (4,)
    fake.embed.assert_called()


def test_detect_falls_back_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings_mod.settings, "AI_CORE_FACE_URL", "http://127.0.0.1:8089")
    monkeypatch.setattr(settings_mod.settings, "AI_CORE_API_KEY", "dev-key")

    fake = MagicMock()
    fake.detect.side_effect = ConnectionError("down")
    monkeypatch.setattr(
        "src.services.ai_core.face_client.get_face_ai_core_client",
        lambda: fake,
    )

    # Avoid loading InsightFace — stub local detect path
    monkeypatch.setattr(
        face_engine,
        "detect_faces_bgr",
        lambda image, for_enrollment=False: {
            "frameWidth": 1,
            "frameHeight": 1,
            "faces": [],
        },
    )
    # detect_faces_bytes calls remote then decode+detect_faces_bgr; stub decode
    monkeypatch.setattr(face_engine, "decode_image_bytes", lambda *_a, **_k: np.zeros((8, 8, 3), dtype=np.uint8))

    out = face_engine.detect_faces_bytes(b"abc", for_enrollment=False)
    assert out["faces"] == []
