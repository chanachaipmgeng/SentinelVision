"""Phase 4A: CCTV frame grab → InsightFace GPU queue → incident / attendance.

Reuses the existing face stack (``face_gpu_queue`` + identify / Decision Engine).
CCTV jobs use kind ``cctv`` (lowest priority) and throttle so the kiosk lane stays healthy.
"""
from __future__ import annotations

import asyncio
import logging
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.database import async_session
from ..config.settings import settings
from ..models.camera import Camera
from ..models.company_location import CompanyLocation
from ..services.camera_service import _grab_snapshot_bgr, effective_stream_url
from ..services.company_module_service import (
    VALID_STATION_MODES,
    get_company_module_config,
)
from ..services.mediamtx_service import path_name_for_camera
from ..utils.face_gpu_queue import face_gpu_queue_stats, run_on_face_gpu, start_face_gpu_workers

logger = logging.getLogger("dpu.cctv_analysis")

ATTENDANCE_LIKE_MODES = frozenset({"ATTENDANCE", "UNIFIED_HYBRID"})

# Mirror F3 ``should_run_sentinel_search`` (face_controller) so CCTV can gate without
# importing the full face HTTP stack at module load.
_SENTINEL_SEARCH_MODES = frozenset(
    {
        "WATCHLIST",
        "WATCHLIST_MONITOR",
        "ACCESS_CONTROL",
        "VISITOR",
        "VISITOR_CHECKIN",
        "EVENTS",
        "EVENT_CHECKIN",
        "COMMAND",
    }
)


def should_run_sentinel_search(station_mode: Optional[str]) -> bool:
    """F3 gate: True when CCTV should run the sentinel Decision Engine path."""
    mode = str(station_mode or "").strip().upper()
    if not mode:
        return False
    return mode in _SENTINEL_SEARCH_MODES


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _cctv_enabled_for_company(module_cfg: dict) -> bool:
    enabled = module_cfg.get("enabledModules") or []
    return "CCTV" in {str(m).strip().upper() for m in enabled}


async def ensure_face_gpu_for_cctv() -> None:
    """Start the local face GPU queue when the worker process hosts the CCTV job."""
    stats = face_gpu_queue_stats()
    if stats.get("started"):
        return
    devices = settings.face_device_list() or ["cpu"]
    await start_face_gpu_workers(
        workers=max(1, int(settings.FACE_GPU_WORKERS)),
        queue_size=int(settings.FACE_GPU_QUEUE_SIZE),
        devices=devices,
    )


def _kiosk_pending(stats: dict) -> int:
    by_kind = stats.get("pendingByKind") or {}
    return int(by_kind.get("checkin") or 0) + int(by_kind.get("identify") or 0)


def _should_pause_for_kiosk(stats: dict) -> bool:
    if _kiosk_pending(stats) >= int(settings.WORKER_CCTV_PAUSE_WHEN_KIOSK_PENDING):
        return True
    if int(stats.get("pending") or 0) >= int(settings.WORKER_CCTV_MAX_QUEUE_PENDING):
        return True
    return False


def _frame_source_urls(cam: Camera) -> list[str]:
    """Prefer camera streamUrl; fall back to MediaMTX publish path."""
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
    timeout = float(settings.WORKER_CCTV_SNAPSHOT_TIMEOUT_SECONDS)
    last_err: Optional[Exception] = None
    for url in _frame_source_urls(cam):
        try:
            return await asyncio.to_thread(_grab_snapshot_bgr, url, timeout)
        except Exception as exc:  # noqa: BLE001 — try next source
            last_err = exc
            logger.debug("CCTV snapshot failed cam=%s url=%s: %s", cam.cameraId, url[:80], exc)
    raise RuntimeError(f"snapshot_failed: {last_err}")


def _persist_snapshot(jpeg: bytes) -> str:
    """Write JPEG evidence; return public ``/images/...`` URL for incident rows."""
    from ..services.sentinel_incident_service import store_incident_snapshot

    snap_name = f"incident_{uuid.uuid4()}.jpg"
    tmp_dir = Path("temp_images")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".jpg", dir=tmp_dir, delete=False) as fh:
        fh.write(jpeg)
        temp_path = Path(fh.name)
    try:
        store_incident_snapshot(snap_name, temp_path)
    finally:
        temp_path.unlink(missing_ok=True)
    return f"/images/{snap_name}"


