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

_face_app: Optional[FaceAnalysis] = None
_face_app_lock = threading.Lock()
_face_app_device: Optional[str] = None


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


def get_face_app() -> FaceAnalysis:
    """Lazy singleton FaceAnalysis (CUDA when available, else CPU)."""
    global _face_app, _face_app_device
    if _face_app is not None:
        return _face_app
    with _face_app_lock:
        if _face_app is None:
            device = (settings.FACE_DEVICE or "cuda:0").strip() or "cuda:0"
            providers, ctx_id = _resolve_providers_and_ctx(device)
            print(f"Loading InsightFace buffalo_l providers={providers} ctx_id={ctx_id}", flush=True)
            try:
                app = FaceAnalysis(name="buffalo_l", providers=providers)
                app.prepare(ctx_id=ctx_id, det_size=(640, 640))
                _face_app_device = device if ctx_id >= 0 else "cpu"
            except Exception as exc:
                if ctx_id < 0:
                    raise
                print(
                    f"CUDA InsightFace init failed ({exc}); falling back to CPU.",
                    flush=True,
                )
                app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
                app.prepare(ctx_id=-1, det_size=(640, 640))
                _face_app_device = "cpu"
            _face_app = app
            print(f"InsightFace ready on {_face_app_device}", flush=True)
    return _face_app


def get_face_device() -> str:
    get_face_app()
    return _face_app_device or "cpu"


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


def detect_faces_bytes(image_bytes: bytes) -> dict:
    """
    Fast detection-only pass for the kiosk stream (no embeddings).
    Returns frame size + face boxes [{x, y, width, height, score}].
    """
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Could not decode frame")
    height, width = image.shape[:2]

    app = get_face_app()
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


def extract_face_features(
    image_path: str, *, require_quality: bool = True
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
        is_good, message = check_image_quality(image_path, face.bbox)
        if not is_good:
            raise ValueError(message)

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


def get_walkby_encoding(image_paths: List[str]) -> List[float]:
    """
    Walk-by mode: 1–2 frames, no head-motion liveness.
    - Detect face on each frame
    - If 2+ frames: require same-person embedding consistency
    - Prefer a quality-checked embedding; fall back without quality if needed
    """
    if not image_paths:
        raise ValueError("No image frames provided for walk-by check-in")

    candidates: List[List[float]] = []
    for path in image_paths:
        encoding = None
        try:
            encoding = generate_face_encoding(path)
        except ValueError:
            encoding = None
        if encoding is None:
            result = extract_face_features(path, require_quality=False)
            if result is not None:
                encoding = result[0]
        if encoding is not None:
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
