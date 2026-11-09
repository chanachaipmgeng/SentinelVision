"""Event clip export (5s pre / 10s post) + continuous recording refs (Phase 4B)."""
from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.settings import settings
from ..models.camera import Camera
from ..models.video_clip import (
    CLIP_KIND_CONTINUOUS_REF,
    CLIP_KIND_EVENT,
    VALID_CLIP_KINDS,
    VideoClip,
)
from ..services import mediamtx_service
from ..services.storage_service import (
    EVIDENCE_KIND_VIDEO_CLIP,
    ROOTS,
    delete_stored_image,
    read_image_bytes,
    store_evidence_image,
)

logger = logging.getLogger("dpu.video_clip")

_SEG_NAME_RE = re.compile(
    r"^(?P<y>\d{4})-(?P<m>\d{2})-(?P<d>\d{2})_"
    r"(?P<H>\d{2})-(?P<M>\d{2})-(?P<S>\d{2})-(?P<f>\d+)"
)


def pre_seconds() -> int:
    return max(0, int(getattr(settings, "VIDEO_CLIP_PRE_SECONDS", 5) or 5))


def post_seconds() -> int:
    return max(0, int(getattr(settings, "VIDEO_CLIP_POST_SECONDS", 10) or 10))


def recordings_root() -> Path:
    return Path(getattr(settings, "MEDIAMTX_RECORDINGS_DIR", None) or "/recordings")


def serialize_clip(clip: VideoClip, *, camera_name: Optional[str] = None) -> dict[str, Any]:
    return {
        "clipId": str(clip.clipId),
        "companyId": str(clip.companyId),
        "cameraId": str(clip.cameraId),
        "cameraName": camera_name,
        "incidentId": str(clip.incidentId) if clip.incidentId else None,
        "startedAt": clip.startedAt,
        "endedAt": clip.endedAt,
        "storageKey": clip.storageKey,
        "durationMs": int(clip.durationMs or 0),
        "kind": clip.kind,
        "createdAt": clip.createdAt,
        "downloadPath": f"/cameras/company/{clip.companyId}/clips/{clip.clipId}/download",
    }


async def get_company_camera(db: AsyncSession, company_id: UUID, camera_id: UUID) -> Camera:
    cam = await db.get(Camera, camera_id)
    if cam is None or cam.companyId != company_id or cam.deletedAt is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    return cam


