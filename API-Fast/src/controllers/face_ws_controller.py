"""WebSocket kiosk stream: identify + walk-by check-in via GPU queue."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import uuid
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, List, Optional
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.exceptions import HTTPException

from ..config.database import async_session
from ..controllers.face_controller import (
    _enrich_face_core_match,
    _face_core_identify,
    _finalize_check_in,
    _resolve_match_response,
)
from ..clients.face_core_client import face_core_enabled, get_face_core_client
from ..utils.face_engine import (
    detect_faces_bytes,
    extract_face_features,
    get_walkby_encoding,
)
from ..utils.face_gpu_queue import face_gpu_queue_stats, run_on_face_gpu

logger = logging.getLogger(__name__)
_bff_pending_value = 0
_bff_pending_at = 0.0


async def _bff_pending() -> int:
    """Cached Face Core queue depth so detect frames do not each call queue-stats."""
    global _bff_pending_value, _bff_pending_at
    import time

    now = time.monotonic()
    if now - _bff_pending_at < 2:
        return _bff_pending_value
    try:
        stats = await get_face_core_client().queue_stats()
        pending = stats.get("pending")
        if pending is None and isinstance(stats.get("pendingByCompany"), dict):
            pending = sum(int(v or 0) for v in stats["pendingByCompany"].values())
        _bff_pending_value = int(pending or 0)
    except Exception:
        _bff_pending_value = int(settings_backpressure())
    _bff_pending_at = now
    return _bff_pending_value


def settings_backpressure() -> int:
    from ..config.settings import settings

    return int(settings.WS_QUEUE_BACKPRESSURE)
TEMP_DIR = Path("temp_images")


async def _face_core_queue_stats(company_id: Optional[UUID] = None) -> dict:
    if not face_core_enabled():
        return face_gpu_queue_stats()
    client = get_face_core_client()
    code = str(company_id) if company_id else None
    stats = await client.queue_stats(code)
    return {"source": "face-core", **stats}


async def face_core_queue_stats_route(company_id: Optional[UUID] = None) -> dict:
    return await _face_core_queue_stats(company_id)


def _json_default(obj: Any):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, Enum):
        return obj.value
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


async def _send(ws: WebSocket, payload: dict, *, lock: Optional[asyncio.Lock] = None) -> None:
    text = json.dumps(payload, default=_json_default)
    if lock is None:
        await ws.send_text(text)
        return
    async with lock:
        await ws.send_text(text)


def _decode_image_b64(raw: str) -> bytes:
    data = (raw or "").strip()
    if "," in data and data.lower().startswith("data:"):
        data = data.split(",", 1)[1]
    return base64.b64decode(data)


def _write_temp_bytes(content: bytes, suffix: str = ".jpg") -> str:
    TEMP_DIR.mkdir(exist_ok=True)
    path = TEMP_DIR / f"{uuid.uuid4()}{suffix}"
    path.write_bytes(content)
    return str(path)


def _cleanup(paths: List[str]) -> None:
    for p in paths:
        try:
            Path(p).unlink(missing_ok=True)
        except OSError:
            pass


async def _handle_detect(
    websocket: WebSocket,
    *,
    request_id: Any,
    image_b64: str,
    send_lock: asyncio.Lock,
) -> None:
    """Detection-only pass for kiosk face boxes (no temp files, no DB)."""
    try:
        from ..config.settings import settings
        from ..utils.face_gpu_queue import face_gpu_queue_stats

        if face_core_enabled():
            from ..clients.face_core_client import face_core_circuit_open

            if face_core_circuit_open():
                await _send(
                    websocket,
                    {
                        "type": "error",
                        "intent": "detect",
                        "requestId": request_id,
                        "code": "face_core_down",
                        "detail": "face_core_down",
                    },
                    lock=send_lock,
                )
                return
            pending = await _bff_pending()
            if pending >= int(settings.WS_QUEUE_BACKPRESSURE):
                await _send(
                    websocket,
                    {
                        "type": "detected",
                        "requestId": request_id,
                        "dropped": True,
                        "queue": {"pending": pending, "source": "face-core"},
                        "frameWidth": 0,
                        "frameHeight": 0,
                        "faces": [],
                    },
                    lock=send_lock,
                )
                return
        else:
            queue = face_gpu_queue_stats()
            if int(queue.get("pending") or 0) >= int(settings.WS_QUEUE_BACKPRESSURE):
                await _send(
                    websocket,
                    {
                        "type": "detected",
                        "requestId": request_id,
                        "dropped": True,
                        "queue": queue,
                        "frameWidth": 0,
                        "frameHeight": 0,
                        "faces": [],
                    },
                    lock=send_lock,
                )
                return
        content = _decode_image_b64(image_b64)
        if face_core_enabled():
            client = get_face_core_client()
            result = await client.detect(content)
            queue = await _face_core_queue_stats()
        else:
            result = await run_on_face_gpu(lambda c=content: detect_faces_bytes(c))
            queue = face_gpu_queue_stats()
        await _send(
            websocket,
            {
                "type": "detected",
                "requestId": request_id,
                "queue": queue,
                **result,
            },
            lock=send_lock,
        )
    except Exception as exc:
        logger.warning("WS detect failed: %s", exc)
        try:
            await _send(
                websocket,
                {
                    "type": "error",
                    "intent": "detect",
                    "requestId": request_id,
                    "detail": str(exc),
                },
                lock=send_lock,
            )
        except Exception:
            pass


async def _handle_identify(
    websocket: WebSocket,
    *,
    track_id: Any,
    request_id: Any,
    image_b64: str,
    company_id: UUID,
    send_lock: asyncio.Lock,
) -> None:
    paths: List[str] = []
    try:
        paths.append(_write_temp_bytes(_decode_image_b64(image_b64)))
        async with async_session() as db:
            if face_core_enabled():
                fc = await _face_core_identify(company_id, paths, "fast")
                payload = await _enrich_face_core_match(db, company_id, fc)
                queue = await _face_core_queue_stats(company_id)
            else:
                features = await run_on_face_gpu(
                    lambda p=paths[0]: extract_face_features(p, require_quality=False)
                )
                if features is None:
                    await _send(
                        websocket,
                        {
                            "type": "error",
                            "intent": "identify",
                            "trackId": track_id,
                            "requestId": request_id,
                            "detail": "No face detected in the image.",
                        },
                        lock=send_lock,
                    )
                    return

                encoding, _bbox = features
                payload = await _resolve_match_response(
                    db,
                    encoding,
                    liveness_passed=False,
                    companyId=company_id,
                )
                queue = face_gpu_queue_stats()
        await _send(
            websocket,
            {
                "type": "identified",
                "trackId": track_id,
                "requestId": request_id,
                "queue": queue,
                **payload,
            },
            lock=send_lock,
        )
    except HTTPException as he:
        await _send(
            websocket,
            {
                "type": "error",
                "intent": "identify",
                "trackId": track_id,
                "requestId": request_id,
                "detail": he.detail,
                "status": he.status_code,
            },
            lock=send_lock,
        )
    except Exception as exc:
        logger.exception("WS identify failed")
        await _send(
            websocket,
            {
                "type": "error",
                "intent": "identify",
                "trackId": track_id,
                "requestId": request_id,
                "detail": str(exc),
            },
            lock=send_lock,
        )
    finally:
        _cleanup(paths)


async def _handle_checkin(
    websocket: WebSocket,
    *,
    track_id: Any,
    request_id: Any,
    images_b64: List[str],
    company_id: UUID,
    latitude: float,
    longitude: float,
    note: Optional[str],
    send_lock: asyncio.Lock,
) -> None:
    paths: List[str] = []
    try:
        if not images_b64:
            await _send(
                websocket,
                {
                    "type": "error",
                    "intent": "checkin",
                    "trackId": track_id,
                    "requestId": request_id,
                    "detail": "No images provided",
                },
                lock=send_lock,
            )
            return

        for raw in images_b64[:3]:
            paths.append(_write_temp_bytes(_decode_image_b64(raw)))

        mid_path = paths[len(paths) // 2]

        async with async_session() as db:
            if face_core_enabled():
                fc = await _face_core_identify(company_id, paths, "walkby")
                match_payload = await _enrich_face_core_match(db, company_id, fc)
                result = await _finalize_check_in(
                    db=db,
                    companyId=company_id,
                    latitude=latitude,
                    longitude=longitude,
                    note=note,
                    match_payload=match_payload,
                    photo_source_path=mid_path,
                    liveness_passed=False,
                    mode="walkby-ws",
                    default_note="Face kiosk websocket walk-by",
                )
                queue = await _face_core_queue_stats(company_id)
            else:
                encoding = await run_on_face_gpu(
                    lambda ps=list(paths): get_walkby_encoding(ps)
                )
                result = await _finalize_check_in(
                    db=db,
                    companyId=company_id,
                    latitude=latitude,
                    longitude=longitude,
                    note=note,
                    target_encoding=encoding,
                    photo_source_path=mid_path,
                    liveness_passed=False,
                    mode="walkby-ws",
                    default_note="Face kiosk websocket walk-by",
                )
                queue = face_gpu_queue_stats()

        await _send(
            websocket,
            {
                "type": "checked_in",
                "trackId": track_id,
                "requestId": request_id,
                "queue": queue,
                **result,
            },
            lock=send_lock,
        )
    except HTTPException as he:
        await _send(
            websocket,
            {
                "type": "error",
                "intent": "checkin",
                "trackId": track_id,
                "requestId": request_id,
                "detail": he.detail,
                "status": he.status_code,
            },
            lock=send_lock,
        )
    except Exception as exc:
        logger.exception("WS checkin failed")
        await _send(
            websocket,
            {
                "type": "error",
                "intent": "checkin",
                "trackId": track_id,
                "requestId": request_id,
                "detail": str(exc),
            },
            lock=send_lock,
        )
    finally:
        _cleanup(paths)


async def kiosk_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    company_id: Optional[UUID] = None
    latitude = 0.0
    longitude = 0.0
    send_lock = asyncio.Lock()
    token_exp = 0
    token_warned = False

    await _send(
        websocket,
        {
            "type": "ready",
            "message": "Send session then identify/checkin frames",
            "faceCoreEnabled": face_core_enabled(),
            "queue": await _face_core_queue_stats(),
        },
        lock=send_lock,
    )

    try:
        while True:
            import time as _time

            if token_exp and not token_warned and token_exp - _time.time() < 300:
                token_warned = True
                await _send(websocket, {"type": "token_expiring"}, lock=send_lock)
            message = await websocket.receive_text()
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                await _send(websocket, {"type": "error", "detail": "Invalid JSON"})
                continue

            msg_type = data.get("type")

            if msg_type == "ping":
                await _send(
                    websocket,
                    {
                        "type": "pong",
                        "queue": await _face_core_queue_stats(company_id),
                    },
                )
                continue

            if msg_type == "session":
                try:
                    company_id = UUID(str(data["companyId"]))
                    latitude = float(data.get("latitude", 0) or 0)
                    longitude = float(data.get("longitude", 0) or 0)
                    from ..config.settings import settings as _settings
                    if _settings.FACE_ROUTES_REQUIRE_JWT:
                        from ..config.database import async_session
                        from ..security.deps import assert_company_access, member_from_token

                        token = str(data.get("token") or "")
                        async with async_session() as db:
                            member = await member_from_token(token, db)
                            await assert_company_access(db, member, company_id)
                        from ..security.jwt import decode_token

                        token_exp = int(decode_token(token).get("exp") or 0)
                        token_warned = False
                except Exception as exc:
                    await _send(
                        websocket,
                        {"type": "error", "detail": getattr(exc, "detail", None) or "Invalid session payload"},
                    )
                    continue
                await _send(
                    websocket,
                    {
                        "type": "session_ok",
                        "companyId": str(company_id),
                        "companyCode": str(company_id),
                        "queue": await _face_core_queue_stats(company_id),
                    },
                )
                continue

            if msg_type == "detect":
                asyncio.create_task(
                    _handle_detect(
                        websocket,
                        request_id=data.get("requestId"),
                        image_b64=str(data.get("image") or ""),
                        send_lock=send_lock,
                    )
                )
                continue

            if msg_type == "identify":
                if company_id is None:
                    await _send(
                        websocket,
                        {
                            "type": "error",
                            "intent": "identify",
                            "trackId": data.get("trackId"),
                            "requestId": data.get("requestId"),
                            "detail": "Session not started",
                        },
                        lock=send_lock,
                    )
                    continue
                asyncio.create_task(
                    _handle_identify(
                        websocket,
                        track_id=data.get("trackId"),
                        request_id=data.get("requestId"),
                        image_b64=str(data.get("image") or ""),
                        company_id=company_id,
                        send_lock=send_lock,
                    )
                )
                continue

            if msg_type == "checkin":
                if company_id is None:
                    await _send(
                        websocket,
                        {
                            "type": "error",
                            "intent": "checkin",
                            "trackId": data.get("trackId"),
                            "requestId": data.get("requestId"),
                            "detail": "Session not started",
                        },
                        lock=send_lock,
                    )
                    continue
                images = data.get("images") or []
                if not images and data.get("image"):
                    images = [data.get("image")]
                if data.get("latitude") is not None:
                    latitude = float(data.get("latitude") or 0)
                if data.get("longitude") is not None:
                    longitude = float(data.get("longitude") or 0)
                if abs(latitude) < 1e-6 and abs(longitude) < 1e-6:
                    await _send(
                        websocket,
                        {
                            "type": "error",
                            "intent": "checkin",
                            "trackId": data.get("trackId"),
                            "requestId": data.get("requestId"),
                            "detail": "Invalid GPS (0,0). Enable location / use HTTPS before check-in.",
                        },
                        lock=send_lock,
                    )
                    continue
                asyncio.create_task(
                    _handle_checkin(
                        websocket,
                        track_id=data.get("trackId"),
                        request_id=data.get("requestId"),
                        images_b64=[str(x) for x in images],
                        company_id=company_id,
                        latitude=latitude,
                        longitude=longitude,
                        note=data.get("note"),
                        send_lock=send_lock,
                    )
                )
                continue

            await _send(
                websocket,
                {"type": "error", "detail": f"Unknown message type: {msg_type}"},
            )

    except WebSocketDisconnect:
        logger.info("Kiosk websocket disconnected")
    except Exception as exc:
        logger.exception("Kiosk websocket error: %s", exc)
        try:
            await _send(websocket, {"type": "error", "detail": str(exc)})
        except Exception:
            pass
