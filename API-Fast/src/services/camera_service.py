"""Camera CRUD, ping, snapshot, and MediaMTX path sync (Phase 3)."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import quote, urlparse, urlunparse
from uuid import UUID, uuid4

import cv2
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.camera import Camera
from ..services import mediamtx_service
from ..services.company_module_service import VALID_STATION_MODES
from ..services.outbox_crypto import decrypt_secret, encrypt_secret
from ..utils.stream_ping import check_stream_reachability

logger = logging.getLogger(__name__)

VALID_PROTOCOLS = ("rtsp", "http", "hls", "rtmp")
VALID_RECORD_MODES = ("off", "event", "continuous")
VALID_STATUSES = ("unknown", "online", "offline", "error")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _clean_uuid(raw: Any, *, field: str) -> Optional[UUID]:
    if raw in (None, ""):
        return None
    try:
        return UUID(str(raw))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid UUID for {field}") from exc


def _seal_credentials(username: Optional[str], password: Optional[str]) -> Optional[str]:
    user = (username or "").strip()
    pwd = password or ""
    if not user and not pwd:
        return None
    payload = json.dumps({"username": user, "password": pwd}, separators=(",", ":"))
    return encrypt_secret(payload)


def _unseal_credentials(sealed: Optional[str]) -> dict[str, str]:
    if not sealed:
        return {}
    try:
        raw = decrypt_secret(sealed)
        data = json.loads(raw)
        if not isinstance(data, dict):
            return {}
        return {
            "username": str(data.get("username") or ""),
            "password": str(data.get("password") or ""),
        }
    except Exception:
        logger.warning("Failed to decrypt camera credentials")
        return {}


def effective_stream_url(camera: Camera) -> str:
    """Merge sealed credentials into stream URL when the URL has no userinfo."""
    url = (camera.streamUrl or "").strip()
    if not url:
        return url
    parsed = urlparse(url)
    if parsed.username:
        return url
    creds = _unseal_credentials(camera.credentialsEnc)
    user = creds.get("username") or ""
    pwd = creds.get("password") or ""
    if not user:
        return url
    host = parsed.hostname or ""
    if not host:
        return url
    auth = quote(user, safe="")
    if pwd:
        auth += ":" + quote(pwd, safe="")
    port = f":{parsed.port}" if parsed.port else ""
    netloc = f"{auth}@{host}{port}"
    return urlunparse((parsed.scheme, netloc, parsed.path or "/", "", parsed.query, ""))


def serialize_camera(cam: Camera, *, include_secrets: bool = False) -> dict[str, Any]:
    creds = _unseal_credentials(cam.credentialsEnc) if include_secrets else {}
    has_creds = bool(cam.credentialsEnc)
    out: dict[str, Any] = {
        "cameraId": str(cam.cameraId),
        "companyId": str(cam.companyId),
        "name": cam.name,
        "streamUrl": cam.streamUrl,
        "protocol": cam.protocol,
        "description": cam.description,
        "hasCredentials": has_creds,
        "siteFloorId": str(cam.siteFloorId) if cam.siteFloorId else None,
        "zoneId": str(cam.zoneId) if cam.zoneId else None,
        "stationMode": cam.stationMode,
        "mapPosX": cam.mapPosX,
        "mapPosY": cam.mapPosY,
        "recordMode": cam.recordMode,
        "status": cam.status,
        "lastPingAt": cam.lastPingAt,
        "lastPingLatencyMs": cam.lastPingLatencyMs,
        "previewImageUrl": cam.previewImageUrl,
        "isActive": cam.isActive,
        "analysisEnabled": bool(cam.analysisEnabled),
        "lastAnalyzedAt": cam.lastAnalyzedAt,
        "aiConfig": cam.aiConfig if isinstance(getattr(cam, "aiConfig", None), dict) else (cam.aiConfig or None),
        "whepPath": mediamtx_service.whep_path(cam.cameraId),
        "hlsPath": mediamtx_service.hls_path(cam.cameraId),
        "mtxPath": mediamtx_service.path_name_for_camera(cam.cameraId),
        "createdAt": cam.createdAt,
        "updatedAt": cam.updatedAt,
    }
    if include_secrets and creds.get("username"):
        out["streamUsername"] = creds["username"]
    return out


async def get_company_camera(db: AsyncSession, company_id: UUID, camera_id: UUID) -> Camera:
    cam = await db.get(Camera, camera_id)
    if not cam or cam.companyId != company_id or cam.deletedAt is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    return cam


async def list_cameras(db: AsyncSession, company_id: UUID) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(Camera)
            .where(Camera.companyId == company_id, Camera.deletedAt.is_(None))
            .order_by(Camera.createdAt.desc())
        )
    ).scalars().all()
    return [serialize_camera(r) for r in rows]


def _apply_body(cam: Camera, body: dict[str, Any], *, creating: bool) -> None:
    if "name" in body or creating:
        name = str(body.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="name is required")
        cam.name = name[:160]

    if "streamUrl" in body or creating:
        url = str(body.get("streamUrl") or "").strip()
        if not url:
            raise HTTPException(status_code=400, detail="streamUrl is required")
        cam.streamUrl = url

    if "protocol" in body or creating:
        proto = str(body.get("protocol") or cam.protocol or "rtsp").strip().lower()
        if proto not in VALID_PROTOCOLS:
            raise HTTPException(
                status_code=400, detail=f"protocol must be one of {', '.join(VALID_PROTOCOLS)}"
            )
        cam.protocol = proto

    if "description" in body:
        desc = body.get("description")
        cam.description = None if desc in (None, "") else str(desc)[:2000]

    if "recordMode" in body or creating:
        mode = str(body.get("recordMode") or cam.recordMode or "event").strip().lower()
        if mode not in VALID_RECORD_MODES:
            raise HTTPException(
                status_code=400,
                detail=f"recordMode must be one of {', '.join(VALID_RECORD_MODES)}",
            )
        cam.recordMode = mode

    if "stationMode" in body:
        raw = body.get("stationMode")
        if raw in (None, ""):
            cam.stationMode = None
        else:
            mode = str(raw).strip().upper()
            if mode not in VALID_STATION_MODES:
                raise HTTPException(
                    status_code=400,
                    detail=f"stationMode must be one of {', '.join(VALID_STATION_MODES)}",
                )
            cam.stationMode = mode

    if "zoneId" in body:
        cam.zoneId = _clean_uuid(body.get("zoneId"), field="zoneId")
    if "siteFloorId" in body:
        cam.siteFloorId = _clean_uuid(body.get("siteFloorId"), field="siteFloorId")

    if "mapPosX" in body:
        cam.mapPosX = None if body.get("mapPosX") in (None, "") else float(body["mapPosX"])
    if "mapPosY" in body:
        cam.mapPosY = None if body.get("mapPosY") in (None, "") else float(body["mapPosY"])

    if "isActive" in body:
        cam.isActive = bool(body.get("isActive"))

    if "analysisEnabled" in body:
        cam.analysisEnabled = bool(body.get("analysisEnabled"))

    if "aiConfig" in body:
        raw = body.get("aiConfig")
        if raw in (None, ""):
            cam.aiConfig = None
        elif isinstance(raw, dict):
            from ..services.people_analytics import normalize_ai_config

            cam.aiConfig = normalize_ai_config(raw)
        else:
            raise HTTPException(status_code=400, detail="aiConfig must be an object")

    # Credentials: accept streamUsername/streamPassword; empty password + clearCredentials clears.
    if body.get("clearCredentials"):
        cam.credentialsEnc = None
    elif "streamUsername" in body or "streamPassword" in body:
        existing = _unseal_credentials(cam.credentialsEnc)
        user = body.get("streamUsername", existing.get("username"))
        pwd = body.get("streamPassword", existing.get("password"))
        if body.get("streamPassword") == "":
            pwd = existing.get("password") or ""
        cam.credentialsEnc = _seal_credentials(
            None if user in (None, "") else str(user),
            None if pwd in (None,) else str(pwd),
        )


async def _sync_mtx(cam: Camera) -> dict[str, Any]:
    if not cam.isActive or cam.recordMode == "off" and cam.protocol not in ("rtsp", "http", "hls"):
        # Still publish pull path when active for live wall even if recordMode=off/event.
        pass
    if not cam.isActive:
        return await mediamtx_service.delete_path(cam.cameraId)
    source = effective_stream_url(cam)
    record = cam.recordMode == "continuous"
    try:
        return await mediamtx_service.upsert_pull_path(
            cam.cameraId, source_url=source, record=record
        )
    except Exception as exc:
        logger.warning("MediaMTX sync failed for %s: %s", cam.cameraId, exc)
        return {"ok": False, "error": str(exc)}


async def create_camera(db: AsyncSession, company_id: UUID, body: dict[str, Any]) -> dict[str, Any]:
    cam = Camera(cameraId=uuid4(), companyId=company_id, status="unknown", isActive=True)
    _apply_body(cam, body or {}, creating=True)
    db.add(cam)
    await db.commit()
    await db.refresh(cam)
    mtx = await _sync_mtx(cam)
    out = serialize_camera(cam)
    out["mediamtx"] = mtx
    return out


async def update_camera(
    db: AsyncSession, company_id: UUID, camera_id: UUID, body: dict[str, Any]
) -> dict[str, Any]:
    cam = await get_company_camera(db, company_id, camera_id)
    _apply_body(cam, body or {}, creating=False)
    await db.commit()
    await db.refresh(cam)
    mtx = await _sync_mtx(cam)
    out = serialize_camera(cam)
    out["mediamtx"] = mtx
    return out


async def delete_camera(db: AsyncSession, company_id: UUID, camera_id: UUID) -> dict[str, Any]:
    cam = await get_company_camera(db, company_id, camera_id)
    cam.deletedAt = _now()
    cam.isActive = False
    await db.commit()
    mtx = await mediamtx_service.delete_path(camera_id)
    return {"ok": True, "cameraId": str(camera_id), "mediamtx": mtx}


async def ping_camera(db: AsyncSession, company_id: UUID, camera_id: UUID) -> dict[str, Any]:
    cam = await get_company_camera(db, company_id, camera_id)
    url = effective_stream_url(cam)
    result = await check_stream_reachability(url, protocol=cam.protocol)
    cam.lastPingAt = _now()
    cam.lastPingLatencyMs = result.get("latency_ms")
    cam.status = "online" if result.get("online") else "offline"
    await db.commit()
    await db.refresh(cam)
    # Keep MediaMTX path warm after a successful ping.
    mtx = await _sync_mtx(cam) if cam.status == "online" else None
    return {
        **result,
        "camera": serialize_camera(cam),
        "mediamtx": mtx,
    }


def _grab_snapshot_bgr(url: str, timeout_sec: float = 8.0) -> bytes:
    """Blocking OpenCV grab — run via asyncio.to_thread."""
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    try:
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, int(timeout_sec * 1000))
        cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, int(timeout_sec * 1000))
        if not cap.isOpened():
            raise RuntimeError("open_failed")
        ok, frame = cap.read()
        if not ok or frame is None:
            raise RuntimeError("read_failed")
        ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        if not ok:
            raise RuntimeError("encode_failed")
        return buf.tobytes()
    finally:
        cap.release()


async def snapshot_camera(db: AsyncSession, company_id: UUID, camera_id: UUID) -> dict[str, Any]:
    """Grab one JPEG frame from the stream (OpenCV). Returns base64 for UI preview."""
    import base64

    cam = await get_company_camera(db, company_id, camera_id)
    url = effective_stream_url(cam)
    try:
        jpeg = await asyncio.to_thread(_grab_snapshot_bgr, url)
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Snapshot failed: {exc}"
        ) from exc
    b64 = base64.b64encode(jpeg).decode("ascii")
    return {
        "cameraId": str(cam.cameraId),
        "contentType": "image/jpeg",
        "imageBase64": b64,
        "bytes": len(jpeg),
    }
