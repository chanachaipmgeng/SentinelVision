"""InsightFace (buffalo_l) face embedding + multi-frame liveness."""

from __future__ import annotations

import threading
from typing import List, Optional, Tuple

import cv2
import numpy as np
from insightface.app import FaceAnalysis

from .image_quality import check_image_quality
from .liveness_detection import check_multi_frame_liveness, cosine_distance
from ..config.settings import settings

_face_apps: dict = {}
_face_app_lock = threading.Lock()
_thread_device = threading.local()


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
        print(f"Loading InsightFace buffalo_l device={device} providers={providers} ctx_id={ctx_id} det={size}", flush=True)
        try:
            app = FaceAnalysis(name="buffalo_l", providers=providers)
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


def decode_image_bytes(image_bytes: bytes) -> np.ndarray:
    """JPEG/PNG decode outside the GPU worker so inference slots stay busy."""
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Could not decode frame")
    return image


def detect_faces_bgr(image: np.ndarray) -> dict:
    """
    Fast detection-only pass for the kiosk stream (no embeddings).
    Uses FACE_DETECT_DET_SIZE (320) — not the 640 embed model.
    Returns frame size + face boxes [{x, y, width, height, score}].
    """
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
    return detect_faces_bgr(decode_image_bytes(image_bytes))


def extract_face_features(
    image_path: str,
    *,
    require_quality: bool = True,
    blur_threshold: Optional[float] = None,
) -> Optional[Tuple[List[float], np.ndarray]]:
    """
    Detect the largest face and return (normed_embedding list, bbox).
    bbox is [x1, y1, x2, y2].

    Quality (blur/brightness) is evaluated on the face crop so soft webcam
    backgrounds do not reject usable enroll frames.
    """
    image = _read_bgr(image_path)
    faces = get_face_app().get(image)
    face = _largest_face(faces)
    if face is None:
        return None

    if require_quality:
        is_good, message = check_image_quality(
            image_path, face.bbox, blur_threshold=blur_threshold
        )
        if not is_good:
            raise ValueError(message)

    embedding = face.normed_embedding
    if embedding is None:
        return None

    return embedding.astype(np.float32).tolist(), face.bbox.astype(np.float32)


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
    Multi-frame liveness (same person + motion) then return middle-frame embedding.
    Raises ValueError on failure.
    """
    if not image_paths:
        raise ValueError("No image frames provided for liveness check")

    frames = []
    for path in image_paths:
        bbox = detect_bbox(path)
        frames.append({"bbox": bbox, "embedding": None} if bbox is not None else None)

    # Motion uses boxes only. Same-person uses the first and middle embeddings.
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


def get_walkby_encoding(image_paths: List[str]) -> List[float]:
    """
    Walk-by mode: 1–2 frames, no head-motion liveness.
    One InsightFace pass per frame (require_quality=False). Soft quality
    check runs on the crop after inference — never a second GPU pass.
    """
    if not image_paths:
        raise ValueError("No image frames provided for walk-by check-in")

    candidates: List[List[float]] = []
    for path in image_paths:
        result = extract_face_features(path, require_quality=False)
        if result is None:
            continue
        encoding, bbox = result
        # Soft gate only — do not reject / re-infer when quality fails.
        check_image_quality(path, bbox)
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
