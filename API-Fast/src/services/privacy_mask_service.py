"""Dynamic PDPA Privacy Masking for CCTV frames & exported clips."""

from __future__ import annotations

from typing import Any

import numpy as np


def validate_privacy_masks(raw_masks: list[dict[str, Any]]) -> list[dict[str, float]]:
    """Validate and clamp normalized [0..1] privacy mask rectangles."""
    cleaned: list[dict[str, float]] = []
    for item in raw_masks or []:
        x = max(0.0, min(1.0, float(item.get("x", 0.0))))
        y = max(0.0, min(1.0, float(item.get("y", 0.0))))
        w = max(0.0, min(1.0 - x, float(item.get("w", 0.0))))
        h = max(0.0, min(1.0 - y, float(item.get("h", 0.0))))
        if w > 0.005 and h > 0.005:
            cleaned.append(
                {
                    "x": round(x, 4),
                    "y": round(y, 4),
                    "w": round(w, 4),
                    "h": round(h, 4),
                }
            )
    return cleaned


def apply_privacy_masks_to_bgr(
    frame: np.ndarray,
    masks: list[dict[str, Any]],
) -> np.ndarray:
    """Apply Gaussian blur over normalized [x, y, w, h] privacy zones on a BGR image."""
    if frame is None or frame.size == 0 or not masks:
        return frame
    try:
        import cv2  # lazy import so lightweight test runners don't fail if unused
    except ImportError:
        cv2 = None  # type: ignore[assignment]

    out = frame.copy()
    fh, fw = out.shape[:2]
    for box in validate_privacy_masks(masks):
        x1 = max(0, int(box["x"] * fw))
        y1 = max(0, int(box["y"] * fh))
        x2 = min(fw, int((box["x"] + box["w"]) * fw))
        y2 = min(fh, int((box["y"] + box["h"]) * fh))
        if x2 - x1 < 4 or y2 - y1 < 4:
            continue
        roi = out[y1:y2, x1:x2]
        blurred = cv2.GaussianBlur(roi, (51, 51), 0) if cv2 is not None else None
        if isinstance(blurred, np.ndarray) and blurred.shape == roi.shape:
            out[y1:y2, x1:x2] = blurred
        else:
            # Fallback when cv2 is mocked in full-suite tests or absent
            out[y1:y2, x1:x2] = np.broadcast_to(
                roi.mean(axis=(0, 1), keepdims=True).astype(out.dtype),
                roi.shape,
            )
    return out
