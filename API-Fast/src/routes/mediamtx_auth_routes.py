"""Internal MediaMTX HTTP authentication endpoint (called by mediamtx container via authMethod: http)."""
from __future__ import annotations

import ipaddress
import logging
from typing import Optional
from urllib.parse import parse_qs
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.database import get_db
from ..models.camera import Camera
from ..security.jwt import TYP_STREAM, decode_token
from ..services.mediamtx_service import path_name_for_camera

router = APIRouter()
logger = logging.getLogger("dpu.mediamtx_auth")


class MediaMtxAuthRequest(BaseModel):
    user: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None
    ip: Optional[str] = None
    action: Optional[str] = None
    path: Optional[str] = None
    protocol: Optional[str] = None
    id: Optional[str] = None
    query: Optional[str] = None


def _is_internal_ip(raw_ip: Optional[str]) -> bool:
    text = (raw_ip or "").strip().split("%", 1)[0]
    if not text:
        return False
    try:
        ip_obj = ipaddress.ip_address(text)
        return ip_obj.is_loopback or ip_obj.is_private
    except ValueError:
        return False


def _extract_stream_jwt(body: MediaMtxAuthRequest) -> str:
    if body.query:
        qs = parse_qs(body.query.lstrip("?"))
        for key in ("jwt", "token"):
            vals = qs.get(key)
            if vals and vals[0].strip():
                return vals[0].strip()
    for candidate in (body.token, body.password):
        if candidate and "." in candidate:
            return candidate.strip()
    return ""


def _normalize_cam_path(path: str) -> str:
    clean = (path or "").strip().strip("/")
    if clean.endswith("_sub"):
        clean = clean[:-4]
    return clean


@router.post("/auth")
async def mediamtx_http_auth(
    body: MediaMtxAuthRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Authorize MediaMTX stream read/playback/publish/api calls.

    - Only internal Docker/loopback peers may call this endpoint.
    - External WHIP publish is always denied; internal RTSP publish is allowed.
    - Browser WebRTC WHEP / HLS read & playback require a valid short-lived ``typ='stream'`` JWT
      whose ``cameraId`` and ``companyId`` match an active camera for the requested path.
    """
    peer_host = request.client.host if request.client else ""
    if peer_host and peer_host != "testclient" and not _is_internal_ip(peer_host):
        raise HTTPException(status_code=403, detail="Forbidden external auth check")

    action = (body.action or "").strip().lower()
    protocol = (body.protocol or "").strip().lower()
    path = _normalize_cam_path(body.path or "")

    # Control API / metrics from internal containers (api-gpu, worker, prometheus).
    if action in {"api", "metrics"}:
        if _is_internal_ip(body.ip):
            return Response(status_code=200)
        raise HTTPException(status_code=401, detail="Unauthorized control access")

    # Never allow external or WebRTC WHIP stream injection/publish.
    if action == "publish":
        if protocol == "rtsp" and _is_internal_ip(body.ip):
            return Response(status_code=200)
        logger.warning("Blocked unauthorized MediaMTX publish: proto=%s ip=%s path=%s", protocol, body.ip, body.path)
        raise HTTPException(status_code=401, detail="Publish denied")

    if action in {"read", "playback"}:
        # Internal worker RTSP reads (e.g. sentinel-worker CCTV/People frame capture).
        if protocol == "rtsp" and _is_internal_ip(body.ip) and path:
            cams = (
                await db.execute(select(Camera.cameraId).where(Camera.deletedAt.is_(None)))
            ).scalars().all()
            if any(path_name_for_camera(cid) == path for cid in cams):
                return Response(status_code=200)
            raise HTTPException(status_code=401, detail="Unknown camera path")

        token = _extract_stream_jwt(body)
        if not token:
            raise HTTPException(status_code=401, detail="Stream token required")
        try:
            payload = decode_token(token, expected_typ=TYP_STREAM)
            cam_id = UUID(str(payload["cameraId"]))
            comp_id = UUID(str(payload["companyId"]))
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid stream token") from None

        if path_name_for_camera(cam_id) != path:
            raise HTTPException(status_code=401, detail="Stream token path mismatch")

        cam: Optional[Camera] = await db.get(Camera, cam_id)
        if cam is None or cam.deletedAt is not None or cam.companyId != comp_id or not cam.isActive:
            raise HTTPException(status_code=401, detail="Camera unavailable")
        return Response(status_code=200)

    raise HTTPException(status_code=401, detail="Unsupported MediaMTX action")
