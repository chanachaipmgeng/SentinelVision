"""WebSocket kiosk stream: identify + walk-by check-in via GPU queue (supports Member JWT and Kiosk Device Token).

Auth contract: the first message must be a valid ``session`` (within
``WS_KIOSK_AUTH_TIMEOUT_SECONDS``). Anything else before that closes the socket
with 1008 so unauthenticated clients can never reach the GPU queue.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
import uuid
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
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
from ..services.observability import ws_kiosk_connections
from ..utils.face_engine import (
    decode_image_bytes,
    detect_faces_bgr,
    extract_face_features_bgr,
    get_decode_executor,
    get_walkby_encoding_frames,
)
from ..utils.face_gpu_queue import StaleFaceJob, face_gpu_queue_stats, run_on_face_gpu

logger = logging.getLogger(__name__)
_bff_pending_value = 0
_bff_pending_at = 0.0

TEMP_DIR = Path("temp_images")


async def _bff_pending() -> int:
    """Cached Face Core queue depth so detect frames do not each call queue-stats."""
    global _bff_pending_value, _bff_pending_at

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


def _detect_interval_ms(pending: int) -> float:
    """Raise server-side detect floor when the GPU queue is backed up."""
    from ..config.settings import settings

    base = float(settings.WS_DETECT_MIN_INTERVAL_MS)
    if pending >= 32:
        return max(base, 800.0)
    if pending >= 8:
        return max(base, 500.0)
    return base


class _IdentifyCache:
    """Per-connection trackId → embedding reuse for walk-by check-in."""

    def __init__(self) -> None:
        self._items: Dict[str, Tuple[List[float], float]] = {}

    def put(self, track_id: Any, encoding: List[float]) -> None:
        self._items[str(track_id)] = (encoding, time.monotonic())

    def get(self, track_id: Any, *, max_age_s: float) -> Optional[List[float]]:
        key = str(track_id)
        item = self._items.get(key)
        if item is None:
            return None
        encoding, ts = item
        if time.monotonic() - ts > max_age_s:
            self._items.pop(key, None)
            return None
        return encoding


async def _handle_detect(
    websocket: WebSocket,
    *,
    request_id: Any,
    image_b64: str,
    company_id: Optional[UUID],
    send_lock: asyncio.Lock,
    last_detect_at: Dict[str, float],
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
        else:
            queue = face_gpu_queue_stats()
            pending = int(queue.get("pending") or 0)

        now = time.monotonic()
        min_ms = _detect_interval_ms(pending)
        last = last_detect_at.get("t", 0.0)
        if (now - last) * 1000.0 < min_ms:
            await _send(
                websocket,
                {
                    "type": "detected",
                    "requestId": request_id,
                    "dropped": True,
                    "queue": (
                        {"pending": pending, "source": "face-core"}
                        if face_core_enabled()
                        else face_gpu_queue_stats()
                    ),
                    "frameWidth": 0,
                    "frameHeight": 0,
                    "faces": [],
                },
                lock=send_lock,
            )
            return
        last_detect_at["t"] = now

        if pending >= int(settings.WS_QUEUE_BACKPRESSURE):
            await _send(
                websocket,
                {
                    "type": "detected",
                    "requestId": request_id,
                    "dropped": True,
                    "queue": (
                        {"pending": pending, "source": "face-core"}
                        if face_core_enabled()
                        else face_gpu_queue_stats()
                    ),
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
            queue = await _face_core_queue_stats(company_id)
        else:
            loop = asyncio.get_running_loop()
            try:
                image = await loop.run_in_executor(
                    get_decode_executor(),
                    lambda c=content: decode_image_bytes(c, for_detect=True),
                )
            except ValueError as exc:
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
                return
            try:
                result = await run_on_face_gpu(
                    lambda img=image: detect_faces_bgr(img),
                    kind="detect",
                    company_id=company_id,
                    stale_ms=float(settings.FACE_DETECT_STALE_MS),
                )
            except StaleFaceJob:
                await _send(
                    websocket,
                    {
                        "type": "detected",
                        "requestId": request_id,
                        "dropped": True,
                        "queue": face_gpu_queue_stats(),
                        "frameWidth": 0,
                        "frameHeight": 0,
                        "faces": [],
                    },
                    lock=send_lock,
                )
                return
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
    identify_cache: _IdentifyCache,
) -> None:
    paths: List[str] = []
    try:
        content = _decode_image_b64(image_b64)
        async with async_session() as db:
            if face_core_enabled():
                paths.append(_write_temp_bytes(content))
                fc = await _face_core_identify(company_id, paths, "fast")
                payload = await _enrich_face_core_match(db, company_id, fc)
                queue = await _face_core_queue_stats(company_id)
            else:
                from ..config.settings import settings

                loop = asyncio.get_running_loop()
                image = await loop.run_in_executor(
                    get_decode_executor(),
                    lambda c=content: decode_image_bytes(c),
                )
                features = await run_on_face_gpu(
                    lambda img=image: extract_face_features_bgr(
                        img,
                        require_quality=False,
                        fast_detect=bool(settings.FACE_FAST_EMBED_DETECT),
                    ),
                    kind="identify",
                    company_id=company_id,
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
                identify_cache.put(track_id, encoding)
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


async def _resolve_station_context(
    db,
    company_id: UUID,
    *,
    station_mode: Optional[str],
    zone_id: Optional[str],
    event_id: Optional[str],
) -> Tuple[str, Optional[str], Optional[str], dict]:
    """Merge session/checkin overrides with company module-config defaults."""
    from ..services.company_module_service import (
        VALID_STATION_MODES,
        get_company_module_config,
    )

    cfg = await get_company_module_config(db, company_id)
    mode = str(station_mode or cfg.get("defaultStationMode") or "ATTENDANCE").strip().upper()
    if mode not in VALID_STATION_MODES:
        mode = "ATTENDANCE"
    resolved_zone = zone_id or cfg.get("defaultZoneId")
    resolved_event = event_id or cfg.get("defaultEventId")
    return mode, resolved_zone, resolved_event, cfg


async def _maybe_attendance_door_relay(
    db,
    company_id: UUID,
    *,
    zone_id: Optional[str],
    rules: dict,
    subject_name: str,
    force: bool = False,
) -> bool:
    """Fire zone relay after attendance when enableDoorRelayOnAttendance or UNIFIED_HYBRID."""
    if not force and not bool((rules or {}).get("enableDoorRelayOnAttendance", False)):
        return False
    if not zone_id:
        return False
    from ..routes.sentinel_routes import maybe_dispatch_zone_relay, resolve_scan_zone

    zone, _ = await resolve_scan_zone(db, company_id, zone_id, "ACCESS_CONTROL")
    return await maybe_dispatch_zone_relay(
        zone, subject_name=subject_name or "Employee", identity_type="EMPLOYEE"
    )


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
    punch_type: Optional[str],
    station_mode: Optional[str],
    zone_id: Optional[str],
    event_id: Optional[str],
    totp_or_pin: Optional[str],
    send_lock: asyncio.Lock,
    identify_cache: _IdentifyCache,
) -> None:
    from ..config.settings import settings

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

        raw_list = list(images_b64[:3])
        contents = [_decode_image_b64(raw) for raw in raw_list]
        mid_bytes = contents[len(contents) // 2]

        async with async_session() as db:
            mode, resolved_zone, resolved_event, module_cfg = await _resolve_station_context(
                db,
                company_id,
                station_mode=station_mode,
                zone_id=zone_id,
                event_id=event_id,
            )
            rules = module_cfg.get("scanActionRules") or {}
            attendance_like = mode in ("ATTENDANCE", "UNIFIED_HYBRID")

            if attendance_like and face_core_enabled():
                for content in contents:
                    paths.append(_write_temp_bytes(content))
                mid_path = paths[len(paths) // 2]
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
                    punch_type=punch_type,
                )
                emp = result.get("employee") or {}
                subject = (
                    f"{emp.get('firstName') or ''} {emp.get('lastName') or ''}".strip()
                    or emp.get("username")
                    or "Employee"
                )
                relay_ok = await _maybe_attendance_door_relay(
                    db,
                    company_id,
                    zone_id=resolved_zone,
                    rules=rules,
                    subject_name=subject,
                    force=(mode == "UNIFIED_HYBRID"),
                )
                result = {
                    **result,
                    "stationMode": mode,
                    "doorRelayTriggered": relay_ok,
                    "accessGranted": True if result.get("checkedIn") or result.get("duplicate") else result.get("accessGranted"),
                }
                if mode == "UNIFIED_HYBRID":
                    result["decision"] = "ATTENDANCE_AND_ACCESS"
                queue = await _face_core_queue_stats(company_id)
            elif attendance_like:
                loop = asyncio.get_running_loop()
                frames = []
                for content in contents:
                    frame = await loop.run_in_executor(
                        get_decode_executor(),
                        lambda c=content: decode_image_bytes(c),
                    )
                    frames.append(frame)

                cached = identify_cache.get(
                    track_id,
                    max_age_s=float(settings.FACE_IDENTIFY_CACHE_SECONDS),
                )
                if cached is not None:
                    encoding = cached
                else:
                    encoding = await run_on_face_gpu(
                        lambda fs=list(frames): get_walkby_encoding_frames(fs),
                        kind="checkin",
                        company_id=company_id,
                    )
                result = await _finalize_check_in(
                    db=db,
                    companyId=company_id,
                    latitude=latitude,
                    longitude=longitude,
                    note=note,
                    target_encoding=encoding,
                    photo_source_bytes=mid_bytes,
                    liveness_passed=False,
                    mode="walkby-ws",
                    default_note="Face kiosk websocket walk-by",
                    punch_type=punch_type,
                )
                emp = result.get("employee") or {}
                subject = (
                    f"{emp.get('firstName') or ''} {emp.get('lastName') or ''}".strip()
                    or emp.get("username")
                    or "Employee"
                )
                relay_ok = await _maybe_attendance_door_relay(
                    db,
                    company_id,
                    zone_id=resolved_zone,
                    rules=rules,
                    subject_name=subject,
                    force=(mode == "UNIFIED_HYBRID"),
                )
                result = {
                    **result,
                    "stationMode": mode,
                    "doorRelayTriggered": relay_ok,
                }
                if mode == "UNIFIED_HYBRID":
                    result["decision"] = "ATTENDANCE_AND_ACCESS"
                    result["accessGranted"] = bool(
                        result.get("checkedIn") or result.get("duplicate") or relay_ok
                    )
                queue = face_gpu_queue_stats()
            else:
                # Non-attendance station modes: Decision Engine via sentinel helpers.
                from ..routes.sentinel_routes import evaluate_unified_scan_decision

                loop = asyncio.get_running_loop()
                frames = []
                for content in contents:
                    frame = await loop.run_in_executor(
                        get_decode_executor(),
                        lambda c=content: decode_image_bytes(c),
                    )
                    frames.append(frame)
                cached = identify_cache.get(
                    track_id,
                    max_age_s=float(settings.FACE_IDENTIFY_CACHE_SECONDS),
                )
                if cached is not None:
                    encoding = cached
                else:
                    encoding = await run_on_face_gpu(
                        lambda fs=list(frames): get_walkby_encoding_frames(fs),
                        kind="checkin",
                        company_id=company_id,
                    )
                if encoding is None:
                    raise HTTPException(status_code=400, detail="No face detected in the image.")
                result = await evaluate_unified_scan_decision(
                    db,
                    company_id,
                    encoding,
                    station_mode=mode,
                    zone_id=resolved_zone,
                    event_id=resolved_event,
                    totp_or_pin=totp_or_pin,
                    snapshot_url=None,
                    scan_action_rules=rules,
                )
                result = {**result, "stationMode": mode}
                queue = (
                    await _face_core_queue_stats(company_id)
                    if face_core_enabled()
                    else face_gpu_queue_stats()
                )

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


async def _run_bounded(sem: asyncio.Semaphore, coro) -> None:
    async with sem:
        await coro


# RFC 6455 close code for "policy violation" — used for every auth/limit rejection.
WS_CLOSE_POLICY_VIOLATION = 1008

# Per-process connection registry (keyed by client IP / companyId). Each API replica
# counts only its own sockets; nginx `limit_conn` on /face/ws/ is the gateway-wide cap.
_conn_by_ip: Dict[str, int] = {}
_conn_by_company: Dict[str, int] = {}


def _acquire_slot(table: Dict[str, int], key: str, limit: int) -> bool:
    current = table.get(key, 0)
    if limit > 0 and current >= limit:
        return False
    table[key] = current + 1
    return True


def _release_slot(table: Dict[str, int], key: str) -> None:
    remaining = table.get(key, 0) - 1
    if remaining <= 0:
        table.pop(key, None)
    else:
        table[key] = remaining


def kiosk_ws_connection_counts() -> Dict[str, Dict[str, int]]:
    """Snapshot of live kiosk sockets per IP and per company (this process only)."""
    return {"byIp": dict(_conn_by_ip), "byCompany": dict(_conn_by_company)}


def _client_ip(websocket: WebSocket) -> str:
    # nginx sets X-Real-IP from $remote_addr (after realip recovery behind a TLS edge).
    # X-Forwarded-For is only consulted as a fallback; both are trusted only because
    # the API port is not published outside the compose network.
    real_ip = (websocket.headers.get("x-real-ip") or "").strip()
    if real_ip:
        return real_ip
    forwarded = (websocket.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    if forwarded:
        return forwarded
    client = websocket.client
    return client.host if client and client.host else "unknown"


async def _reject(
    websocket: WebSocket,
    *,
    code: str,
    detail: str,
    send_lock: Optional[asyncio.Lock] = None,
) -> None:
    """Send a final error frame, then close with 1008 so the client knows not to retry blindly."""
    try:
        await _send(
            websocket, {"type": "error", "code": code, "detail": detail}, lock=send_lock
        )
    except Exception:
        pass
    try:
        await websocket.close(code=WS_CLOSE_POLICY_VIOLATION, reason=code)
    except Exception:
        pass


async def _authenticate_session(data: dict) -> Tuple[UUID, int, Optional[UUID]]:
    """Resolve (companyId, token_exp, kiosk_device_id) from a `session` payload."""
    from ..config.settings import settings as _settings

    raw_cid = data.get("companyId")
    if not _settings.FACE_ROUTES_REQUIRE_JWT:
        return UUID(str(raw_cid)), 0, None

    from ..config.database import async_session as _async_session
    from ..security.deps import (
        assert_company_access,
        member_from_token,
        verify_kiosk_token_db,
    )
    from ..security.jwt import decode_token
    from ..services.token_revocation_service import is_token_revoked

    token = str(data.get("token") or "")
    decoded = decode_token(token, expected_typ=None)
    if await is_token_revoked(decoded):
        raise HTTPException(status_code=401, detail="Token has been revoked")
    token_exp = int(decoded.get("exp") or 0)
    if token_exp and time.time() > token_exp:
        raise HTTPException(status_code=401, detail="Token has expired")
    async with _async_session() as db:
        if decoded.get("typ") == "kiosk":
            device = await verify_kiosk_token_db(token, db)
            if raw_cid and UUID(str(raw_cid)) != device.companyId:
                raise HTTPException(status_code=403, detail="Kiosk token companyId mismatch")
            # Bind device stationMode/zoneId from provisioned device when session omits them.
            return device.companyId, token_exp, device.deviceId
        company_id = UUID(str(raw_cid))
        member = await member_from_token(token, db)
        await assert_company_access(db, member, company_id)
        return company_id, token_exp, None


async def kiosk_websocket(websocket: WebSocket) -> None:
    from ..config.settings import settings as _settings

    client_ip = _client_ip(websocket)
    max_per_ip = int(_settings.WS_KIOSK_MAX_CONN_PER_IP)
    max_per_company = int(_settings.WS_KIOSK_MAX_CONN_PER_COMPANY)
    auth_timeout = float(_settings.WS_KIOSK_AUTH_TIMEOUT_SECONDS)

    if not _acquire_slot(_conn_by_ip, client_ip, max_per_ip):
        await websocket.accept()
        logger.warning("Kiosk websocket rejected: per-IP limit (%s) reached for %s", max_per_ip, client_ip)
        await _reject(
            websocket,
            code="too_many_connections",
            detail=f"Too many kiosk connections from this address (limit {max_per_ip})",
        )
        return

    await websocket.accept()
    ws_kiosk_connections.inc()
    company_id: Optional[UUID] = None
    company_key: Optional[str] = None
    authenticated = False
    auth_deadline = time.monotonic() + auth_timeout
    latitude = 0.0
    longitude = 0.0
    session_station_mode: Optional[str] = None
    session_zone_id: Optional[str] = None
    session_event_id: Optional[str] = None
    session_totp_or_pin: Optional[str] = None
    kiosk_device_id: Optional[UUID] = None
    send_lock = asyncio.Lock()
    task_sem = asyncio.Semaphore(4)
    token_exp = 0
    token_warned = False
    last_detect_at: Dict[str, float] = {"t": 0.0}
    identify_cache = _IdentifyCache()

    try:
        await _send(
            websocket,
            {
                "type": "ready",
                "message": "Send session then identify/checkin frames",
                "faceCoreEnabled": face_core_enabled(),
                "authTimeoutSeconds": auth_timeout,
                "queue": await _face_core_queue_stats(),
            },
            lock=send_lock,
        )

        while True:
            if token_exp and not token_warned and token_exp - time.time() < 300:
                token_warned = True
                await _send(websocket, {"type": "token_expiring"}, lock=send_lock)

            if authenticated:
                message = await websocket.receive_text()
            else:
                remaining = auth_deadline - time.monotonic()
                if remaining <= 0:
                    await _reject(
                        websocket,
                        code="auth_timeout",
                        detail=f"No valid session within {auth_timeout:g}s",
                        send_lock=send_lock,
                    )
                    return
                try:
                    message = await asyncio.wait_for(
                        websocket.receive_text(), timeout=remaining
                    )
                except asyncio.TimeoutError:
                    await _reject(
                        websocket,
                        code="auth_timeout",
                        detail=f"No valid session within {auth_timeout:g}s",
                        send_lock=send_lock,
                    )
                    return

            try:
                data = json.loads(message)
                if not isinstance(data, dict):
                    raise json.JSONDecodeError("expected object", message, 0)
            except json.JSONDecodeError:
                if not authenticated:
                    await _reject(
                        websocket,
                        code="unauthenticated",
                        detail="Send a valid session message first",
                        send_lock=send_lock,
                    )
                    return
                await _send(websocket, {"type": "error", "detail": "Invalid JSON"}, lock=send_lock)
                continue

            msg_type = data.get("type")

            if msg_type == "session":
                try:
                    latitude = float(data.get("latitude", 0) or 0)
                    longitude = float(data.get("longitude", 0) or 0)
                    if data.get("stationMode") is not None:
                        session_station_mode = str(data.get("stationMode") or "").strip().upper() or None
                    if data.get("zoneId") is not None:
                        session_zone_id = str(data.get("zoneId") or "").strip() or None
                    if data.get("eventId") is not None:
                        session_event_id = str(data.get("eventId") or "").strip() or None
                    if data.get("totpOrPin") is not None:
                        session_totp_or_pin = str(data.get("totpOrPin") or "").strip() or None
                    new_company_id, new_token_exp, new_device_id = await _authenticate_session(data)
                except Exception as exc:
                    detail = getattr(exc, "detail", None) or "Invalid session payload"
                    if not authenticated:
                        await _reject(
                            websocket,
                            code="invalid_session",
                            detail=str(detail),
                            send_lock=send_lock,
                        )
                        return
                    await _send(
                        websocket,
                        {"type": "error", "code": "invalid_session", "detail": str(detail)},
                        lock=send_lock,
                    )
                    continue

                new_key = str(new_company_id)
                if new_key != company_key:
                    if not _acquire_slot(_conn_by_company, new_key, max_per_company):
                        logger.warning(
                            "Kiosk websocket rejected: per-company limit (%s) reached for %s",
                            max_per_company,
                            new_key,
                        )
                        await _reject(
                            websocket,
                            code="too_many_connections",
                            detail=(
                                "Too many kiosk connections for this company "
                                f"(limit {max_per_company})"
                            ),
                            send_lock=send_lock,
                        )
                        return
                    if company_key is not None:
                        _release_slot(_conn_by_company, company_key)
                    company_key = new_key

                company_id = new_company_id
                token_exp = new_token_exp
                kiosk_device_id = new_device_id
                token_warned = False
                authenticated = True
                # Apply provisioned stationMode/zoneId when session omitted them.
                if kiosk_device_id is not None and (
                    session_station_mode is None or session_zone_id is None
                ):
                    try:
                        from ..config.database import async_session as _async_session
                        from ..models.hr_schedule import KioskDevice

                        async with _async_session() as db:
                            device = await db.get(KioskDevice, kiosk_device_id)
                            if device is not None:
                                if session_station_mode is None and device.stationMode:
                                    session_station_mode = device.stationMode
                                if session_zone_id is None and device.zoneId:
                                    session_zone_id = str(device.zoneId)
                    except Exception:
                        logger.exception("failed to load device station binding")
                await _send(
                    websocket,
                    {
                        "type": "session_ok",
                        "companyId": str(company_id),
                        "companyCode": str(company_id),
                        "deviceId": str(kiosk_device_id) if kiosk_device_id else None,
                        "stationMode": session_station_mode,
                        "zoneId": session_zone_id,
                        "queue": await _face_core_queue_stats(company_id),
                    },
                    lock=send_lock,
                )
                continue

            if not authenticated:
                await _reject(
                    websocket,
                    code="unauthenticated",
                    detail=f"Message '{msg_type}' rejected: send session first",
                    send_lock=send_lock,
                )
                return

            if msg_type == "heartbeat":
                if kiosk_device_id is None or company_id is None:
                    await _send(
                        websocket,
                        {
                            "type": "error",
                            "code": "heartbeat_unsupported",
                            "detail": "Heartbeat requires a paired kiosk device session",
                        },
                        lock=send_lock,
                    )
                    continue
                try:
                    from ..config.database import async_session as _async_session
                    from ..services import device_service as _device_svc

                    async with _async_session() as db:
                        row = await _device_svc.record_heartbeat(
                            db,
                            company_id,
                            kiosk_device_id,
                            {
                                "fingerprint": data.get("fingerprint"),
                                "appVersion": data.get("appVersion"),
                                "config": data.get("config") if isinstance(data.get("config"), dict) else None,
                            },
                        )
                    await _send(
                        websocket,
                        {
                            "type": "heartbeat_ok",
                            "deviceId": row["deviceId"],
                            "heartbeatAt": row.get("heartbeatAt").isoformat()
                            if row.get("heartbeatAt")
                            else None,
                        },
                        lock=send_lock,
                    )
                except Exception as exc:
                    detail = getattr(exc, "detail", None) or str(exc)
                    await _send(
                        websocket,
                        {"type": "error", "code": "heartbeat_failed", "detail": str(detail)},
                        lock=send_lock,
                    )
                continue

            if msg_type == "ping":
                await _send(
                    websocket,
                    {
                        "type": "pong",
                        "queue": await _face_core_queue_stats(company_id),
                    },
                    lock=send_lock,
                )
                continue

            if token_exp and time.time() > token_exp:
                await _send(
                    websocket,
                    {
                        "type": "error",
                        "code": "token_expired",
                        "detail": "Session token expired. Please send a fresh session token.",
                    },
                    lock=send_lock,
                )
                continue

            if msg_type == "detect":
                if task_sem.locked():
                    await _send(
                        websocket,
                        {
                            "type": "detected",
                            "requestId": data.get("requestId"),
                            "dropped": True,
                            "frameWidth": 0,
                            "frameHeight": 0,
                            "faces": [],
                        },
                        lock=send_lock,
                    )
                    continue
                asyncio.create_task(
                    _run_bounded(
                        task_sem,
                        _handle_detect(
                            websocket,
                            request_id=data.get("requestId"),
                            image_b64=str(data.get("image") or ""),
                            company_id=company_id,
                            send_lock=send_lock,
                            last_detect_at=last_detect_at,
                        ),
                    )
                )
                continue

            if msg_type == "identify":
                asyncio.create_task(
                    _run_bounded(
                        task_sem,
                        _handle_identify(
                            websocket,
                            track_id=data.get("trackId"),
                            request_id=data.get("requestId"),
                            image_b64=str(data.get("image") or ""),
                            company_id=company_id,
                            send_lock=send_lock,
                            identify_cache=identify_cache,
                        ),
                    )
                )
                continue

            if msg_type == "checkin":
                images = data.get("images") or []
                if not images and data.get("image"):
                    images = [data.get("image")]
                if data.get("latitude") is not None:
                    latitude = float(data.get("latitude") or 0)
                if data.get("longitude") is not None:
                    longitude = float(data.get("longitude") or 0)
                checkin_mode = (
                    str(data.get("stationMode") or "").strip().upper()
                    if data.get("stationMode") is not None
                    else session_station_mode
                )
                # Non-attendance station modes may run without GPS (door / event / watchlist).
                mode_for_gps = checkin_mode or "ATTENDANCE"
                if mode_for_gps in ("ATTENDANCE", "UNIFIED_HYBRID") and abs(latitude) < 1e-6 and abs(longitude) < 1e-6:
                    await _send(
                        websocket,
                        {
                            "type": "error",
                            "intent": "checkin",
                            "trackId": data.get("trackId"),
                            "requestId": data.get("requestId"),
                            "detail": (
                                "Invalid GPS (0,0). Enable location / use HTTPS "
                                "before check-in."
                            ),
                        },
                        lock=send_lock,
                    )
                    continue
                checkin_zone = (
                    str(data.get("zoneId") or "").strip() or None
                    if data.get("zoneId") is not None
                    else session_zone_id
                )
                checkin_event = (
                    str(data.get("eventId") or "").strip() or None
                    if data.get("eventId") is not None
                    else session_event_id
                )
                checkin_totp = (
                    str(data.get("totpOrPin") or "").strip() or None
                    if data.get("totpOrPin") is not None
                    else session_totp_or_pin
                )
                asyncio.create_task(
                    _run_bounded(
                        task_sem,
                        _handle_checkin(
                            websocket,
                            track_id=data.get("trackId"),
                            request_id=data.get("requestId"),
                            images_b64=[str(x) for x in images],
                            company_id=company_id,
                            latitude=latitude,
                            longitude=longitude,
                            note=data.get("note"),
                            punch_type=data.get("punchType"),
                            station_mode=checkin_mode,
                            zone_id=checkin_zone,
                            event_id=checkin_event,
                            totp_or_pin=checkin_totp,
                            send_lock=send_lock,
                            identify_cache=identify_cache,
                        ),
                    )
                )
                continue

            await _send(
                websocket,
                {"type": "error", "detail": f"Unknown message type: {msg_type}"},
                lock=send_lock,
            )

    except WebSocketDisconnect:
        logger.info("Kiosk websocket disconnected")
    except Exception as exc:
        logger.exception("Kiosk websocket error: %s", exc)
        try:
            await _send(websocket, {"type": "error", "detail": str(exc)}, lock=send_lock)
        except Exception:
            pass
    finally:
        ws_kiosk_connections.dec()
        _release_slot(_conn_by_ip, client_ip)
        if company_key is not None:
            _release_slot(_conn_by_company, company_key)
