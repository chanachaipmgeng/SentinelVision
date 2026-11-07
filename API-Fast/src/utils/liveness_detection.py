"""Multi-frame liveness + passive anti-spoofing + optional ONNX PAD (Phase D8).

Heuristic path (YCrCb chrominance + specular glare) always runs. When
``FACE_PAD_MODEL_PATH`` points at a MiniFASNet-compatible ONNX file the crop is
also scored by that model. Weights are **not** committed — see ``docs/FACE-PAD.md``.
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np

from ..config.settings import settings

logger = logging.getLogger("dpu.pad")

_pad_lock = threading.Lock()
_pad_session = None
_pad_load_attempted = False
_pad_input_size = 80


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


def _pad_model_path() -> Optional[Path]:
    raw = (getattr(settings, "FACE_PAD_MODEL_PATH", None) or "").strip()
    if not raw:
        return None
    path = Path(raw)
    return path if path.is_file() else None


def _load_pad_session():
    """Lazy-load ONNX PAD session once per process."""
    global _pad_session, _pad_load_attempted, _pad_input_size
    if _pad_load_attempted:
        return _pad_session
    with _pad_lock:
        if _pad_load_attempted:
            return _pad_session
        _pad_load_attempted = True
        path = _pad_model_path()
        if path is None:
            logger.info(
                "FACE_PAD_MODEL_PATH unset or missing; PAD model disabled (heuristic only). "
                "See docs/FACE-PAD.md"
            )
            return None
        try:
            import onnxruntime as ort

            opts = ort.SessionOptions()
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            providers = ["CPUExecutionProvider"]
            # Prefer CUDA when the host already runs InsightFace on GPU.
            try:
                available = ort.get_available_providers()
                if "CUDAExecutionProvider" in available:
                    providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
            except Exception:
                pass
            session = ort.InferenceSession(str(path), sess_options=opts, providers=providers)
            # Infer square input size from the first input shape when static.
            try:
                shape = session.get_inputs()[0].shape
                for dim in shape:
                    if isinstance(dim, int) and dim > 1:
                        _pad_input_size = int(dim)
                        break
            except Exception:
                _pad_input_size = 80
            _pad_session = session
            logger.info("PAD model loaded from %s (input=%s)", path, _pad_input_size)
            return _pad_session
        except Exception:
            logger.exception("failed to load PAD model from %s", path)
            _pad_session = None
            return None


def reset_pad_for_tests() -> None:
    global _pad_session, _pad_load_attempted
    with _pad_lock:
        _pad_session = None
        _pad_load_attempted = False


def _prepare_pad_tensor(crop_bgr: np.ndarray, size: int) -> np.ndarray:
    """NCHW float32 in [0, 1] — MiniFASNet / Silent-Face style preprocess."""
    rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
    resized = cv2.resize(rgb, (size, size), interpolation=cv2.INTER_LINEAR)
    tensor = resized.astype(np.float32) / 255.0
    tensor = np.transpose(tensor, (2, 0, 1))[None, ...]
    return np.ascontiguousarray(tensor)


def _crop_face(
    image: np.ndarray, bbox: Optional[Union[np.ndarray, List[float]]], *, pad: float = 0.2
) -> Optional[np.ndarray]:
    h, w = image.shape[:2]
    if bbox is None or len(bbox) < 4:
        return image
    x1, y1, x2, y2 = [float(v) for v in bbox[:4]]
    bw, bh = max(1.0, x2 - x1), max(1.0, y2 - y1)
    left = max(0, int(x1 - bw * pad))
    top = max(0, int(y1 - bh * pad))
    right = min(w, int(x2 + bw * pad))
    bottom = min(h, int(y2 + bh * pad))
    if right <= left or bottom <= top:
        return None
    return image[top:bottom, left:right]


def check_pad_model_bgr(
    image: np.ndarray,
    bbox: Optional[Union[np.ndarray, List[float]]] = None,
    *,
    min_live_score: Optional[float] = None,
) -> Tuple[bool, str, Optional[float]]:
    """Run ONNX PAD when configured. Returns ``(ok, reason, live_score)``.

    When no model is loaded this returns ``(True, "pad_skipped", None)`` so callers
    can rely on the heuristic gate alone.
    """
    session = _load_pad_session()
    if session is None:
        return True, "pad_skipped", None
    crop = _crop_face(image, bbox)
    if crop is None or crop.size == 0 or min(crop.shape[:2]) < 16:
        return False, "Face region too small for PAD model.", None
    threshold = (
        float(min_live_score)
        if min_live_score is not None
        else float(getattr(settings, "FACE_PAD_MIN_LIVE_SCORE", 0.80) or 0.80)
    )
    try:
        inp = session.get_inputs()[0]
        tensor = _prepare_pad_tensor(crop, _pad_input_size)
        outputs = session.run(None, {inp.name: tensor})
        out = np.asarray(outputs[0]).reshape(-1)
        # Common layouts: [spoof, live] softmax or single live logit.
        if out.size >= 2:
            # softmax
            exp = np.exp(out - np.max(out))
            probs = exp / np.sum(exp)
            live_score = float(probs[-1])
        else:
            live_score = float(1.0 / (1.0 + np.exp(-float(out[0]))))
        if live_score < threshold:
            return (
                False,
                f"PAD rejected: live_score={live_score:.3f} < {threshold:.3f}.",
                live_score,
            )
        return True, f"PAD passed (live_score={live_score:.3f})", live_score
    except Exception as exc:
        logger.warning("PAD inference failed: %s", type(exc).__name__)
        # Fail closed when a model was explicitly configured.
        if bool(getattr(settings, "FACE_PAD_FAIL_CLOSED", True)):
            return False, "PAD inference failed.", None
        return True, "pad_inference_error_bypassed", None


def check_liveness_frame_bgr(
    image: np.ndarray,
    bbox: Optional[Union[np.ndarray, List[float]]] = None,
    *,
    min_chroma_std: Optional[float] = None,
    max_specular_ratio: Optional[float] = None,
) -> Tuple[bool, str]:
    """Heuristic anti-spoof + optional PAD model on one BGR frame."""
    chroma = (
        float(min_chroma_std)
        if min_chroma_std is not None
        else float(getattr(settings, "FACE_ANTISPOOF_MIN_CHROMA_STD", 2.0) or 2.0)
    )
    specular = (
        float(max_specular_ratio)
        if max_specular_ratio is not None
        else float(getattr(settings, "FACE_ANTISPOOF_MAX_SPECULAR_RATIO", 0.22) or 0.22)
    )
    if bool(getattr(settings, "FACE_ANTISPOOF_ENABLED", True)):
        ok, msg = check_passive_antispoof_bgr(
            image, bbox, min_chroma_std=chroma, max_specular_ratio=specular
        )
        if not ok:
            return False, msg
    else:
        msg = "heuristic_disabled"
    pad_ok, pad_msg, _score = check_pad_model_bgr(image, bbox)
    if not pad_ok:
        return False, pad_msg
    if pad_msg != "pad_skipped":
        return True, f"{msg}; {pad_msg}"
    return True, msg


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