async def resolve_camera_for_incident(
    db: AsyncSession,
    company_id: UUID,
    *,
    camera_id: Optional[UUID] = None,
    zone_id: Optional[UUID] = None,
) -> Optional[Camera]:
    if camera_id is not None:
        try:
            return await get_company_camera(db, company_id, camera_id)
        except HTTPException:
            return None
    if zone_id is None:
        return None
    stmt = (
        select(Camera)
        .where(
            Camera.companyId == company_id,
            Camera.zoneId == zone_id,
            Camera.deletedAt.is_(None),
            Camera.isActive.is_(True),
        )
        .order_by(Camera.createdAt.asc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


def _parse_segment_start(name: str) -> Optional[datetime]:
    m = _SEG_NAME_RE.match(Path(name).stem)
    if not m:
        return None
    try:
        micro = int((m.group("f") + "000000")[:6])
        return datetime(
            int(m.group("y")),
            int(m.group("m")),
            int(m.group("d")),
            int(m.group("H")),
            int(m.group("M")),
            int(m.group("S")),
            micro,
            tzinfo=timezone.utc,
        )
    except ValueError:
        return None


def _ffmpeg_bin() -> str:
    configured = (getattr(settings, "VIDEO_CLIP_FFMPEG_BIN", None) or "ffmpeg").strip()
    return shutil.which(configured) or shutil.which("ffmpeg") or configured


async def _run_ffmpeg(args: list[str]) -> tuple[int, str]:
    bin_path = _ffmpeg_bin()
    cmd = [bin_path, "-y", *args]
    timeout = float(getattr(settings, "VIDEO_CLIP_FFMPEG_TIMEOUT_SECONDS", 90) or 90)
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        return 127, "ffmpeg_not_found"
    try:
        _out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return 124, "ffmpeg_timeout"
    return int(proc.returncode or 0), (err or b"").decode("utf-8", errors="replace")[-2000:]


def _camera_recording_dir(camera_id: UUID) -> Path:
    return recordings_root() / mediamtx_service.path_name_for_camera(camera_id)


def list_recording_segments(camera_id: UUID) -> list[tuple[Path, datetime]]:
    root = _camera_recording_dir(camera_id)
    if not root.is_dir():
        return []
    out: list[tuple[Path, datetime]] = []
    for path in sorted(root.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".mp4", ".m4s", ".mkv", ".ts"}:
            continue
        started = _parse_segment_start(path.name) or datetime.fromtimestamp(
            path.stat().st_mtime, tz=timezone.utc
        )
        out.append((path, started))
    return out


async def _cut_from_recordings(
    camera_id: UUID,
    *,
    window_start: datetime,
    window_end: datetime,
    dest: Path,
) -> bool:
    segments = list_recording_segments(camera_id)
    if not segments:
        return False
    # Prefer the newest segment that starts at or before window_start; else nearest.
    candidates = [p for p, st in segments if st <= window_end]
    if not candidates:
        return False
    # Use the last segment that overlaps the window start when possible.
    chosen = candidates[-1]
    for path, st in segments:
        if st <= window_start:
            chosen = path
    seg_start = _parse_segment_start(chosen.name) or window_start
    ss = max(0.0, (window_start - seg_start).total_seconds())
    duration = max(0.5, (window_end - window_start).total_seconds())
    # MediaMTX fmp4 often needs remux; fall back to re-encode audio/video copy.
    code, err = await _run_ffmpeg(
        [
            "-ss",
            f"{ss:.3f}",
            "-i",
            str(chosen),
            "-t",
            f"{duration:.3f}",
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(dest),
        ]
    )
    if code == 0 and dest.is_file() and dest.stat().st_size > 0:
        return True
    logger.info("ffmpeg copy cut failed (%s); retry encode: %s", code, err[:300])
    code, err = await _run_ffmpeg(
        [
            "-ss",
            f"{ss:.3f}",
            "-i",
            str(chosen),
            "-t",
            f"{duration:.3f}",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(dest),
        ]
    )
    if code == 0 and dest.is_file() and dest.stat().st_size > 0:
        return True
    logger.warning("ffmpeg recording cut failed: %s", err[:400])
    return False


async def _capture_from_live(
    camera_id: UUID,
    *,
    duration_s: float,
    dest: Path,
) -> bool:
    path_name = mediamtx_service.path_name_for_camera(camera_id)
    rtsp_base = (settings.MEDIAMTX_RTSP_PUBLISH_URL or "rtsp://mediamtx:8554").rstrip("/")
    hls_base = (getattr(settings, "MEDIAMTX_HLS_INTERNAL_URL", None) or "http://mediamtx:8888").rstrip(
        "/"
    )
    sources = [
        f"{hls_base}/{path_name}/index.m3u8",
        f"{rtsp_base}/{path_name}",
    ]
    duration_s = max(1.0, float(duration_s))
    for src in sources:
        args: list[str] = []
        if src.startswith("rtsp://"):
            args.extend(["-rtsp_transport", "tcp"])
        args.extend(
            [
                "-i",
                src,
                "-t",
                f"{duration_s:.3f}",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-an",
                "-movflags",
                "+faststart",
                str(dest),
            ]
        )
        code, err = await _run_ffmpeg(args)
        if code == 0 and dest.is_file() and dest.stat().st_size > 0:
            return True
        logger.info("live capture via %s failed (%s): %s", src, code, err[:300])
        if dest.exists():
            try:
                dest.unlink()
            except OSError:
                pass
    return False


async def export_event_clip(
    db: AsyncSession,
    company_id: UUID,
    camera_id: UUID,
    *,
    incident_id: Optional[UUID] = None,
    occurred_at: Optional[datetime] = None,
    wait_for_post: bool = True,
) -> VideoClip:
    """Cut/export a 5s-pre / 10s-post event clip and persist under retention kind ``video_clip``."""
    cam = await get_company_camera(db, company_id, camera_id)
    now = datetime.now(timezone.utc)
    pivot = occurred_at or now
    if pivot.tzinfo is None:
        pivot = pivot.replace(tzinfo=timezone.utc)

    window_start = pivot - timedelta(seconds=pre_seconds())
    window_end = pivot + timedelta(seconds=post_seconds())
    duration_ms = int((window_end - window_start).total_seconds() * 1000)

    if wait_for_post:
        delay = (window_end - now).total_seconds()
        if delay > 0:
            # Cap wait so API callers with wait_for_post=false path stay responsive via hook.
            await asyncio.sleep(min(delay, float(post_seconds()) + 2.0))

    with tempfile.TemporaryDirectory(prefix="dpu-clip-") as tmp:
        dest = Path(tmp) / "clip.mp4"
        ok = await _cut_from_recordings(
            cam.cameraId, window_start=window_start, window_end=window_end, dest=dest
        )
        if not ok:
            # Live/HLS fallback: capture the full window length from the live path.
            ok = await _capture_from_live(
                cam.cameraId,
                duration_s=(window_end - window_start).total_seconds(),
                dest=dest,
            )
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to export clip (no MediaMTX buffer / ffmpeg failed)",
            )

        filename = f"{uuid4().hex}.mp4"
        stored = store_evidence_image(
            EVIDENCE_KIND_VIDEO_CLIP,
            filename,
            dest,
            move=False,
            content_type="video/mp4",
        )

    clip = VideoClip(
        companyId=company_id,
        cameraId=cam.cameraId,
        incidentId=incident_id,
        startedAt=window_start,
        endedAt=window_end,
        storageKey=stored,
        durationMs=duration_ms,
        kind=CLIP_KIND_EVENT,
    )
    db.add(clip)
    await db.commit()
    await db.refresh(clip)
    return clip


async def schedule_incident_clip_export(
    *,
    company_id: UUID,
    camera_id: UUID,
    incident_id: UUID,
    occurred_at: datetime,
) -> None:
    """Background export after incident create — does not raise to the request path."""
    from ..config.database import async_session

    try:
        async with async_session() as db:
            await export_event_clip(
                db,
                company_id,
                camera_id,
                incident_id=incident_id,
                occurred_at=occurred_at,
                wait_for_post=True,
            )
    except Exception as exc:
        logger.warning(
            "incident clip export failed company=%s camera=%s incident=%s: %s",
            company_id,
            camera_id,
            incident_id,
            exc,
        )


async def upsert_continuous_refs(
    db: AsyncSession,
    company_id: UUID,
    camera_id: UUID,
) -> list[VideoClip]:
    """Index MediaMTX continuous segments as ``continuous_ref`` rows (continuous cameras only)."""
    cam = await get_company_camera(db, company_id, camera_id)
    if (cam.recordMode or "").strip().lower() != "continuous":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="continuous_ref listing is only available for continuous cameras",
        )
    segments = list_recording_segments(cam.cameraId)
    path_name = mediamtx_service.path_name_for_camera(cam.cameraId)
    out: list[VideoClip] = []
    for path, started in segments[-100:]:
        # Assume segment duration from MediaMTX default (1h) unless file mtime suggests shorter.
        ended = started + timedelta(hours=1)
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            if mtime > started:
                ended = mtime
        except OSError:
            pass
        storage_key = f"mtx:{path_name}/{path.name}"
        existing = (
            await db.execute(
                select(VideoClip).where(
                    VideoClip.companyId == company_id,
                    VideoClip.storageKey == storage_key,
                )
            )
        ).scalar_one_or_none()
        if existing:
            out.append(existing)
            continue
        duration_ms = max(0, int((ended - started).total_seconds() * 1000))
        row = VideoClip(
            companyId=company_id,
            cameraId=cam.cameraId,
            incidentId=None,
            startedAt=started,
            endedAt=ended,
            storageKey=storage_key,
            durationMs=duration_ms,
            kind=CLIP_KIND_CONTINUOUS_REF,
        )
        db.add(row)
        out.append(row)
    await db.commit()
    for row in out:
        await db.refresh(row)
    return out


