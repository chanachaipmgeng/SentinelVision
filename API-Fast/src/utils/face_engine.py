"""InsightFace (buffalo_l) face embedding + multi-frame liveness."""

from __future__ import annotations

import threading
from typing import List, Optional, Tuple

import cv2
import numpy as np
from insightface.app import FaceAnalysis

from .image_quality import check_image_quality
from .liveness_detection import check_multi_frame_liveness
from ..config.settings import settings

_face_app: Optional[FaceAnalysis] = None
_face_app_lock = threading.Lock()


def get_face_app() -> FaceAnalysis:
    """Lazy singleton FaceAnalysis (CPU)."""
    global _face_app
    if _face_app is not None:
        return _face_app
    with _face_app_lock:
        if _face_app is None:
            app = FaceAnalysis(
                name="buffalo_l",
                providers=["CPUExecutionProvider"],
            )
            app.prepare(ctx_id=-1, det_size=(640, 640))
            _face_app = app
    return _face_app


def _largest_face(faces):
    if not faces:
        return None
    return max(
        faces,
        key=lambda f: float(f.bbox[2] - f.bbox[0]) * float(f.bbox[3] - f.bbox[1]),
    )


def _read_bgr(image_path: str) -> np.ndarray:
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not read image: {image_path}")
    return image


def extract_face_features(
    image_path: str, *, require_quality: bool = True
) -> Optional[Tuple[List[float], np.ndarray]]:
    """
    Detect the largest face and return (normed_embedding list, bbox).
    bbox is [x1, y1, x2, y2].
    """
    if require_quality:
        is_good, message = check_image_quality(image_path)
        if not is_good:
            raise ValueError(message)

    image = _read_bgr(image_path)
    faces = get_face_app().get(image)
    face = _largest_face(faces)
    if face is None:
        return None

    embedding = face.normed_embedding
    if embedding is None:
        return None

    return embedding.astype(np.float32).tolist(), face.bbox.astype(np.float32)


def generate_face_encoding(image_path: str) -> Optional[List[float]]:
    """Quality-check + InsightFace 512-d embedding for enrollment."""
    try:
        result = extract_face_features(image_path, require_quality=True)
        if result is None:
            return None
        return result[0]
    except ValueError:
        raise
    except Exception as e:
        print(f"Error generating face encoding: {e}")
        return None


def verify_liveness_and_get_encoding(image_paths: List[str]) -> List[float]:
    """
    Multi-frame liveness (same person + motion) then return middle-frame embedding.
    Raises ValueError on failure.
    """
    if not image_paths:
        raise ValueError("No image frames provided for liveness check")

    frames = []
    for path in image_paths:
        # Skip blur/brightness on every frame; quality on the recognition frame only
        result = extract_face_features(path, require_quality=False)
        if result is None:
            frames.append(None)
            continue
        embedding, bbox = result
        frames.append({"embedding": embedding, "bbox": bbox})

    is_live, reason = check_multi_frame_liveness(
        frames,
        same_person_max_distance=settings.LIVENESS_SAME_PERSON_MAX_DISTANCE,
        min_bbox_motion=settings.LIVENESS_MIN_BBOX_MOTION,
    )
    if not is_live:
        raise ValueError(f"Liveness check failed: {reason}")

    mid = image_paths[len(image_paths) // 2]
    encoding = generate_face_encoding(mid)
    if encoding is None:
        raise ValueError("Could not generate face encoding from validation frame.")
    return encoding
