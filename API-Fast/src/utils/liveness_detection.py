"""Multi-frame & single-frame passive liveness / anti-spoofing for InsightFace."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np


def cosine_distance(a: List[float], b: List[float]) -> float:
    """Cosine distance for L2-normalized vectors: 1 - dot(a, b)."""
    va = np.asarray(a, dtype=np.float32)
    vb = np.asarray(b, dtype=np.float32)
    return float(1.0 - np.dot(va, vb))


def bbox_center(bbox: np.ndarray) -> Tuple[float, float]:
    return (
        float((bbox[0] + bbox[2]) / 2.0),
        float((bbox[1] + bbox[3]) / 2.0),
    )


def check_passive_antispoof_bgr(
    image: np.ndarray,
    bbox: Optional[Union[np.ndarray, List[float]]] = None,
    *,
    min_chroma_std: float = 2.0,
    max_specular_ratio: float = 0.22,
) -> Tuple[bool, str]:
    """
    Single-frame passive anti-spoofing (texture, chrominance & specular screen glare):
    1. Crops the face region from BGR image.
    2. Converts to YCrCb and verifies skin chrominance variance (Cr/Cb std dev).
       Flat grayscale prints, monochrome IR/paper attacks, or washed-out screens fail this gate.
    3. Verifies specular reflection / screen over-saturation clipping ratio (Y > 250 with low chroma)
       to reject phone/tablet screen replay glare.
    """
    if image is None or not hasattr(image, "shape") or image.ndim != 3:
        return False, "Invalid image frame for anti-spoofing check."

    h, w = image.shape[:2]
    if bbox is not None and len(bbox) >= 4:
        x1, y1, x2, y2 = [float(v) for v in bbox[:4]]
        left = max(0, int(x1))
        top = max(0, int(y1))
        right = min(w, int(x2))
        bottom = min(h, int(y2))
        crop = image[top:bottom, left:right] if (right > left and bottom > top) else image
    else:
        crop = image

    if crop.size == 0 or crop.shape[0] < 16 or crop.shape[1] < 16:
        return False, "Face region too small for anti-spoofing verification."

    ycrcb = cv2.cvtColor(crop, cv2.COLOR_BGR2YCrCb)
    y_chan = ycrcb[:, :, 0].astype(np.float32)
    cr_chan = ycrcb[:, :, 1].astype(np.float32)
    cb_chan = ycrcb[:, :, 2].astype(np.float32)

    chroma_std = float(0.5 * (np.std(cr_chan) + np.std(cb_chan)))
    if chroma_std < float(min_chroma_std):
        return (
            False,
            f"Anti-spoofing rejected: insufficient skin chrominance variance ({chroma_std:.2f} < {min_chroma_std}).",
        )

    specular_mask = (y_chan >= 250.0) & (np.abs(cr_chan - 128.0) < 8.0) & (np.abs(cb_chan - 128.0) < 8.0)
    specular_ratio = float(np.mean(specular_mask))
    if specular_ratio > float(max_specular_ratio):
        return (
            False,
            f"Anti-spoofing rejected: excessive screen glare / specular reflection ({specular_ratio:.2%}).",
        )

    return True, f"Passive anti-spoofing passed (chroma_std={chroma_std:.2f}, glare={specular_ratio:.2%})"


def check_multi_frame_liveness(
    frames: List[Optional[Dict[str, Any]]],
    *,
    same_person_max_distance: float,
    min_bbox_motion: float,
) -> Tuple[bool, str]:
    """
    frames: list of None or {"embedding": list[float], "bbox": np.ndarray}

    Passes when:
    1. At least half of frames contain a single detected face
    2. Embeddings across valid frames are the same person (low cosine distance)
    3. BBox centers move enough to reject a static photo replay
    """
    valid = [f for f in frames if f is not None]
    if len(valid) < max(2, len(frames) / 2):
        return False, "Face not consistently detected in frames."

    embeddings = [f["embedding"] for f in valid if f.get("embedding")]
    if len(embeddings) >= 2:
        anchor = embeddings[0]
        for emb in embeddings[1:]:
            dist = cosine_distance(anchor, emb)
            if dist > same_person_max_distance:
                return False, f"Face identity inconsistent across frames (distance={dist:.3f})."

    centers = [bbox_center(f["bbox"]) for f in valid]
    max_motion = 0.0
    for i in range(len(centers)):
        for j in range(i + 1, len(centers)):
            dx = centers[i][0] - centers[j][0]
            dy = centers[i][1] - centers[j][1]
            max_motion = max(max_motion, float(np.hypot(dx, dy)))

    if max_motion < min_bbox_motion:
        return False, f"Insufficient face motion (motion={max_motion:.2f}px)."

    return True, f"Liveness passed (motion={max_motion:.2f}px, frames={len(valid)})"
