"""MediaMTX Control API helpers — sync pull paths for live wall (Phase 3)."""

from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

import httpx

from ..config.settings import settings

logger = logging.getLogger(__name__)


def path_name_for_camera(camera_id: UUID) -> str:
    """Stable MediaMTX path name (no dashes — safer in some clients)."""
    return str(camera_id).replace("-", "")


def whep_path(camera_id: UUID) -> str:
    base = (settings.MEDIAMTX_WHEP_BASE_PATH or "/mediamtx").rstrip("/")
    return f"{base}/{path_name_for_camera(camera_id)}/whep"


def hls_path(camera_id: UUID) -> str:
    base = (settings.MEDIAMTX_HLS_BASE_PATH or "/mediamtx-hls").rstrip("/")
    return f"{base}/{path_name_for_camera(camera_id)}/index.m3u8"


def _api_base() -> str:
    return (settings.MEDIAMTX_API_URL or "http://mediamtx:9997").rstrip("/")


def _enabled() -> bool:
    return bool(getattr(settings, "MEDIAMTX_ENABLED", True))


async def upsert_pull_path(
    camera_id: UUID,
    *,
    source_url: str,
    record: bool = False,
) -> dict[str, Any]:
    """Create or patch a MediaMTX path that pulls from an RTSP/HTTP source."""
    if not _enabled():
        return {"ok": False, "skipped": True, "reason": "mediamtx_disabled"}

    name = path_name_for_camera(camera_id)
    body: dict[str, Any] = {
        "name": name,
        "source": source_url,
        "sourceOnDemand": True,
        "sourceOnDemandStartTimeout": "10s",
        "sourceOnDemandCloseAfter": "30s",
        "record": bool(record),
    }
    if record:
        body["recordPath"] = "/recordings/%path/%Y-%m-%d_%H-%M-%S-%f"

    timeout = httpx.Timeout(8.0, connect=3.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        # Prefer patch; if missing, add.
        patch = await client.patch(f"{_api_base()}/v3/config/paths/patch/{name}", json=body)
        if patch.status_code == 404:
            add = await client.post(f"{_api_base()}/v3/config/paths/add/{name}", json=body)
            if add.status_code >= 400:
                text = add.text[:300]
                logger.warning("MediaMTX add path %s failed: %s %s", name, add.status_code, text)
                return {"ok": False, "status": add.status_code, "error": text}
            return {"ok": True, "action": "add", "path": name}
        if patch.status_code >= 400:
            text = patch.text[:300]
            logger.warning("MediaMTX patch path %s failed: %s %s", name, patch.status_code, text)
            return {"ok": False, "status": patch.status_code, "error": text}
        return {"ok": True, "action": "patch", "path": name}


async def delete_path(camera_id: UUID) -> dict[str, Any]:
    if not _enabled():
        return {"ok": False, "skipped": True, "reason": "mediamtx_disabled"}
    name = path_name_for_camera(camera_id)
    timeout = httpx.Timeout(5.0, connect=2.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.delete(f"{_api_base()}/v3/config/paths/delete/{name}")
        if resp.status_code in (200, 404):
            return {"ok": True, "path": name, "status": resp.status_code}
        return {"ok": False, "status": resp.status_code, "error": resp.text[:300]}


async def path_ready(camera_id: UUID) -> Optional[bool]:
    """Best-effort readiness probe via Control API list."""
    if not _enabled():
        return None
    name = path_name_for_camera(camera_id)
    timeout = httpx.Timeout(4.0, connect=2.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(f"{_api_base()}/v3/paths/get/{name}")
            if resp.status_code == 404:
                return False
            if resp.status_code >= 400:
                return None
            data = resp.json()
            # ready / readers vary by version; treat 200 as present
            return bool(data)
    except (httpx.HTTPError, ValueError):
        return None
