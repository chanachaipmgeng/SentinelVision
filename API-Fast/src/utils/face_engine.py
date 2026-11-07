"""InsightFace (buffalo_l) face embedding + multi-frame & passive anti-spoofing liveness."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Tuple

import cv2
import numpy as np
from insightface.app import FaceAnalysis

from .image_quality import check_image_quality, check_image_quality_bgr
from .liveness_detection import (
    check_multi_frame_liveness,
    check_passive_antispoof_bgr,
    cosine_distance,
)
from ..config.settings import settings

_face_apps: dict = {}
_face_app_lock = threading.Lock()
_thread_device = threading.local()
# Separate from the GPU ThreadPoolExecutor so JPEG decode does not steal
# inference worker slots (and so decode can oversubscribe CPU cores).
_decode_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="face-decode")


def get_decode_executor() -> ThreadPoolExecutor:
    return _decode_executor


def set_thread_device(device: str) -> None:
    _thread_device.device = device


def _active_device() -> str:
    pinned = getattr(_thread_device, "device", None)
    if pinned:
        return pinned
    devices = settings.face_device_list()
    return devices[0] if devices else "cpu"


def _cuda_runtime_usable() -> bool:
    """True only when CUDA EP exists AND the container can see a GPU."""
    try:
        import onnxruntime as ort

        if "CUDAExecutionProvider" not in set(ort.get_available_providers()):
            return False
    except Exception:
        return False

    try:
        import subprocess

        result = subprocess.run(
            ["nvidia-smi", "-L"],
            capture_output=True,
            text=True,
            timeout=8,
        )
        if result.returncode != 0:
            print(
                f"nvidia-smi failed (rc={result.returncode}): "
                f"{(result.stderr or result.stdout or '').strip()[:200]}",
                flush=True,
            )
            return False
        return "GPU" in (result.stdout or "")
    except Exception as exc:
        print(f"GPU probe failed ({exc})", flush=True)
        return False


def _resolve_providers_and_ctx(device: str) -> Tuple[List[str], int]:
    """Match AI_VISION worker FaceRecognizer provider selection."""
    use_cuda = device.lower().startswith("cuda")
    if use_cuda:
        if not _cuda_runtime_usable():
            print(
                "FACE_DEVICE is cuda but GPU is not usable in this container; "
                "falling back to CPU. Enable Docker Desktop GPU and start with "
                "docker-compose.gpu.yml when ready.",
                flush=True,
            )
            return ["CPUExecutionProvider"], -1

        gpu_id = 0
        if ":" in device:
            gpu_id = int(device.split(":")[1])
        return ["CUDAExecutionProvider", "CPUExecutionProvider"], gpu_id

    return ["CPUExecutionProvider"], -1


def get_face_app(device: Optional[str] = None, *, det_size: Optional[int] = None) -> FaceAnalysis:
    """Lazy FaceAnalysis per CUDA device (or CPU)."""
    global _face_apps
    device = (device or _active_device() or "cpu").strip()
    size = int(det_size or settings.FACE_EMBED_DET_SIZE)
    key = f"{device}:{size}"
    cached = _face_apps.get(key)
    if cached is not None:
        return cached
    with _face_app_lock:
        cached = _face_apps.get(key)
        if cached is not None:
            return cached
        providers, ctx_id = _resolve_providers_and_ctx(device)
        provider_options = None
        if ctx_id >= 0 and providers and providers[0] == "CUDAExecutionProvider":
            provider_options = [{"device_id": ctx_id}, {}]
        print(
            f"Loading InsightFace buffalo_l device={device} providers={providers} "
            f"ctx_id={ctx_id} provider_options={provider_options} det={size}",
            flush=True,
        )
        try:
            kwargs: dict = {"name": "buffalo_l", "providers": providers}
            if provider_options is not None:
                kwargs["provider_options"] = provider_options
            app = FaceAnalysis(**kwargs)
            app.prepare(ctx_id=ctx_id, det_size=(size, size))
        except Exception as exc:
            if ctx_id < 0:
                raise
            print(f"CUDA InsightFace init failed ({exc}); falling back to CPU.", flush=True)
            app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
            app.prepare(ctx_id=-1, det_size=(size, size))
            key = f"cpu:{size}"
        _face_apps[key] = app
        print(f"InsightFace ready key={key}", flush=True)
        return app


def get_face_device() -> str:
    return _active_device()


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


def detect_bbox(image_path: str) -> Optional[np.ndarray]:
    """Detector only (smaller det_size) for liveness motion checks."""
    image = _read_bgr(image_path)
    app = get_face_app(det_size=int(settings.FACE_DETECT_DET_SIZE))
    bboxes, _kpss = app.det_model.detect(image, max_num=1, metric="default")
    if bboxes is None or len(bboxes) == 0:
        return None
    return np.asarray(bboxes[0][:4], dtype=np.float32)


def decode_image_bytes(image_bytes: bytes, *, for_detect: bool = False) -> np.ndarray:
    """JPEG/PNG decode outside the GPU worker so inference slots stay busy."""
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    image = None
    if for_detect and len(image_bytes) >= 80_000:
        image = cv2.imdecode(arr, cv2.IMREAD_REDUCED_COLOR_2)
    if image is None:
        image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Could not decode frame")
    if for_detect:
        height, width = image.shape[:2]
        det = int(settings.FACE_DETECT_DET_SIZE)
        if width > 2 * det:
            scale = (2.0 * det) / float(width)
            image = cv2.resize(
                image,
                (int(round(width * scale)), int(round(height * scale))),
                interpolation=cv2.INTER_AREA,
            )
    return image


def detect_faces_bgr(image: np.ndarray) -> dict:
    """Fast detection-only pass for the kiosk stream (no embeddings)."""
    if image is None or not hasattr(image, "shape"):
        raise ValueError("Could not decode frame")
    height, width = image.shape[:2]

    app = get_face_app(det_size=int(settings.FACE_DETECT_DET_SIZE))
    bboxes, _kpss = app.det_model.detect(image, max_num=0, metric="default")

    faces = []
    if bboxes is not None:
        for box in bboxes:
            x1, y1, x2, y2, score = (float(v) for v in box[:5])
            x1 = max(0.0, x1)
            y1 = max(0.0, y1)
            faces.append(
                {
                    "x": x1,
                    "y": y1,
                    "width": max(0.0, x2 - x1),
                    "height": max(0.0, y2 - y1),
                    "score": score,
                }
            )

    return {"frameWidth": width, "frameHeight": height, "faces": faces}


def detect_faces_bytes(image_bytes: bytes) -> dict:
    """Decode + detect (prefer decode_image_bytes + detect_faces_bgr off the GPU path)."""
    return detect_faces_bgr(decode_image_bytes(image_bytes, for_detect=True))


def _largest_det_index(bboxes) -> Optional[int]:
    if bboxes is None or len(bboxes) == 0:
        return None
    areas = []
    for box in bboxes:
        x1, y1, x2, y2 = (float(v) for v in box[:4])
        areas.append(max(0.0, x2 - x1) * max(0.0, y2 - y1))
    return int(max(range(len(areas)), key=lambda i: areas[i]))


def _embed_from_det(
    image: np.ndarray,
    bbox: np.ndarray,
    kps: Optional[np.ndarray],
    det_score: float,
) -> Optional[np.ndarray]:
    """Run recognition on a pre-detected face (skips the 640 embed detector)."""
    from insightface.app.common import Face

    app = get_face_app(det_size=int(settings.FACE_EMBED_DET_SIZE))
    face = Face(
        bbox=np.asarray(bbox[:4], dtype=np.float32),
        kps=None if kps is None else np.asarray(kps, dtype=np.float32),
        det_score=float(det_score),
    )
    rec = app.models.get("recognition")
    if rec is None:
        faces = app.get(image)
        largest = _largest_face(faces)
        if largest is None or largest.normed_embedding is None:
            return None
        return largest.normed_embedding.astype(np.float32)
    rec.get(image, face)
    if face.normed_embedding is None:
        return None
    return face.normed_embedding.astype(np.float32)


def extract_face_features_bgr(
    image: np.ndarray,
    *,
    require_quality: bool = True,
    blur_threshold: Optional[float] = None,
    fast_detect: bool = True,
) -> Optional[Tuple[List[float], np.ndarray]]:
    """Detect the largest face and return (normed_embedding list, bbox)."""
    if image is None or not hasattr(image, "shape"):
        raise ValueError("Could not decode frame")

    use_fast = bool(fast_detect) and bool(getattr(settings, "FACE_FAST_EMBED_DETECT", True))
    if use_fast:
        det_app = get_face_app(det_size=int(settings.FACE_DETECT_DET_SIZE))
        bboxes, kpss = det_app.det_model.detect(image, max_num=0, metric="default")
        idx = _largest_det_index(bboxes)
        if idx is None:
            return None
        box = np.asarray(bboxes[idx], dtype=np.float32)
        bbox = box[:4]
        score = float(box[4]) if box.shape[0] > 4 else 0.0
        kps = None if kpss is None else np.asarray(kpss[idx], dtype=np.float32)
        if require_quality:
            is_good, message = check_image_quality_bgr(
                image, bbox, blur_threshold=blur_threshold
            )
            if not is_good:
                raise ValueError(message)
        embedding = _embed_from_det(image, bbox, kps, score)
        if embedding is None:
            return None
        return embedding.astype(np.float32).tolist(), bbox.astype(np.float32)

    faces = get_face_app().get(image)
    face = _largest_face(faces)
    if face is None:
        return None

    if require_quality:
        is_good, message = check_image_quality_bgr(
            image, face.bbox, blur_threshold=blur_threshold
        )
        if not is_good:
            raise ValueError(message)

    embedding = face.normed_embedding
    if embedding is None:
        return None

    return embedding.astype(np.float32).tolist(), face.bbox.astype(np.float32)


def _synthetic_kps_for_crop(width: int, height: int) -> np.ndarray:
    """Approximate 5-point landmarks for a tight face crop (InsightFace order)."""
    w = float(max(width, 1))
    h = float(max(height, 1))
    return np.asarray(
        [
            [0.30 * w, 0.38 * h],
            [0.70 * w, 0.38 * h],
            [0.50 * w, 0.55 * h],
            [0.35 * w, 0.75 * h],
            [0.65 * w, 0.75 * h],
        ],
        dtype=np.float32,
    )


def extract_face_features_from_crop_bgr(
    image: np.ndarray,
    *,
    require_quality: bool = False,
    blur_threshold: Optional[float] = None,
) -> Optional[Tuple[List[float], np.ndarray]]:
    """Embed a pre-cropped face image for Edge / Smart Camera clients."""
    if image is None or not hasattr(image, "shape"):
        raise ValueError("Could not decode frame")
    height, width = image.shape[:2]
    if height < 32 or width < 32:
        raise ValueError("Crop too small for embedding")

    try:
        features = extract_face_features_bgr(
            image,
            require_quality=require_quality,
            blur_threshold=blur_threshold,
            fast_detect=False,
        )
        if features is not None:
            return features
    except ValueError:
        raise

    try:
        features = extract_face_features_bgr(
            image,
            require_quality=require_quality,
            blur_threshold=blur_threshold,
            fast_detect=True,
        )
        if features is not None:
            return features
    except ValueError:
        raise

    bbox = np.asarray([0.0, 0.0, float(width - 1), float(height - 1)], dtype=np.float32)
    if require_quality:
        is_good, message = check_image_quality_bgr(
            image, bbox, blur_threshold=blur_threshold
        )
        if not is_good:
            raise ValueError(message)
    kps = _synthetic_kps_for_crop(width, height)
    embedding = _embed_from_det(image, bbox, kps, det_score=1.0)
    if embedding is None:
        return None
    return embedding.astype(np.float32).tolist(), bbox


def extract_face_features_from_crop(
    image_path: str,
    *,
    require_quality: bool = False,
    blur_threshold: Optional[float] = None,
) -> Optional[Tuple[List[float], np.ndarray]]:
    """Path-based wrapper for Edge crop identify (skip detector)."""
    image = _read_bgr(image_path)
    return extract_face_features_from_crop_bgr(
        image,
        require_quality=require_quality,
        blur_threshold=blur_threshold,
    )


def extract_face_features(
    image_path: str,
    *,
    require_quality: bool = True,
    blur_threshold: Optional[float] = None,
) -> Optional[Tuple[List[float], np.ndarray]]:
    """Detect the largest face and return (normed_embedding list, bbox)."""
    image = _read_bgr(image_path)
    return extract_face_features_bgr(
        image,
        require_quality=require_quality,
        blur_threshold=blur_threshold,
        fast_detect=False,
    )


def generate_face_encoding(
    image_path: str,
    *,
    require_quality: bool = True,
    blur_threshold: Optional[float] = None,
) -> Optional[List[float]]:
    """Quality-check + InsightFace 512-d embedding for enrollment."""
    try:
        result = extract_face_features(
            image_path,
            require_quality=require_quality,
            blur_threshold=blur_threshold,
        )
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
    Multi-frame liveness (same person + motion + passive anti-spoof) then return middle-frame embedding.
    Raises ValueError on failure.
    """
    if not image_paths:
        raise ValueError("No image frames provided for liveness check")

    frames = []
    for path in image_paths:
        bbox = detect_bbox(path)
        frames.append({"bbox": bbox, "embedding": None} if bbox is not None else None)

    is_live, reason = check_multi_frame_liveness(
        frames,
        same_person_max_distance=settings.LIVENESS_SAME_PERSON_MAX_DISTANCE,
        min_bbox_motion=settings.LIVENESS_MIN_BBOX_MOTION,
    )
    if not is_live:
        raise ValueError(f"Liveness check failed: {reason}")

    mid = image_paths[len(image_paths) // 2]
    if bool(getattr(settings, "FACE_ANTISPOOF_ENABLED", True)):
        mid_img = _read_bgr(mid)
        mid_bbox = frames[len(frames) // 2]["bbox"] if frames[len(frames) // 2] else None
        passed, spoof_msg = check_passive_antispoof_bgr(
            mid_img,
            mid_bbox,
            min_chroma_std=float(getattr(settings, "FACE_ANTISPOOF_MIN_CHROMA_STD", 2.0)),
            max_specular_ratio=float(getattr(settings, "FACE_ANTISPOOF_MAX_SPECULAR_RATIO", 0.22)),
        )
        if not passed:
            raise ValueError(spoof_msg)

    encoding = generate_face_encoding(mid)
    if encoding is None:
        raise ValueError("Could not generate face encoding from validation frame.")
    return encoding


def get_walkby_encoding_frames(frames: List[np.ndarray]) -> List[float]:
    """
    Walk-by mode on in-memory BGR frames (no temp files).
    Uses fast det@320 + recognition + passive single-frame anti-spoofing when enabled.
    """
    if not frames:
        raise ValueError("No image frames provided for walk-by check-in")

    candidates: List[List[float]] = []
    antispoof_enabled = bool(getattr(settings, "FACE_ANTISPOOF_ENABLED", True))
    min_chroma = float(getattr(settings, "FACE_ANTISPOOF_MIN_CHROMA_STD", 2.0))
    max_spec = float(getattr(settings, "FACE_ANTISPOOF_MAX_SPECULAR_RATIO", 0.22))

    for image in frames:
        result = extract_face_features_bgr(
            image,
            require_quality=False,
            fast_detect=True,
        )
        if result is None:
            continue
        encoding, bbox = result
        check_image_quality_bgr(image, bbox)
        if antispoof_enabled:
            passed, spoof_msg = check_passive_antispoof_bgr(
                image,
                bbox,
                min_chroma_std=min_chroma,
                max_specular_ratio=max_spec,
            )
            if not passed:
                raise ValueError(spoof_msg)
        candidates.append(encoding)

    if not candidates:
        raise ValueError("No face detected for walk-by check-in")

    if len(candidates) >= 2:
        anchor = candidates[0]
        for emb in candidates[1:]:
            dist = cosine_distance(anchor, emb)
            if dist > settings.LIVENESS_SAME_PERSON_MAX_DISTANCE:
                raise ValueError(
                    f"Face identity inconsistent across walk-by frames (distance={dist:.3f})."
                )

    return candidates[len(candidates) // 2]


def get_walkby_encoding(image_paths: List[str]) -> List[float]:
    """
    Walk-by mode: 1–2 frames, no head-motion liveness (uses passive anti-spoof).
    Path-based wrapper — loads frames then delegates to get_walkby_encoding_frames.
    """
    if not image_paths:
        raise ValueError("No image frames provided for walk-by check-in")
    frames = [_read_bgr(path) for path in image_paths]
    return get_walkby_encoding_frames(frames)
