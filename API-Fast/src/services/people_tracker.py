"""Lightweight IoU + centroid tracker for person detections (Phase 6D).

No DeepSORT / ByteTrack dependency — keeps the people lane independent of
InsightFace and avoids pulling torch/ultralytics into the API image.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


def _iou(a: list[float], b: list[float]) -> float:
    ax1, ay1, ax2, ay2 = (float(v) for v in a[:4])
    bx1, by1, bx2, by2 = (float(v) for v in b[:4])
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _centroid(bbox: list[float]) -> tuple[float, float]:
    x1, y1, x2, y2 = (float(v) for v in bbox[:4])
    return ((x1 + x2) * 0.5, (y1 + y2) * 0.5)


def _centroid_dist(a: list[float], b: list[float]) -> float:
    ax, ay = _centroid(a)
    bx, by = _centroid(b)
    return ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5


@dataclass
class Track:
    track_id: int
    bbox: list[float]
    label: str = "person"
    confidence: float = 0.0
    hits: int = 1
    age: int = 1
    time_since_update: int = 0
    centroid_history: list[tuple[float, float]] = field(default_factory=list)

    def as_det(self) -> dict[str, Any]:
        return {
            "bbox": list(self.bbox),
            "label": self.label,
            "confidence": self.confidence,
            "track_id": self.track_id,
        }


class CentroidIoUTracker:
    """Greedy IoU-first matcher with centroid distance fallback."""

    def __init__(
        self,
        *,
        iou_threshold: float = 0.3,
        max_centroid_dist: float = 80.0,
        max_age: int = 15,
    ) -> None:
        self.iou_threshold = float(iou_threshold)
        self.max_centroid_dist = float(max_centroid_dist)
        self.max_age = int(max_age)
        self._next_id = 1
        self._tracks: dict[int, Track] = {}

    def reset(self) -> None:
        self._tracks.clear()
        self._next_id = 1

    def update(self, detections: list[dict[str, Any]]) -> list[dict[str, Any]]:
        dets = [d for d in detections if d.get("bbox") and len(d["bbox"]) >= 4]
        for t in self._tracks.values():
            t.time_since_update += 1
            t.age += 1

        unmatched_dets = set(range(len(dets)))
        unmatched_tracks = set(self._tracks.keys())
        pairs: list[tuple[float, int, int]] = []  # score, det_i, track_id

        for di, det in enumerate(dets):
            for tid in list(unmatched_tracks):
                track = self._tracks[tid]
                iou = _iou(det["bbox"], track.bbox)
                if iou >= self.iou_threshold:
                    pairs.append((iou, di, tid))
                else:
                    dist = _centroid_dist(det["bbox"], track.bbox)
                    if dist <= self.max_centroid_dist:
                        # Lower is better for distance — invert into a weak score.
                        pairs.append((0.15 + max(0.0, 1.0 - dist / self.max_centroid_dist) * 0.14, di, tid))

        pairs.sort(key=lambda x: x[0], reverse=True)
        used_dets: set[int] = set()
        used_tracks: set[int] = set()
        for _score, di, tid in pairs:
            if di in used_dets or tid in used_tracks:
                continue
            det = dets[di]
            track = self._tracks[tid]
            track.bbox = list(det["bbox"][:4])
            track.confidence = float(det.get("confidence") or 0.0)
            track.label = str(det.get("label") or "person")
            track.hits += 1
            track.time_since_update = 0
            cx, cy = _centroid(track.bbox)
            track.centroid_history.append((cx, cy))
            if len(track.centroid_history) > 32:
                track.centroid_history = track.centroid_history[-32:]
            used_dets.add(di)
            used_tracks.add(tid)
            unmatched_dets.discard(di)
            unmatched_tracks.discard(tid)

        for di in unmatched_dets:
            det = dets[di]
            tid = self._next_id
            self._next_id += 1
            cx, cy = _centroid(det["bbox"])
            self._tracks[tid] = Track(
                track_id=tid,
                bbox=list(det["bbox"][:4]),
                label=str(det.get("label") or "person"),
                confidence=float(det.get("confidence") or 0.0),
                centroid_history=[(cx, cy)],
            )

        stale = [tid for tid, t in self._tracks.items() if t.time_since_update > self.max_age]
        for tid in stale:
            self._tracks.pop(tid, None)

        return [t.as_det() for t in self._tracks.values() if t.time_since_update == 0]


# Per-camera tracker instances (worker process memory).
_TRACKERS: dict[str, CentroidIoUTracker] = {}


def get_tracker(camera_id: str) -> CentroidIoUTracker:
    tr = _TRACKERS.get(camera_id)
    if tr is None:
        tr = CentroidIoUTracker()
        _TRACKERS[camera_id] = tr
    return tr


def clear_tracker(camera_id: Optional[str] = None) -> None:
    if camera_id is None:
        _TRACKERS.clear()
    else:
        _TRACKERS.pop(str(camera_id), None)
