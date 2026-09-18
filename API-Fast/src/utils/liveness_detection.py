"""Multi-frame liveness for InsightFace (same-person + bbox motion)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

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
