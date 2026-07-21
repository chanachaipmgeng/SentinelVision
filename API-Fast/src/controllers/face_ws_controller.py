"""WebSocket kiosk stream: identify + walk-by check-in via GPU queue."""

from __future__ import annotations

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
from ..controllers.face_controller import _finalize_check_in, _resolve_match_response
from ..utils.face_engine import extract_face_features, get_walkby_encoding
from ..utils.face_gpu_queue import face_gpu_queue_stats, run_on_face_gpu

logger = logging.getLogger(__name__)
TEMP_DIR = Path("temp_images")


def _json_default(obj: Any):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, Enum):
        return obj.value
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


async def _send(ws: WebSocket, payload: dict) -> None:
    await ws.send_text(json.dumps(payload, default=_json_default))


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


async def _handle_identify(
    websocket: WebSocket,
    *,
    track_id: Any,
    request_id: Any,
    image_b64: str,
) -> None:
    paths: List[str] = []
    try:
        paths.append(_write_temp_bytes(_decode_image_b64(image_b64)))
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
            )
            return

        encoding, _bbox = features
        async with async_session() as db:
            payload = await _resolve_match_response(
                db, encoding, liveness_passed=False
            )
        await _send(
            websocket,
            {
                "type": "identified",
                "trackId": track_id,
                "requestId": request_id,
                "queue": face_gpu_queue_stats(),
                **payload,
            },
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
            )
            return

        for raw in images_b64[:3]:
            paths.append(_write_temp_bytes(_decode_image_b64(raw)))

        encoding = await run_on_face_gpu(lambda ps=list(paths): get_walkby_encoding(ps))
        mid_path = paths[len(paths) // 2]

        async with async_session() as db:
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

        await _send(
            websocket,
            {
                "type": "checked_in",
                "trackId": track_id,
                "requestId": request_id,
                "queue": face_gpu_queue_stats(),
                **result,
            },
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
        )
    finally:
        _cleanup(paths)


async def kiosk_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    company_id: Optional[UUID] = None
    latitude = 0.0
    longitude = 0.0

    await _send(
        websocket,
        {
            "type": "ready",
            "message": "Send session then identify/checkin frames",
            "queue": face_gpu_queue_stats(),
        },
    )

    try:
        while True:
            message = await websocket.receive_text()
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                await _send(websocket, {"type": "error", "detail": "Invalid JSON"})
                continue

            msg_type = data.get("type")

            if msg_type == "ping":
                await _send(
                    websocket, {"type": "pong", "queue": face_gpu_queue_stats()}
                )
                continue

            if msg_type == "session":
                try:
                    company_id = UUID(str(data["companyId"]))
                    latitude = float(data.get("latitude", 0) or 0)
                    longitude = float(data.get("longitude", 0) or 0)
                except Exception:
                    await _send(
                        websocket,
                        {"type": "error", "detail": "Invalid session payload"},
                    )
                    continue
                await _send(
                    websocket,
                    {
                        "type": "session_ok",
                        "companyId": str(company_id),
                        "queue": face_gpu_queue_stats(),
                    },
                )
                continue

            if msg_type == "identify":
                await _handle_identify(
                    websocket,
                    track_id=data.get("trackId"),
                    request_id=data.get("requestId"),
                    image_b64=str(data.get("image") or ""),
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
                    )
                    continue
                images = data.get("images") or []
                if not images and data.get("image"):
                    images = [data.get("image")]
                # Refresh geo from message if provided
                if data.get("latitude") is not None:
                    latitude = float(data.get("latitude") or 0)
                if data.get("longitude") is not None:
                    longitude = float(data.get("longitude") or 0)
                await _handle_checkin(
                    websocket,
                    track_id=data.get("trackId"),
                    request_id=data.get("requestId"),
                    images_b64=[str(x) for x in images],
                    company_id=company_id,
                    latitude=latitude,
                    longitude=longitude,
                    note=data.get("note"),
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