async def _company_punch_coords(
    db: AsyncSession, company_id: UUID
) -> Optional[tuple[float, float]]:
    """CCTV has no client GPS — use the first active company location when present."""
    row = (
        await db.execute(
            select(CompanyLocation)
            .where(
                CompanyLocation.companyId == company_id,
                CompanyLocation.deletedAt.is_(None),
            )
            .order_by(CompanyLocation.createdAt.asc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    lat = float(row.latitude)
    lon = float(row.longitude)
    if abs(lat) < 1e-6 and abs(lon) < 1e-6:
        return None
    return lat, lon


async def _resolve_station_mode(
    db: AsyncSession, cam: Camera, module_cfg: dict
) -> str:
    mode = str(cam.stationMode or module_cfg.get("defaultStationMode") or "ATTENDANCE")
    mode = mode.strip().upper()
    if mode not in VALID_STATION_MODES:
        mode = "ATTENDANCE"
    return mode


async def _embed_frame(
    jpeg: bytes, *, company_id: UUID
) -> Optional[list[float]]:
    from ..utils.face_engine import decode_image_bytes, extract_face_features_bgr

    frame = await asyncio.to_thread(decode_image_bytes, jpeg)
    stale_ms = float(settings.WORKER_CCTV_STALE_MS)

    def _work(img=frame):
        features = extract_face_features_bgr(img, require_quality=False)
        if features is None:
            return None
        encoding, _bbox = features
        return encoding

    return await run_on_face_gpu(
        _work,
        kind="cctv",
        company_id=company_id,
        stale_ms=stale_ms,
    )


async def _handle_attendance_like(
    db: AsyncSession,
    *,
    cam: Camera,
    company_id: UUID,
    mode: str,
    encoding: list[float],
    jpeg: bytes,
    snapshot_url: str,
    module_cfg: dict,
) -> dict[str, Any]:
    from fastapi import HTTPException

    from ..controllers.face_controller import _finalize_check_in, _resolve_match_response
    from ..services.sentinel_incident_service import record_incident

    coords = await _company_punch_coords(db, company_id)
    attendance: Optional[dict] = None
    if coords is not None:
        lat, lon = coords
        try:
            attendance = await _finalize_check_in(
                db=db,
                companyId=company_id,
                latitude=lat,
                longitude=lon,
                note=f"CCTV auto · {cam.name}",
                target_encoding=encoding,
                photo_source_bytes=jpeg,
                liveness_passed=False,
                mode="cctv",
                default_note=f"CCTV camera {cam.name}",
                station_mode=mode,
            )
        except HTTPException as he:
            # 401 = no gallery match (expected); anything else is logged.
            if int(getattr(he, "status_code", 0) or 0) not in (401, 403):
                logger.warning(
                    "CCTV attendance finalize failed cam=%s: %s", cam.cameraId, he.detail
                )
        except Exception as exc:  # noqa: BLE001 — still record sighting
            logger.warning(
                "CCTV attendance finalize failed cam=%s: %s", cam.cameraId, exc
            )
    else:
        # No company location → identify only (no punch); still log match incidents.
        try:
            attendance = await _resolve_match_response(
                db,
                encoding,
                liveness_passed=False,
                companyId=company_id,
                stationMode=mode,
            )
        except HTTPException:
            attendance = None
        except Exception as exc:  # noqa: BLE001
            logger.warning("CCTV match-only failed cam=%s: %s", cam.cameraId, exc)
            attendance = None

    member_id = None
    subject = None
    confidence = None
    distance = None
    matched = False
    if attendance and attendance.get("matched"):
        matched = True
        subject = (attendance.get("member") or {}).get("fullName") or (
            attendance.get("employee") or {}
        ).get("fullName")
        confidence = attendance.get("confidencePercent")
        distance = attendance.get("distance")
        try:
            member_id = UUID(str(attendance["memberId"]))
        except (KeyError, ValueError, TypeError):
            member_id = None

    if matched:
        inc, created = await record_incident(
            db,
            company_id=company_id,
            event_type="CCTV_MATCH",
            severity="INFO",
            member_id=member_id,
            subject_name=subject or "Employee",
            identity_type="EMPLOYEE",
            zone_id=cam.zoneId,
            zone_name=cam.name,
            confidence_percent=confidence,
            distance=distance,
            snapshot_url=snapshot_url,
            action_taken=(
                f"CCTV attendance ({mode})"
                + (" · punched" if attendance and attendance.get("checkedIn") else "")
                + (" · duplicate" if attendance and attendance.get("duplicate") else "")
            ),
        )
        return {
            "decision": "ATTENDANCE",
            "matched": True,
            "incidentId": str(inc.incidentId),
            "incidentCreated": created,
            "checkedIn": bool(attendance and attendance.get("checkedIn")),
            "duplicate": bool(attendance and attendance.get("duplicate")),
        }

    # No employee match on attendance-like CCTV — optional unknown-face incident.
    rules = module_cfg.get("scanActionRules") or {}
    unknown = str(rules.get("unknownFaceAction") or "IGNORE").strip().upper()
    if unknown == "LOG_INCIDENT":
        inc, created = await record_incident(
            db,
            company_id=company_id,
            event_type="ACCESS_DENIED",
            severity="WARNING",
            subject_name="Unknown Person",
            identity_type="UNKNOWN",
            zone_id=cam.zoneId,
            zone_name=cam.name,
            snapshot_url=snapshot_url,
            action_taken=f"CCTV unknown face ({mode})",
        )
        return {
            "decision": "UNKNOWN_FACE",
            "matched": False,
            "incidentId": str(inc.incidentId),
            "incidentCreated": created,
        }
    return {"decision": "NO_MATCH", "matched": False}


async def _handle_sentinel_mode(
    db: AsyncSession,
    *,
    cam: Camera,
    company_id: UUID,
    mode: str,
    encoding: list[float],
    snapshot_url: str,
    module_cfg: dict,
) -> dict[str, Any]:
    from ..routes.sentinel_routes import evaluate_unified_scan_decision

    zone_id = str(cam.zoneId) if cam.zoneId else module_cfg.get("defaultZoneId")
    event_id = module_cfg.get("defaultEventId")
    result = await evaluate_unified_scan_decision(
        db,
        company_id,
        encoding,
        station_mode=mode,
        zone_id=zone_id,
        event_id=event_id,
        snapshot_url=snapshot_url,
        scan_action_rules=module_cfg.get("scanActionRules"),
    )
    incident = result.get("incident") or {}
    return {
        "decision": result.get("decision"),
        "matched": bool(result.get("matched")),
        "accessGranted": result.get("accessGranted"),
        "incidentId": incident.get("incidentId"),
        "stationMode": mode,
    }


async def analyze_camera(db: AsyncSession, cam: Camera) -> dict[str, Any]:
    """Grab one frame, embed via ``cctv`` GPU lane, then incident / attendance."""
    company_id = cam.companyId
    module_cfg = await get_company_module_config(db, company_id)
    if not _cctv_enabled_for_company(module_cfg):
        return {"skipped": True, "reason": "module_cctv_disabled"}

    mode = await _resolve_station_mode(db, cam, module_cfg)
    attendance_like = mode in ATTENDANCE_LIKE_MODES
    if not attendance_like and not should_run_sentinel_search(mode):
        return {"skipped": True, "reason": "station_mode_unsupported", "stationMode": mode}

    stats = face_gpu_queue_stats()
    if _should_pause_for_kiosk(stats):
        return {
            "skipped": True,
            "reason": "kiosk_backpressure",
            "kioskPending": _kiosk_pending(stats),
            "pending": stats.get("pending"),
        }

    try:
        jpeg = await _grab_frame_jpeg(cam)
    except Exception as exc:  # noqa: BLE001
        cam.status = "error"
        return {"ok": False, "error": f"snapshot: {exc}"}

    try:
        encoding = await _embed_frame(jpeg, company_id=company_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("CCTV embed failed cam=%s: %s", cam.cameraId, exc)
        return {"ok": False, "error": f"embed: {exc}"}

    cam.lastAnalyzedAt = _now()

    if encoding is None:
        return {"ok": True, "faces": 0, "stationMode": mode}

    snapshot_url = _persist_snapshot(jpeg)

    if attendance_like:
        outcome = await _handle_attendance_like(
            db,
            cam=cam,
            company_id=company_id,
            mode=mode,
            encoding=encoding,
            jpeg=jpeg,
            snapshot_url=snapshot_url,
            module_cfg=module_cfg,
        )
    else:
        outcome = await _handle_sentinel_mode(
            db,
            cam=cam,
            company_id=company_id,
            mode=mode,
            encoding=encoding,
            snapshot_url=snapshot_url,
            module_cfg=module_cfg,
        )

    return {"ok": True, "faces": 1, "stationMode": mode, **outcome}


async def list_due_cameras(
    db: AsyncSession, *, now: Optional[datetime] = None
) -> list[Camera]:
    """Active cameras with analysis enabled whose interval has elapsed."""
    now = now or _now()
    interval = timedelta(seconds=max(5, int(settings.WORKER_CCTV_CAMERA_INTERVAL_SECONDS)))
    due_before = now - interval
    stmt = (
        select(Camera)
        .where(
            Camera.analysisEnabled.is_(True),
            Camera.isActive.is_(True),
            Camera.deletedAt.is_(None),
            or_(Camera.lastAnalyzedAt.is_(None), Camera.lastAnalyzedAt <= due_before),
        )
        .order_by(Camera.lastAnalyzedAt.asc().nullsfirst())
    )
    return list((await db.execute(stmt)).scalars().all())


async def run_cctv_analysis_tick(
    *, stop_event: Optional[asyncio.Event] = None
) -> dict[str, Any]:
    """One worker tick: process due cameras with a concurrency cap."""
    await ensure_face_gpu_for_cctv()
    max_concurrent = max(1, int(settings.WORKER_CCTV_MAX_CONCURRENT))
    sem = asyncio.Semaphore(max_concurrent)
    analyzed = 0
    skipped = 0
    errors = 0
    results: list[dict[str, Any]] = []

    async with async_session() as db:
        cameras = await list_due_cameras(db)

    if not cameras:
        return {"analyzed": 0, "skipped": 0, "errors": 0, "due": 0}

    async def _one(cam_id: UUID, company_id: UUID) -> dict[str, Any]:
        nonlocal analyzed, skipped, errors
        if stop_event is not None and stop_event.is_set():
            return {"skipped": True, "reason": "stopping"}
        async with sem:
            if stop_event is not None and stop_event.is_set():
                return {"skipped": True, "reason": "stopping"}
            stats = face_gpu_queue_stats()
            if _should_pause_for_kiosk(stats):
                skipped += 1
                return {
                    "cameraId": str(cam_id),
                    "skipped": True,
                    "reason": "kiosk_backpressure",
                }
            async with async_session() as db:
                cam = await db.get(Camera, cam_id)
                if (
                    cam is None
                    or cam.companyId != company_id
                    or not cam.analysisEnabled
                    or not cam.isActive
                    or cam.deletedAt is not None
                ):
                    skipped += 1
                    return {"cameraId": str(cam_id), "skipped": True, "reason": "stale"}
                try:
                    outcome = await analyze_camera(db, cam)
                    await db.commit()
                except Exception as exc:  # noqa: BLE001
                    await db.rollback()
                    errors += 1
                    logger.exception("CCTV analyze failed cam=%s", cam_id)
                    return {"cameraId": str(cam_id), "ok": False, "error": str(exc)}
                if outcome.get("skipped"):
                    skipped += 1
                elif outcome.get("ok") is False:
                    errors += 1
                else:
                    analyzed += 1
                return {"cameraId": str(cam_id), **outcome}

    tasks = [_one(c.cameraId, c.companyId) for c in cameras]
    raw = await asyncio.gather(*tasks, return_exceptions=True)
    for item in raw:
        if isinstance(item, Exception):
            errors += 1
            results.append({"ok": False, "error": str(item)})
        else:
            results.append(item)

    return {
        "due": len(cameras),
        "analyzed": analyzed,
        "skipped": skipped,
        "errors": errors,
        "results": results[:50],
    }
