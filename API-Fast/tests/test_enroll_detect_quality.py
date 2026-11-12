"""Enrollment quality attached to /face/detect for admin auto-capture."""

from __future__ import annotations

import numpy as np

from src.utils.enrollment_quality import enrich_detect_with_enroll_quality


def test_enrich_detect_no_face():
    image = np.zeros((240, 320, 3), dtype=np.uint8)
    out = enrich_detect_with_enroll_quality(image, {"faces": []})
    assert out["enrollReady"] is False
    assert "No face" in out["enrollMessage"]
    assert out["minFaceRatio"] > 0


def test_enrich_detect_rejects_unusable_face():
    image = np.full((400, 400, 3), 180, dtype=np.uint8)
    # Flat solid image + tiny box fails blur and/or size gate.
    detect = {
        "faces": [{"x": 10, "y": 10, "width": 12, "height": 12, "score": 0.9}],
        "frameWidth": 400,
        "frameHeight": 400,
    }
    out = enrich_detect_with_enroll_quality(image, detect)
    assert out["enrollReady"] is False
    msg = out["enrollMessage"].lower()
    assert any(k in msg for k in ("small", "ratio", "blur", "sharp", "quality", "bright"))


def test_enrich_detect_gate_disabled(monkeypatch):
    from src.utils import enrollment_quality as eq

    monkeypatch.setattr(eq.settings, "ENROLL_QUALITY_GATE_ENABLED", False)
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    detect = {"faces": [{"x": 1, "y": 1, "width": 5, "height": 5, "score": 0.5}]}
    out = enrich_detect_with_enroll_quality(image, detect)
    assert out["enrollReady"] is True
