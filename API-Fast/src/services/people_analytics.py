"""Line crossing / zone count / loitering helpers (ported from AI_VISION_new custom_logic)."""
from __future__ import annotations

import time
from typing import Any, Optional


def bbox_center(bbox: list[float]) -> tuple[float, float]:
    if not bbox or len(bbox) < 4:
        return (0.0, 0.0)
    x1, y1, x2, y2 = (float(v) for v in bbox[:4])
    return ((x1 + x2) * 0.5, (y1 + y2) * 0.5)


def point_in_polygon(x: float, y: float, polygon: list[list[float]]) -> bool:
    inside = False
    n = len(polygon)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        xi, yi = float(polygon[i][0]), float(polygon[i][1])
        xj, yj = float(polygon[j][0]), float(polygon[j][1])
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-9) + xi):
            inside = not inside
        j = i
    return inside


def segments_cross(
    a1: tuple[float, float],
    a2: tuple[float, float],
    b1: tuple[float, float],
    b2: tuple[float, float],
) -> bool:
    def ccw(p, q, r) -> float:
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    d1 = ccw(b1, b2, a1)
    d2 = ccw(b1, b2, a2)
    d3 = ccw(a1, a2, b1)
    d4 = ccw(a1, a2, b2)
    return (d1 * d2 < 0) and (d3 * d4 < 0)


def track_key(det: dict[str, Any]) -> str:
    tid = det.get("track_id")
    if tid is not None:
        return f"t:{tid}"
    cx, cy = bbox_center(det.get("bbox") or [])
    return f"l:{det.get('label', '?')}:{int(cx) // 32}:{int(cy) // 32}"


