"""Phase 6D people counting worker — dedicated YOLO lane (not InsightFace queue).

Flow per tick:
1. Scrape API /metrics for kiosk pending; pause when threshold hit.
2. Select active cameras with ``ai_config.peopleEnabled`` + ROI.
3. Snapshot → YOLOv8n ONNX (own session) → IoU/centroid tracker.
4. line_crossing / zone_count / loitering → buckets + CROWD / LOITERING incidents.
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.database import async_session
from ..config.settings import settings
from ..models.camera import Camera
from ..models.people_count_bucket import PeopleCountBucket
from ..services import people_analytics as analytics
from ..services.camera_service import _grab_snapshot_bgr, effective_stream_url, serialize_camera
from ..services.mediamtx_service import path_name_for_camera
from ..services.people_tracker import get_tracker
from ..services.people_yolo import detect_persons_jpeg, model_available

logger = logging.getLogger("dpu.people_count")

# Per-camera custom-logic state (line centers / loiter timers).
_LOGIC_STATE: dict[str, dict[str, Any]] = {}
_METRIC_RE = re.compile(
    r'^dpu_face_gpu_queue_pending\{kind="([^"]+)"\}\s+(\d+(?:\.\d+)?)',
    re.MULTILINE,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _bucket_start(ts: datetime, *, seconds: Optional[int] = None) -> datetime:
    width = int(seconds if seconds is not None else settings.PEOPLE_BUCKET_SECONDS or 60)
    width = max(10, width)
    epoch = int(ts.timestamp())
    aligned = epoch - (epoch % width)
    return datetime.fromtimestamp(aligned, tz=timezone.utc)


def parse_kiosk_pending_from_metrics(text: str) -> dict[str, int]:
    """Parse Prometheus text for face GPU queue pending by kind."""
    out: dict[str, int] = {}
    for m in _METRIC_RE.finditer(text or ""):
        out[m.group(1)] = int(float(m.group(2)))
    return out


async def scrape_kiosk_queue_stats() -> dict[str, Any]:
    """HTTP scrape API /metrics (no JWT). Sums checkin+identify across replicas."""
    urls = [
        u.strip()
        for u in str(settings.WORKER_PEOPLE_KIOSK_METRICS_URLS or "").split(",")
        if u.strip()
    ]
    pending_by_kind: dict[str, int] = {}
    errors: list[str] = []
    async with httpx.AsyncClient(timeout=3.0) as client:
        for url in urls:
            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    errors.append(f"{url}:{resp.status_code}")
                    continue
                part = parse_kiosk_pending_from_metrics(resp.text)
                for k, v in part.items():
                    pending_by_kind[k] = pending_by_kind.get(k, 0) + v
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{url}:{exc}")
    kiosk = int(pending_by_kind.get("checkin") or 0) + int(pending_by_kind.get("identify") or 0)
    total = sum(pending_by_kind.values())
    return {
        "pendingByKind": pending_by_kind,
        "kioskPending": kiosk,
        "pending": total,
        "errors": errors,
    }


def should_pause_for_kiosk(stats: dict[str, Any]) -> bool:
    kiosk = int(stats.get("kioskPending") or 0)
    if kiosk >= int(settings.WORKER_PEOPLE_PAUSE_WHEN_KIOSK_PENDING):
        return True
    if int(stats.get("pending") or 0) >= int(settings.WORKER_PEOPLE_MAX_QUEUE_PENDING):
        return True
    return False


def _frame_source_urls(cam: Camera) -> list[str]:
    urls: list[str] = []
    direct = effective_stream_url(cam)
    if direct:
        urls.append(direct)
    base = (settings.MEDIAMTX_RTSP_PUBLISH_URL or "").rstrip("/")
    if base:
        mtx = f"{base}/{path_name_for_camera(cam.cameraId)}"
        if mtx not in urls:
            urls.append(mtx)
    return urls


async def _grab_frame_jpeg(cam: Camera) -> bytes:
    timeout = float(settings.WORKER_PEOPLE_SNAPSHOT_TIMEOUT_SECONDS)
    last_err: Optional[Exception] = None
    for url in _frame_source_urls(cam):
        try:
            return await asyncio.to_thread(_grab_snapshot_bgr, url, timeout)
        except Exception as exc:  # noqa: BLE001
            last_err = exc
    raise RuntimeError(f"snapshot_failed: {last_err}")


def _logic_state(camera_id: UUID) -> dict[str, Any]:
    key = str(camera_id)
    st = _LOGIC_STATE.get(key)
    if st is None:
        st = {}
        _LOGIC_STATE[key] = st
    return st


async def _upsert_bucket(
    db: AsyncSession,
    *,
    company_id: UUID,
    camera_id: UUID,
    start: datetime,
    in_delta: int = 0,
    out_delta: int = 0,
    crossing_delta: int = 0,
    zone_occupancy: Optional[int] = None,
    detections: int = 0,
) -> PeopleCountBucket:
    row = (
        await db.execute(
            select(PeopleCountBucket).where(
                PeopleCountBucket.cameraId == camera_id,
                PeopleCountBucket.bucketStart == start,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        row = PeopleCountBucket(
            bucketId=uuid4(),
            companyId=company_id,
            cameraId=camera_id,
            bucketStart=start,
            inCount=0,
            outCount=0,
            zoneOccupancy=0,
            crossingCount=0,
            detections=0,
        )
        db.add(row)
    row.inCount = int(row.inCount or 0) + int(in_delta)
    row.outCount = int(row.outCount or 0) + int(out_delta)
    row.crossingCount = int(row.crossingCount or 0) + int(crossing_delta)
    row.detections = int(row.detections or 0) + int(detections)
    if zone_occupancy is not None:
        row.zoneOccupancy = max(int(row.zoneOccupancy or 0), int(zone_occupancy))
    return row


async def _emit_crowd(
    db: AsyncSession,
    *,
    cam: Camera,
    count: int,
    min_count: int,
    snapshot_url: Optional[str] = None,
) -> None:
    from src.services.sentinel_incident_service import record_incident

    await record_incident(
        db,
        company_id=cam.companyId,
        event_type="CROWD",
        severity="WARNING",
        subject_name=f"Crowd {count} (min {min_count})",
        zone_id=cam.zoneId,
        camera_id=cam.cameraId,
        snapshot_url=snapshot_url,
        action_taken=f"zone_count={count}",
        confidence_percent=100.0,
        commit=False,
        schedule_clip=True,
    )


async def _emit_loiter(
    db: AsyncSession,
    *,
    cam: Camera,
    det: dict[str, Any],
    snapshot_url: Optional[str] = None,
) -> None:
    from src.services.sentinel_incident_service import record_incident

    dwell = float(det.get("dwell_seconds") or 0)
    await record_incident(
        db,
        company_id=cam.companyId,
        event_type="LOITERING",
        severity="WARNING",
        subject_name=f"Loitering track {det.get('track_id')}",
        zone_id=cam.zoneId,
        camera_id=cam.cameraId,
        snapshot_url=snapshot_url,
        action_taken=f"dwell_seconds={dwell:.1f}",
        confidence_percent=float(det.get("confidence") or 0) * 100.0,
        commit=False,
        schedule_clip=True,
    )


async def analyze_camera(db: AsyncSession, cam: Camera) -> dict[str, Any]:
    cfg = analytics.normalize_ai_config(
        cam.aiConfig if isinstance(cam.aiConfig, dict) else None
    )
    if not cfg.get("peopleEnabled"):
        return {"skipped": "people_disabled"}

    jpeg = await _grab_frame_jpeg(cam)
    dets = await asyncio.to_thread(
        detect_persons_jpeg,
        jpeg,
        confidence=float(cfg.get("confidence") or settings.PEOPLE_YOLO_CONFIDENCE),
    )
    dets = analytics.filter_detections_by_roi(dets, cfg)
    tracker = get_tracker(str(cam.cameraId))
    tracked = tracker.update(dets)

    state = _logic_state(cam.cameraId)
    modes = set(str(m).lower() for m in (cfg.get("modes") or []))
    in_delta = out_delta = crossing_delta = 0
    zone_occ: Optional[int] = None
    incidents: list[str] = []

    if "line_crossing" in modes and (cfg.get("line") or []):
        crosses = analytics.line_crossing(tracked, state, cfg)
        for c in crosses:
            crossing_delta += 1
            if c.get("direction") == "out":
                out_delta += 1
            else:
                in_delta += 1

    if "zone_count" in modes:
        z = analytics.zone_count(tracked, cfg)
        zone_occ = int(z.get("count") or 0)
        if z.get("crowd"):
            await _emit_crowd(
                db,
                cam=cam,
                count=zone_occ,
                min_count=int(z.get("min_count") or cfg.get("crowd_min_count") or 5),
            )
            incidents.append("CROWD")

    if "loitering" in modes:
        loiters = analytics.loitering(tracked, state, cfg)
        for det in loiters:
            await _emit_loiter(db, cam=cam, det=det)
            incidents.append("LOITERING")

    start = _bucket_start(_now())
    await _upsert_bucket(
        db,
        company_id=cam.companyId,
        camera_id=cam.cameraId,
        start=start,
        in_delta=in_delta,
        out_delta=out_delta,
        crossing_delta=crossing_delta,
        zone_occupancy=zone_occ,
        detections=len(tracked),
    )
    cam.lastAnalyzedAt = _now()  # reuse stamp so ops can see activity
    await db.commit()
    return {
        "cameraId": str(cam.cameraId),
        "detections": len(tracked),
        "in": in_delta,
        "out": out_delta,
        "crossings": crossing_delta,
        "zoneOccupancy": zone_occ,
        "incidents": incidents,
    }


async def due_people_cameras(
    db: AsyncSession, *, limit: int = 20
) -> list[Camera]:
    """Cameras with peopleEnabled + ROI; due by lastAnalyzedAt interval."""
    interval = timedelta(seconds=max(5, int(settings.WORKER_PEOPLE_CAMERA_INTERVAL_SECONDS)))
    cutoff = _now() - interval
    rows = (
        await db.execute(
            select(Camera)
            .where(
                Camera.deletedAt.is_(None),
                Camera.isActive.is_(True),
                Camera.aiConfig.isnot(None),
            )
            .order_by(Camera.lastAnalyzedAt.asc().nullsfirst())
            .limit(limit * 3)
        )
    ).scalars().all()
    due: list[Camera] = []
    for cam in rows:
        cfg = analytics.normalize_ai_config(
            cam.aiConfig if isinstance(cam.aiConfig, dict) else None
        )
        if not cfg.get("peopleEnabled"):
            continue
        if cam.lastAnalyzedAt is not None and cam.lastAnalyzedAt > cutoff:
            continue
        due.append(cam)
        if len(due) >= limit:
            break
    return due


async def run_people_count_tick(
    *, stop_event: Optional[asyncio.Event] = None
) -> dict[str, Any]:
    if not model_available():
        return {"skipped": "model_missing", "path": str(settings.PEOPLE_YOLO_ONNX_PATH)}

    stats = await scrape_kiosk_queue_stats()
    if should_pause_for_kiosk(stats):
        logger.info(
            "people tick paused for kiosk pending=%s total=%s",
            stats.get("kioskPending"),
            stats.get("pending"),
        )
        return {"paused": True, "kiosk": stats}

    max_conc = max(1, int(settings.WORKER_PEOPLE_MAX_CONCURRENT))
    sem = asyncio.Semaphore(max_conc)
    results: list[dict[str, Any]] = []

    async with async_session() as db:
        cameras = await due_people_cameras(db, limit=max_conc * 4)

    async def _one(cam_id: UUID) -> dict[str, Any]:
        async with sem:
            if stop_event is not None and stop_event.is_set():
                return {"skipped": "stopping"}
            async with async_session() as db:
                cam = await db.get(Camera, cam_id)
                if cam is None or cam.deletedAt is not None:
                    return {"skipped": "missing"}
                try:
                    return await analyze_camera(db, cam)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("people analyze failed cam=%s: %s", cam_id, exc)
                    return {"cameraId": str(cam_id), "error": str(exc)}

    tasks = [asyncio.create_task(_one(c.cameraId)) for c in cameras]
    if tasks:
        results = list(await asyncio.gather(*tasks))
    return {
        "cameras": len(cameras),
        "results": results,
        "kiosk": {"kioskPending": stats.get("kioskPending"), "pending": stats.get("pending")},
    }


# ---- HTTP helpers (buckets + ai_config + CSV) ---------------------------------


def serialize_bucket(row: PeopleCountBucket) -> dict[str, Any]:
    return {
        "bucketId": str(row.bucketId),
        "companyId": str(row.companyId),
        "cameraId": str(row.cameraId),
        "bucketStart": row.bucketStart,
        "inCount": int(row.inCount or 0),
        "outCount": int(row.outCount or 0),
        "zoneOccupancy": int(row.zoneOccupancy or 0),
        "crossingCount": int(row.crossingCount or 0),
        "detections": int(row.detections or 0),
        "createdAt": row.createdAt,
        "updatedAt": row.updatedAt,
    }


async def list_buckets(
    db: AsyncSession,
    company_id: UUID,
    *,
    camera_id: Optional[UUID] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    q = select(PeopleCountBucket).where(PeopleCountBucket.companyId == company_id)
    if camera_id is not None:
        q = q.where(PeopleCountBucket.cameraId == camera_id)
    if start is not None:
        q = q.where(PeopleCountBucket.bucketStart >= start)
    if end is not None:
        q = q.where(PeopleCountBucket.bucketStart < end)
    q = q.order_by(PeopleCountBucket.bucketStart.desc()).limit(max(1, min(limit, 5000)))
    rows = (await db.execute(q)).scalars().all()
    return [serialize_bucket(r) for r in rows]


async def people_metrics_summary(
    db: AsyncSession,
    company_id: UUID,
    *,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> dict[str, Any]:
    buckets = await list_buckets(db, company_id, start=start, end=end, limit=5000)
    total_in = sum(b["inCount"] for b in buckets)
    total_out = sum(b["outCount"] for b in buckets)
    peak_zone = max((b["zoneOccupancy"] for b in buckets), default=0)
    by_camera: dict[str, dict[str, Any]] = {}
    for b in buckets:
        cid = b["cameraId"]
        slot = by_camera.setdefault(
            cid,
            {"cameraId": cid, "inCount": 0, "outCount": 0, "peakZone": 0, "crossings": 0},
        )
        slot["inCount"] += b["inCount"]
        slot["outCount"] += b["outCount"]
        slot["crossings"] += b["crossingCount"]
        slot["peakZone"] = max(slot["peakZone"], b["zoneOccupancy"])
    return {
        "companyId": str(company_id),
        "start": start,
        "end": end,
        "totals": {
            "inCount": total_in,
            "outCount": total_out,
            "net": total_in - total_out,
            "peakZoneOccupancy": peak_zone,
            "bucketCount": len(buckets),
        },
        "byCamera": list(by_camera.values()),
        "buckets": buckets[:200],
    }


def parse_camera_csv(text: str) -> list[dict[str, Any]]:
    """Parse camera CSV: name, stream_url|rtsp_url|streamUrl, protocol (optional)."""
    import csv
    import io

    sample = (text or "").lstrip("\ufeff")
    reader = csv.reader(io.StringIO(sample))
    rows = [r for r in reader if any(str(c).strip() for c in r)]
    if not rows:
        return []

    header = [str(c).strip().lower() for c in rows[0]]
    name_keys = {"name", "camera", "camera_name", "ชื่อ"}
    url_keys = {"stream_url", "streamurl", "rtsp_url", "rtspurl", "url", "stream"}
    proto_keys = {"protocol", "proto", "โปรโตคอล"}
    looks_header = any(h in name_keys or h in url_keys for h in header)
    name_idx, url_idx, proto_idx = 0, 1, 2
    if looks_header:
        for i, h in enumerate(header):
            if h in name_keys:
                name_idx = i
            if h in url_keys:
                url_idx = i
            if h in proto_keys:
                proto_idx = i
        data_rows = rows[1:]
    else:
        data_rows = rows

    out: list[dict[str, Any]] = []
    for row in data_rows:
        if len(row) <= max(name_idx, url_idx):
            continue
        name = str(row[name_idx]).strip()
        url = str(row[url_idx]).strip()
        if not name or not url:
            continue
        proto = "rtsp"
        if len(row) > proto_idx and str(row[proto_idx]).strip():
            proto = str(row[proto_idx]).strip().lower()
        out.append({"name": name[:160], "streamUrl": url, "protocol": proto})
    return out


async def import_cameras_csv(
    db: AsyncSession, company_id: UUID, text: str
) -> dict[str, Any]:
    from ..services import camera_service

    items = parse_camera_csv(text)
    created: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for i, item in enumerate(items):
        try:
            row = await camera_service.create_camera(db, company_id, item)
            created.append({"index": i, "cameraId": row.get("cameraId"), "name": row.get("name")})
        except Exception as exc:  # noqa: BLE001
            errors.append({"index": i, "name": item.get("name"), "error": str(exc)})
    return {"created": len(created), "errors": errors, "items": created}


async def update_camera_ai_config(
    db: AsyncSession, company_id: UUID, camera_id: UUID, body: dict[str, Any]
) -> dict[str, Any]:
    from ..services.camera_service import get_company_camera

    cam = await get_company_camera(db, company_id, camera_id)
    current = dict(cam.aiConfig) if isinstance(cam.aiConfig, dict) else {}
    # Accept either full aiConfig object or flat patch.
    patch = body.get("aiConfig") if isinstance(body.get("aiConfig"), dict) else body
    if not isinstance(patch, dict):
        patch = {}
    merged = {**current, **patch}
    # Drop non-config bookkeeping keys from request body.
    for k in ("cameraId", "companyId", "aiConfig"):
        merged.pop(k, None)
    normalized = analytics.normalize_ai_config(merged)
    cam.aiConfig = normalized
    await db.commit()
    await db.refresh(cam)
    out = serialize_camera(cam)
    return out
