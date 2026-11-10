"""YOLOv8n person detector via onnxruntime (dedicated people lane — not InsightFace).

Expects a standard Ultralytics YOLOv8 ONNX export (input NCHW float32 0..1,
output [1, 84, N] or [1, N, 84] with COCO class scores; person = class 0).
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any, Optional

import numpy as np

from ..config.settings import settings

logger = logging.getLogger("dpu.people_yolo")

_PERSON_CLASS_ID = 0
_lock = threading.Lock()
_session = None
_input_name: Optional[str] = None
_output_names: list[str] = []
_load_error: Optional[str] = None


def model_path() -> Path:
    return Path(str(settings.PEOPLE_YOLO_ONNX_PATH or "models/yolov8n.onnx"))


def providers() -> list[str]:
    raw = str(settings.PEOPLE_YOLO_PROVIDERS or "CUDAExecutionProvider,CPUExecutionProvider")
    return [p.strip() for p in raw.split(",") if p.strip()]


def model_available() -> bool:
    return model_path().is_file()


def _letterbox(
    img: np.ndarray, new_shape: int
) -> tuple[np.ndarray, float, tuple[float, float]]:
    """Resize with aspect ratio preserved; pad to square. Returns (padded, ratio, (dw, dh))."""
    h, w = img.shape[:2]
    r = min(new_shape / h, new_shape / w)
    nh, nw = int(round(h * r)), int(round(w * r))
    import cv2

    resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)
    canvas = np.full((new_shape, new_shape, 3), 114, dtype=np.uint8)
    dw = (new_shape - nw) / 2.0
    dh = (new_shape - nh) / 2.0
    top, left = int(round(dh - 0.1)), int(round(dw - 0.1))
    canvas[top : top + nh, left : left + nw] = resized
    return canvas, r, (dw, dh)


def _nms(boxes: np.ndarray, scores: np.ndarray, iou_thr: float) -> list[int]:
    if boxes.size == 0:
        return []
    x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
    areas = (x2 - x1).clip(min=0) * (y2 - y1).clip(min=0)
    order = scores.argsort()[::-1]
    keep: list[int] = []
    while order.size > 0:
        i = int(order[0])
        keep.append(i)
        if order.size == 1:
            break
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        inter = (xx2 - xx1).clip(min=0) * (yy2 - yy1).clip(min=0)
        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-9)
        order = order[1:][iou <= iou_thr]
    return keep


def _ensure_session() -> bool:
    global _session, _input_name, _output_names, _load_error
    if _session is not None:
        return True
    if _load_error is not None:
        return False
    path = model_path()
    if not path.is_file():
        _load_error = f"missing_model:{path}"
        logger.warning("People YOLO model missing at %s — people job will no-op", path)
        return False
    with _lock:
        if _session is not None:
            return True
        try:
            import onnxruntime as ort

            avail = set(ort.get_available_providers())
            wanted = [p for p in providers() if p in avail]
            if not wanted:
                wanted = ["CPUExecutionProvider"]
            opts = ort.SessionOptions()
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            sess = ort.InferenceSession(str(path), sess_options=opts, providers=wanted)
            _session = sess
            _input_name = sess.get_inputs()[0].name
            _output_names = [o.name for o in sess.get_outputs()]
            logger.info(
                "People YOLO loaded path=%s providers=%s",
                path,
                sess.get_providers(),
            )
            return True
        except Exception as exc:  # noqa: BLE001
            _load_error = str(exc)
            logger.exception("Failed to load people YOLO ONNX: %s", exc)
            return False


def reset_session_for_tests() -> None:
    global _session, _input_name, _output_names, _load_error
    with _lock:
        _session = None
        _input_name = None
        _output_names = []
        _load_error = None


def detect_persons_bgr(
    frame_bgr: np.ndarray,
    *,
    confidence: Optional[float] = None,
    iou: Optional[float] = None,
) -> list[dict[str, Any]]:
    """Run YOLOv8n person detection on a BGR uint8 frame. Returns list of dets."""
    if frame_bgr is None or getattr(frame_bgr, "size", 0) == 0:
        return []
    if not _ensure_session():
        return []
    assert _session is not None and _input_name

    conf_thr = float(confidence if confidence is not None else settings.PEOPLE_YOLO_CONFIDENCE)
    iou_thr = float(iou if iou is not None else settings.PEOPLE_YOLO_IOU)
    size = int(settings.PEOPLE_YOLO_INPUT_SIZE or 640)

    img, ratio, (dw, dh) = _letterbox(frame_bgr, size)
    blob = img[:, :, ::-1].astype(np.float32) / 255.0  # BGR→RGB, 0..1
    blob = np.transpose(blob, (2, 0, 1))[None, ...]  # NCHW

    outputs = _session.run(_output_names, {_input_name: blob})
    pred = outputs[0]
    # Ultralytics export: (1, 84, N) or (1, N, 84)
    if pred.ndim == 3:
        pred = pred[0]
    if pred.shape[0] < pred.shape[1] and pred.shape[0] <= 84 + 10:
        pred = pred.T  # → (N, 84)

    if pred.shape[1] < 5:
        return []

    boxes_xywh = pred[:, :4]
    class_scores = pred[:, 4:]
    # Some exports put objectness at col 4 then 80 classes; YOLOv8 usually is 4+80.
    if class_scores.shape[1] >= 80:
        person_scores = class_scores[:, _PERSON_CLASS_ID]
    else:
        person_scores = class_scores.max(axis=1)

    mask = person_scores >= conf_thr
    boxes_xywh = boxes_xywh[mask]
    scores = person_scores[mask]
    if boxes_xywh.size == 0:
        return []

    # xywh (center) → xyxy in letterbox space, then undo pad/scale.
    cx, cy, w, h = boxes_xywh[:, 0], boxes_xywh[:, 1], boxes_xywh[:, 2], boxes_xywh[:, 3]
    x1 = cx - w / 2.0
    y1 = cy - h / 2.0
    x2 = cx + w / 2.0
    y2 = cy + h / 2.0
    boxes = np.stack([x1, y1, x2, y2], axis=1)
    keep = _nms(boxes, scores, iou_thr)
    boxes = boxes[keep]
    scores = scores[keep]

    orig_h, orig_w = frame_bgr.shape[:2]
    dets: list[dict[str, Any]] = []
    for box, score in zip(boxes, scores):
        bx1 = (float(box[0]) - dw) / ratio
        by1 = (float(box[1]) - dh) / ratio
        bx2 = (float(box[2]) - dw) / ratio
        by2 = (float(box[3]) - dh) / ratio
        bx1 = max(0.0, min(float(orig_w - 1), bx1))
        by1 = max(0.0, min(float(orig_h - 1), by1))
        bx2 = max(0.0, min(float(orig_w - 1), bx2))
        by2 = max(0.0, min(float(orig_h - 1), by2))
        if bx2 <= bx1 or by2 <= by1:
            continue
        dets.append(
            {
                "bbox": [bx1, by1, bx2, by2],
                "confidence": float(score),
                "label": "person",
            }
        )
    return dets


def detect_persons_jpeg(
    jpeg: bytes,
    *,
    confidence: Optional[float] = None,
    iou: Optional[float] = None,
) -> list[dict[str, Any]]:
    import cv2

    arr = np.frombuffer(jpeg, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        return []
    return detect_persons_bgr(frame, confidence=confidence, iou=iou)