def filter_detections_by_roi(
    detections: list[dict[str, Any]],
    ai_config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Keep detections whose centroid falls inside roi_polygon or roi_rect."""
    poly = ai_config.get("roi_polygon") or ai_config.get("roiPolygon")
    rect = ai_config.get("roi_rect") or ai_config.get("roiRect")
    if not poly and not rect:
        return detections
    out: list[dict[str, Any]] = []
    for det in detections:
        cx, cy = bbox_center(det.get("bbox") or [])
        if poly and len(poly) >= 3:
            if point_in_polygon(cx, cy, poly):
                out.append(det)
            continue
        if rect and len(rect) >= 4:
            x1, y1, x2, y2 = (float(v) for v in rect[:4])
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                out.append(det)
    return out


def line_crossing(
    detections: list[dict[str, Any]],
    state: dict[str, Any],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    line = config.get("line") or []
    if len(line) < 2:
        return []
    last: dict[str, tuple[float, float]] = state.setdefault("last_centers", {})
    triggered: list[dict[str, Any]] = []
    for det in detections:
        key = track_key(det)
        cur = bbox_center(det.get("bbox") or [])
        prev = last.get(key)
        last[key] = cur
        if prev is None:
            continue
        for i in range(len(line) - 1):
            a = (float(line[i][0]), float(line[i][1]))
            b = (float(line[i + 1][0]), float(line[i + 1][1]))
            if segments_cross(prev, cur, a, b):
                # Direction: sign of cross product relative to line → in vs out.
                lx, ly = b[0] - a[0], b[1] - a[1]
                mx, my = cur[0] - prev[0], cur[1] - prev[1]
                cross = lx * my - ly * mx
                direction = "in" if cross >= 0 else "out"
                triggered.append(
                    {
                        **det,
                        "label": "line_crossing",
                        "algorithm_code": "line_crossing",
                        "direction": direction,
                    }
                )
                break
    return triggered


def zone_count(
    detections: list[dict[str, Any]],
    config: dict[str, Any],
) -> dict[str, Any]:
    polygon = (
        config.get("zone_polygon")
        or config.get("zonePolygon")
        or config.get("polygon")
        or []
    )
    if len(polygon) < 3:
        return {"count": 0, "inside": [], "crowd": False}
    min_count = int(config.get("crowd_min_count") or config.get("min_count") or 5)
    inside: list[dict[str, Any]] = []
    for det in detections:
        if str(det.get("label") or "person").lower() not in ("person", "line_crossing"):
            # Raw person tracks only.
            if str(det.get("label") or "").lower() != "person":
                continue
        cx, cy = bbox_center(det.get("bbox") or [])
        if point_in_polygon(cx, cy, polygon):
            inside.append(det)
    crowd = len(inside) >= min_count
    return {"count": len(inside), "inside": inside, "crowd": crowd, "min_count": min_count}


def loitering(
    detections: list[dict[str, Any]],
    state: dict[str, Any],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    polygon = (
        config.get("loiter_polygon")
        or config.get("loiterPolygon")
        or config.get("polygon")
        or []
    )
    if len(polygon) < 3:
        return []
    min_seconds = float(config.get("loiter_min_seconds") or config.get("min_seconds") or 30)
    entered_at: dict[str, float] = state.setdefault("loiter_entered_at", {})
    alerted: set[str] = state.setdefault("loiter_alerted", set())
    triggered: list[dict[str, Any]] = []
    now = time.monotonic()
    seen: set[str] = set()
    for det in detections:
        if str(det.get("label") or "person").lower() != "person":
            continue
        key = track_key(det)
        seen.add(key)
        cx, cy = bbox_center(det.get("bbox") or [])
        if not point_in_polygon(cx, cy, polygon):
            entered_at.pop(key, None)
            alerted.discard(key)
            continue
        start = entered_at.get(key)
        if start is None:
            entered_at[key] = now
            continue
        dwell = now - start
        if dwell >= min_seconds and key not in alerted:
            alerted.add(key)
            triggered.append(
                {
                    **det,
                    "label": "loitering",
                    "algorithm_code": "loitering",
                    "dwell_seconds": dwell,
                }
            )
    for stale in list(entered_at.keys()):
        if stale not in seen:
            entered_at.pop(stale, None)
            alerted.discard(stale)
    return triggered


def normalize_ai_config(raw: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Canonical people ai_config; peopleEnabled stays false until ROI is present."""
    cfg = dict(raw or {}) if isinstance(raw, dict) else {}
    has_roi = bool(
        (cfg.get("roi_polygon") or cfg.get("roiPolygon") or [])
        or (cfg.get("roi_rect") or cfg.get("roiRect") or [])
        or (cfg.get("line") or [])
        or (cfg.get("zone_polygon") or cfg.get("zonePolygon") or [])
        or (cfg.get("loiter_polygon") or cfg.get("loiterPolygon") or [])
    )
    enabled = bool(cfg.get("peopleEnabled") or cfg.get("people_enabled"))
    # Hard gate: never run people without ROI geometry even if flag flipped.
    if enabled and not has_roi:
        enabled = False
    modes = cfg.get("modes") or []
    if not modes:
        modes = []
        if cfg.get("line"):
            modes.append("line_crossing")
        if cfg.get("zone_polygon") or cfg.get("zonePolygon"):
            modes.append("zone_count")
        if cfg.get("loiter_polygon") or cfg.get("loiterPolygon"):
            modes.append("loitering")
    role = str(cfg.get("presenceRole") or cfg.get("presence_role") or "LOCATE").strip().upper()
    if role not in ("LOCATE", "BOOTH", "OT_AREA"):
        role = "LOCATE"
    event_raw = cfg.get("eventId") or cfg.get("event_id")
    event_id = str(event_raw).strip() if event_raw else None
    if role == "BOOTH" and not event_id:
        role = "LOCATE"

    return {
        **cfg,
        "peopleEnabled": enabled,
        "modes": list(modes),
        "hasRoi": has_roi,
        "confidence": float(cfg.get("confidence") or 0.4),
        "crowd_min_count": int(cfg.get("crowd_min_count") or cfg.get("min_count") or 5),
        "loiter_min_seconds": float(
            cfg.get("loiter_min_seconds") or cfg.get("min_seconds") or 30
        ),
        "presenceRole": role,
        "eventId": event_id,
    }