async def list_clips(
    db: AsyncSession,
    company_id: UUID,
    *,
    camera_id: Optional[UUID] = None,
    incident_id: Optional[UUID] = None,
    kind: Optional[str] = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    kind_norm = (kind or "").strip().lower() or None
    if kind_norm and kind_norm not in VALID_CLIP_KINDS:
        raise HTTPException(status_code=400, detail="kind must be event or continuous_ref")

    # continuous_ref: refresh index for requested continuous camera(s) first.
    if kind_norm in (None, CLIP_KIND_CONTINUOUS_REF):
        cam_q = select(Camera).where(
            Camera.companyId == company_id,
            Camera.deletedAt.is_(None),
            Camera.recordMode == "continuous",
        )
        if camera_id is not None:
            cam_q = cam_q.where(Camera.cameraId == camera_id)
        continuous_cams = (await db.execute(cam_q)).scalars().all()
        for cam in continuous_cams:
            try:
                await upsert_continuous_refs(db, company_id, cam.cameraId)
            except HTTPException:
                continue

    stmt = select(VideoClip).where(VideoClip.companyId == company_id)
    if camera_id is not None:
        stmt = stmt.where(VideoClip.cameraId == camera_id)
    if incident_id is not None:
        stmt = stmt.where(VideoClip.incidentId == incident_id)
    if kind_norm:
        stmt = stmt.where(VideoClip.kind == kind_norm)
    elif camera_id is None:
        # Default list: event clips for all cameras + continuous_ref only for continuous cams
        # (already indexed above). Keep both kinds.
        pass

    # Hide continuous_ref for non-continuous cameras (stale rows after mode change).
    if kind_norm == CLIP_KIND_CONTINUOUS_REF and camera_id is not None:
        cam = await get_company_camera(db, company_id, camera_id)
        if (cam.recordMode or "").strip().lower() != "continuous":
            return []

    stmt = stmt.order_by(VideoClip.startedAt.desc()).limit(max(1, min(500, int(limit or 100))))
    rows = (await db.execute(stmt)).scalars().all()

    # Filter continuous_ref to continuous cameras only when mixed listing.
    cam_ids = {r.cameraId for r in rows}
    cam_modes: dict[UUID, str] = {}
    if cam_ids:
        cams = (
            await db.execute(select(Camera).where(Camera.cameraId.in_(list(cam_ids))))
        ).scalars().all()
        cam_modes = {c.cameraId: (c.recordMode or "") for c in cams}
        cam_names = {c.cameraId: c.name for c in cams}
    else:
        cam_names = {}

    filtered: list[VideoClip] = []
    for r in rows:
        if r.kind == CLIP_KIND_CONTINUOUS_REF:
            if (cam_modes.get(r.cameraId) or "").lower() != "continuous":
                continue
        filtered.append(r)

    return [
        serialize_clip(r, camera_name=cam_names.get(r.cameraId))
        for r in filtered
    ]


async def get_clip(db: AsyncSession, company_id: UUID, clip_id: UUID) -> VideoClip:
    clip = await db.get(VideoClip, clip_id)
    if clip is None or clip.companyId != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clip not found")
    if clip.kind == CLIP_KIND_CONTINUOUS_REF:
        cam = await db.get(Camera, clip.cameraId)
        if cam is None or (cam.recordMode or "").lower() != "continuous":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clip not found")
    return clip


def resolve_clip_bytes(clip: VideoClip) -> tuple[bytes, str]:
    """Return (bytes, filename) for download. continuous_ref reads MediaMTX volume."""
    key = (clip.storageKey or "").strip()
    if clip.kind == CLIP_KIND_CONTINUOUS_REF or key.startswith("mtx:"):
        rel = key[4:] if key.startswith("mtx:") else key
        path = recordings_root() / rel
        # Prevent path escape
        try:
            path = path.resolve()
            root = recordings_root().resolve()
            if root not in path.parents and path != root:
                raise HTTPException(status_code=400, detail="Invalid storage key")
        except OSError as exc:
            raise HTTPException(status_code=404, detail="Recording file missing") from exc
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Recording file missing")
        return path.read_bytes(), path.name

    data = read_image_bytes("video_clips", Path(key).name)
    if not data:
        # Legacy fallback if somehow stored under uploaded_images
        data = read_image_bytes("uploaded_images", Path(key).name)
    if not data:
        raise HTTPException(status_code=404, detail="Clip file missing")
    return data, Path(key).name


async def delete_clip(db: AsyncSession, company_id: UUID, clip_id: UUID) -> dict[str, Any]:
    clip = await get_clip(db, company_id, clip_id)
    key = (clip.storageKey or "").strip()
    removed = False
    if clip.kind == CLIP_KIND_EVENT and key and not key.startswith("mtx:"):
        removed = delete_stored_image("video_clips", Path(key).name)
    await db.delete(clip)
    await db.commit()
    return {"deleted": True, "fileRemoved": removed, "clipId": str(clip_id)}


def ensure_video_clip_dirs() -> None:
    ROOTS["video_clips"].mkdir(exist_ok=True)
    try:
        os.chmod(ROOTS["video_clips"], 0o755)
    except OSError:
        pass
