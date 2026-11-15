"""Enrollment quality gate (Phase D8).

Extends blur/brightness with face-size and pose (landmark geometry) checks so
kiosk enrollment rejects unusable frames before they become ``FaceEncoding`` rows.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple, Union

import cv2
import numpy as np

from ..config.settings import settings
from .image_quality import check_image_quality_bgr


def _face_size_ratio(image: np.ndarray, bbox: Union[np.ndarray, list]) -> float:
    h, w = image.shape[:2]
    if h <= 0 or w <= 0:
        return 0.0
    x1, y1, x2, y2 = [float(v) for v in bbox[:4]]
    area = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    return float(area / float(h * w))


def _pose_from_kps(kps: Optional[np.ndarray]) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """Rough yaw/pitch/roll proxies from 5-point InsightFace landmarks (no 3D model).

    Returns ``(yaw_proxy_deg, pitch_proxy_deg, roll_deg)``.
    """
    if kps is None:
        return None, None, None
    arr = np.asarray(kps, dtype=np.float32)
    if arr.ndim != 2 or arr.shape[0] < 5:
        return None, None, None
    # InsightFace order: left_eye, right_eye, nose, left_mouth, right_mouth
    left_eye, right_eye, nose, left_mouth, right_mouth = arr[0], arr[1], arr[2], arr[3], arr[4]
    eye_mid = (left_eye + right_eye) * 0.5
    mouth_mid = (left_mouth + right_mouth) * 0.5
    eye_dist = float(np.linalg.norm(right_eye - left_eye)) + 1e-6
    face_v_span = float(max(1.0, abs(mouth_mid[1] - eye_mid[1])))
    # Horizontal offset of nose from eye midpoint / IOD → yaw proxy
    yaw = float(np.degrees(np.arctan2(nose[0] - eye_mid[0], eye_dist)))
    # Vertical offset of nose relative to eye-mouth midpoint → pitch proxy
    vert_mid_y = (eye_mid[1] + mouth_mid[1]) * 0.5
    pitch = float(np.degrees(np.arctan2(nose[1] - vert_mid_y, face_v_span)))
    roll = float(np.degrees(np.arctan2(right_eye[1] - left_eye[1], right_eye[0] - left_eye[0])))
    return yaw, pitch, roll


def check_enrollment_quality_bgr(
    image: np.ndarray,
    bbox: Optional[Union[np.ndarray, list]] = None,
    kps: Optional[np.ndarray] = None,
    *,
    blur_threshold: Optional[float] = None,
    angle: Optional[str] = None,
) -> Tuple[bool, str, Dict[str, Any]]:
    """Return ``(ok, reason, scores)`` for enrollment frames."""
    scores: Dict[str, Any] = {}
    if image is None or not hasattr(image, "shape") or image.ndim != 3:
        return False, "Invalid image for enrollment quality check.", scores

    ok, msg = check_image_quality_bgr(image, bbox, blur_threshold=blur_threshold)
    scores["baseQuality"] = msg
    if not ok:
        return False, msg, scores

    if bbox is None or len(bbox) < 4:
        return False, "Face bounding box required for enrollment quality gate.", scores

    min_ratio = float(getattr(settings, "ENROLL_MIN_FACE_RATIO", 0.07) or 0.07)
    ratio = _face_size_ratio(image, bbox)
    scores["faceRatio"] = ratio
    if ratio < min_ratio:
        return (
            False,
            f"Face too small for enrollment (ratio={ratio:.3f} < {min_ratio}). Move closer.",
            scores,
        )

    angle_norm = (angle or "FRONT").strip().upper()
    max_yaw = float(getattr(settings, "ENROLL_MAX_YAW_DEG", 25.0) or 25.0)
    if angle_norm in ("LEFT", "RIGHT"):
        max_yaw = max(max_yaw, 55.0)
    max_pitch = 40.0 if angle_norm in ("UP", "DOWN") else 25.0
    max_roll = float(getattr(settings, "ENROLL_MAX_ROLL_DEG", 20.0) or 20.0)
    yaw, pitch, roll = _pose_from_kps(kps)
    if yaw is not None:
        scores["yawDeg"] = yaw
    if pitch is not None:
        scores["pitchDeg"] = pitch
    if roll is not None:
        scores["rollDeg"] = roll
    if yaw is not None and abs(yaw) > max_yaw:
        return (
            False,
            f"Face pose too angled for enrollment (|yaw|={abs(yaw):.1f}° > {max_yaw}°).",
            scores,
        )
    if pitch is not None and abs(pitch) > max_pitch:
        return (
            False,
            f"Face pitch too extreme for enrollment (|pitch|={abs(pitch):.1f}° > {max_pitch}°).",
            scores,
        )
    if roll is not None and abs(roll) > max_roll:
        return (
            False,
            f"Face tilt too high for enrollment (|roll|={abs(roll):.1f}° > {max_roll}°).",
            scores,
        )

    # Det score / sharpness proxy already covered; expose a composite for metrics.
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    x1, y1, x2, y2 = [int(float(v)) for v in bbox[:4]]
    h, w = gray.shape[:2]
    crop = gray[max(0, y1) : min(h, y2), max(0, x1) : min(w, x2)]
    sharpness = float(cv2.Laplacian(crop, cv2.CV_64F).var()) if crop.size else 0.0
    scores["sharpness"] = sharpness
    min_sharp = float(getattr(settings, "ENROLL_MIN_SHARPNESS", 25.0) or 25.0)
    if min_sharp > 0 and sharpness < min_sharp:
        return (
            False,
            f"Enrollment sharpness too low ({sharpness:.1f} < {min_sharp}).",
            scores,
        )

    return True, "Enrollment quality gate passed.", scores


def enrich_detect_with_enroll_quality(
    image: np.ndarray,
    detect_result: dict,
    kps_list: Optional[list] = None,
) -> dict:
    """Attach ``enrollReady`` / message / scores for admin auto-capture gating.

    Uses the same ENROLL_* settings as add-face. Pose checks run only when
    landmark sets are provided (local InsightFace detect); Face Core detect
    still gates on size / blur / sharpness.
    """
    out = dict(detect_result or {})
    faces = list(out.get("faces") or [])
    out["enrollReady"] = False
    out["enrollMessage"] = "No face detected"
    out["enrollScores"] = {}
    out["minFaceRatio"] = float(getattr(settings, "ENROLL_MIN_FACE_RATIO", 0.07) or 0.07)
    if not faces:
        return out

    best_i = max(
        range(len(faces)),
        key=lambda i: float(faces[i].get("width") or 0) * float(faces[i].get("height") or 0),
    )
    face = faces[best_i]
    x = float(face.get("x") or 0)
    y = float(face.get("y") or 0)
    w = float(face.get("width") or 0)
    h = float(face.get("height") or 0)
    bbox = [x, y, x + w, y + h]
    kps = None
    if kps_list is not None and 0 <= best_i < len(kps_list):
        kps = kps_list[best_i]

    if not bool(getattr(settings, "ENROLL_QUALITY_GATE_ENABLED", True)):
        out["enrollReady"] = True
        out["enrollMessage"] = "Enrollment quality gate disabled."
        return out

    ok, message, scores = check_enrollment_quality_bgr(image, bbox, kps)
    out["enrollReady"] = bool(ok)
    out["enrollMessage"] = message
    out["enrollScores"] = scores
    return out
