"""SEN-21 Phase 1: company module-config CRUD, kiosk allow-list, WS stationMode branches."""
from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, WebSocket
from starlette.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Avoid InsightFace/onnx at import time for WS unit tests (same as test_face_ws_auth_gating).
_mock_insight = MagicMock()
sys.modules.setdefault("insightface", _mock_insight)
sys.modules.setdefault("insightface.app", _mock_insight.app)
sys.modules.setdefault("onnxruntime", MagicMock())

from src.controllers import face_ws_controller as ws_mod  # noqa: E402
from src.security.jwt import create_access_token  # noqa: E402
from src.security.middleware import _is_kiosk_path_allowed  # noqa: E402
from src.services.company_module_service import (  # noqa: E402
    ALL_PLATFORM_MODULES,
    DEFAULT_COMPANY_MODULE_CONFIG,
    TOGGLEABLE_COMPANY_MODULES,
    VALID_STATION_MODES,
    merge_module_config,
    modules_config_key,
    normalize_module_config,
)


def test_module_constants_include_unified_hybrid():
    assert "CORE" in ALL_PLATFORM_MODULES
    assert "GOVERNANCE" in ALL_PLATFORM_MODULES
    assert set(TOGGLEABLE_COMPANY_MODULES) == {
        "ATTENDANCE",
        "ACCESS_CONTROL",
        "WATCHLIST",
        "VISITOR",
        "EVENTS",
        "CCTV",
    }
    assert "UNIFIED_HYBRID" in VALID_STATION_MODES
    assert DEFAULT_COMPANY_MODULE_CONFIG["defaultStationMode"] == "ATTENDANCE"
    assert DEFAULT_COMPANY_MODULE_CONFIG["scanActionRules"]["enableDoorRelayOnAttendance"] is False


def test_merge_module_config_defaults_and_always_on():
    merged = merge_module_config(None)
    assert merged["alwaysOnModules"] == ["CORE", "GOVERNANCE"]
    assert set(merged["enabledModules"]) == set(TOGGLEABLE_COMPANY_MODULES)
    assert merged["scanActionRules"]["unknownFaceAction"] == "IGNORE"
    assert modules_config_key("abc") == "modules:abc"

    partial = merge_module_config(
        {
            "enabledModules": ["ATTENDANCE", "EVENTS", "CORE"],
            "defaultStationMode": "EVENT_CHECKIN",
            "scanActionRules": {"enableDoorRelayOnAttendance": True},
        }
    )
    assert partial["enabledModules"] == ["ATTENDANCE", "EVENTS"]
    assert partial["defaultStationMode"] == "EVENT_CHECKIN"
    assert partial["scanActionRules"]["enableDoorRelayOnAttendance"] is True
    assert partial["scanActionRules"]["enableTtsVoice"] is True


def test_normalize_module_config_rejects_bad_mode_and_module():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as bad_mode:
        normalize_module_config({"defaultStationMode": "NOPE"})
    assert bad_mode.value.status_code == 400

    with pytest.raises(HTTPException) as bad_mod:
        normalize_module_config({"enabledModules": ["NOT_A_MODULE"]})
    assert bad_mod.value.status_code == 400

    clean = normalize_module_config(
        {
            "enabledModules": ["attendance", "WATCHLIST"],
            "defaultStationMode": "unified_hybrid",
            "defaultZoneId": None,
            "scanActionRules": {"unknownFaceAction": "log_incident"},
        }
    )
    assert clean["enabledModules"] == ["ATTENDANCE", "WATCHLIST"]
    assert clean["defaultStationMode"] == "UNIFIED_HYBRID"
    assert clean["scanActionRules"]["unknownFaceAction"] == "LOG_INCIDENT"
    assert "alwaysOnModules" not in clean


def test_kiosk_path_allows_module_config_and_events_get():
    cid = str(uuid.uuid4())
    assert _is_kiosk_path_allowed("GET", f"/sentinel/company/{cid}/module-config") is True
    assert _is_kiosk_path_allowed("PUT", f"/sentinel/company/{cid}/module-config") is False
    assert _is_kiosk_path_allowed("GET", f"/sentinel/company/{cid}/events") is True
    assert _is_kiosk_path_allowed("POST", f"/sentinel/company/{cid}/events") is False
    # Prior allow-list still holds
    assert _is_kiosk_path_allowed("POST", f"/sentinel/company/{cid}/scan") is True
    assert _is_kiosk_path_allowed("GET", f"/sentinel/company/{cid}/zones") is True
    assert _is_kiosk_path_allowed("GET", f"/sentinel/company/{cid}/edge-sync") is True
    assert _is_kiosk_path_allowed("DELETE", f"/sentinel/company/{cid}/identities/1") is False


@pytest.mark.skipif(
    not os.environ.get("DPU_TEST_DB_READY"),
    reason="No test database: set TEST_DATABASE_URL or `pip install pgserver`",
)
@pytest.mark.asyncio
async def test_module_config_http_crud_defaults_and_validation():
    from src.models.sentinel import SentinelAccessZone, SentinelEvent
    from src.routes import sentinel_routes
    from tests.support import build_app, client, seed_world, teardown_world

    world = await seed_world()
    app = build_app((sentinel_routes.router, "/sentinel"))
    cid = world.a.company_id
    try:
        async with client(app) as http:
            # Defaults with no stored row
            r = await http.get(
                f"/sentinel/company/{cid}/module-config",
                headers=world.auth("admin_a"),
            )
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["defaultStationMode"] == "ATTENDANCE"
            assert set(body["enabledModules"]) == set(TOGGLEABLE_COMPANY_MODULES)
            assert body["alwaysOnModules"] == ["CORE", "GOVERNANCE"]

            # Foreign company blocked
            denied = await http.get(
                f"/sentinel/company/{cid}/module-config",
                headers=world.auth("admin_b"),
            )
            assert denied.status_code == 403

            # Kiosk may GET module-config + events
            kiosk_get = await http.get(
                f"/sentinel/company/{cid}/module-config",
                headers=world.auth("kiosk_a"),
            )
            assert kiosk_get.status_code == 200
            kiosk_events = await http.get(
                f"/sentinel/company/{cid}/events",
                headers=world.auth("kiosk_a"),
            )
            assert kiosk_events.status_code == 200
            kiosk_put = await http.put(
                f"/sentinel/company/{cid}/module-config",
                headers=world.auth("kiosk_a"),
                json={"enabledModules": ["ATTENDANCE"]},
            )
            assert kiosk_put.status_code == 403

            # Create zone + event for validation
            from src.config.database import async_session

            zone_id = uuid.uuid4()
            event_id = uuid.uuid4()
            other_zone = uuid.uuid4()
            async with async_session() as db:
                db.add(
                    SentinelAccessZone(
                        zoneId=zone_id,
                        companyId=cid,
                        name="Lobby",
                        code="LOBBY",
                        stationMode="ACCESS_CONTROL",
                        isActive=True,
                    )
                )
                now = datetime.now(timezone.utc)
                db.add(
                    SentinelEvent(
                        eventId=event_id,
                        companyId=cid,
                        name="Town Hall",
                        startAt=now,
                        endAt=now,
                        status="LIVE",
                    )
                )
                db.add(
                    SentinelAccessZone(
                        zoneId=other_zone,
                        companyId=world.b.company_id,
                        name="Other",
                        code="OTHER",
                        stationMode="ACCESS_CONTROL",
                        isActive=True,
                    )
                )
                await db.commit()

            bad_zone = await http.put(
                f"/sentinel/company/{cid}/module-config",
                headers=world.auth("admin_a"),
                json={
                    "enabledModules": ["ATTENDANCE", "ACCESS_CONTROL"],
                    "defaultStationMode": "UNIFIED_HYBRID",
                    "defaultZoneId": str(other_zone),
                },
            )
            assert bad_zone.status_code == 400
            assert "defaultZoneId" in bad_zone.json()["detail"]

            ok = await http.put(
                f"/sentinel/company/{cid}/module-config",
                headers=world.auth("admin_a"),
                json={
                    "enabledModules": ["ATTENDANCE", "ACCESS_CONTROL", "EVENTS"],
                    "defaultStationMode": "UNIFIED_HYBRID",
                    "defaultZoneId": str(zone_id),
                    "defaultEventId": str(event_id),
                    "scanActionRules": {
                        "enableDoorRelayOnAttendance": True,
                        "unknownFaceAction": "LOG_INCIDENT",
                    },
                    "moduleSettings": {"attendance": {"requireGps": False}},
                },
            )
            assert ok.status_code == 200, ok.text
            saved = ok.json()
            assert saved["defaultStationMode"] == "UNIFIED_HYBRID"
            assert saved["defaultZoneId"] == str(zone_id)
            assert saved["defaultEventId"] == str(event_id)
            assert saved["scanActionRules"]["enableDoorRelayOnAttendance"] is True
            assert saved["moduleSettings"]["attendance"]["requireGps"] is False
            assert saved["moduleSettings"]["attendance"]["defaultPunchMode"] == "AUTO"

            again = await http.get(
                f"/sentinel/company/{cid}/module-config",
                headers=world.auth("admin_a"),
            )
            assert again.json()["defaultStationMode"] == "UNIFIED_HYBRID"
    finally:
        from sqlalchemy import text

        from src.config.database import async_session as _db

        async with _db() as db:
            await db.execute(
                text(
                    'DELETE FROM sentinel_incident_log WHERE "companyId" IN (:a, :b)'
                ),
                {"a": world.a.company_id, "b": world.b.company_id},
            )
            await db.execute(
                text('DELETE FROM sentinel_identity WHERE "companyId" IN (:a, :b)'),
                {"a": world.a.company_id, "b": world.b.company_id},
            )
            await db.execute(
                text('DELETE FROM sentinel_event WHERE "companyId" IN (:a, :b)'),
                {"a": world.a.company_id, "b": world.b.company_id},
            )
            await db.execute(
                text('DELETE FROM sentinel_access_zone WHERE "companyId" IN (:a, :b)'),
                {"a": world.a.company_id, "b": world.b.company_id},
            )
            await db.commit()
        await teardown_world(world)


# ---------------------------------------------------------------------------
# WS stationMode branches (mocked GPU / finalize / sentinel decision)
# ---------------------------------------------------------------------------


MEMBER_ID = uuid.uuid4()
COMPANY_ID = uuid.uuid4()
TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


@pytest.fixture
def _ws_station_env(monkeypatch):
    import src.config.settings as settings_mod

    s = settings_mod.settings
    monkeypatch.setattr(s, "SECRET_KEY", "unit-test-secret-key-that-is-long-enough-0123456789")
    monkeypatch.setattr(s, "FACE_ROUTES_REQUIRE_JWT", True)
    monkeypatch.setattr(s, "FACE_CORE_ENABLED", False)
    monkeypatch.setattr(s, "WS_KIOSK_AUTH_TIMEOUT_SECONDS", 2.0)
    monkeypatch.setattr(s, "WS_KIOSK_MAX_CONN_PER_IP", 16)
    monkeypatch.setattr(s, "WS_KIOSK_MAX_CONN_PER_COMPANY", 64)
    monkeypatch.setattr(s, "FACE_IDENTIFY_CACHE_SECONDS", 30.0)

    monkeypatch.setattr(ws_mod, "face_core_enabled", lambda: False)
    monkeypatch.setattr(ws_mod, "face_gpu_queue_stats", lambda: {"pending": 0, "started": True})
    monkeypatch.setattr(ws_mod, "decode_image_bytes", lambda c, **kw: object())
    monkeypatch.setattr(ws_mod, "get_decode_executor", lambda: None)
    monkeypatch.setattr(ws_mod, "run_on_face_gpu", AsyncMock(return_value=[0.1] * 8))
    monkeypatch.setattr(ws_mod, "get_walkby_encoding_frames", lambda frames: [0.1] * 8)

    class _CfgSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return None

        async def get(self, model, key):
            from src.models.member import RoleType, StatusType

            m = MagicMock()
            m.memberId = MEMBER_ID
            m.deletedAt = None
            m.status = StatusType.ENABLE
            m.role = RoleType.ADMIN_SYSTEM
            return m

        async def commit(self):
            return None

    monkeypatch.setattr(ws_mod, "async_session", lambda: _CfgSession())
    monkeypatch.setattr("src.config.database.async_session", lambda: _CfgSession())
    monkeypatch.setattr(
        "src.services.company_module_service.get_company_module_config",
        AsyncMock(
            return_value=merge_module_config(
                {"defaultStationMode": "ATTENDANCE", "defaultZoneId": None}
            )
        ),
    )

    ws_mod._conn_by_ip.clear()
    ws_mod._conn_by_company.clear()
    yield
    ws_mod._conn_by_ip.clear()
    ws_mod._conn_by_company.clear()


def _ws_app() -> FastAPI:
    app = FastAPI()

    @app.websocket("/face/ws/kiosk")
    async def _ws(websocket: WebSocket):
        await ws_mod.kiosk_websocket(websocket)

    return app


def test_ws_attendance_golden_path_still_finalize(_ws_station_env, monkeypatch):
    """ATTENDANCE (default) must still call _finalize_check_in — golden path."""
    finalize = AsyncMock(
        return_value={
            "matched": True,
            "checkedIn": True,
            "employee": {"firstName": "Ada", "lastName": "Lovelace", "username": "ada"},
            "message": "ok",
        }
    )
    monkeypatch.setattr(ws_mod, "_finalize_check_in", finalize)
    sentinel_eval = AsyncMock()
    monkeypatch.setattr(
        "src.routes.sentinel_routes.evaluate_unified_scan_decision",
        sentinel_eval,
    )

    token = create_access_token(str(MEMBER_ID), "admin")
    with TestClient(_ws_app()) as client:
        with client.websocket_connect("/face/ws/kiosk") as ws:
            assert ws.receive_json()["type"] == "ready"
            ws.send_json(
                {
                    "type": "session",
                    "companyId": str(COMPANY_ID),
                    "token": token,
                    "latitude": 13.75,
                    "longitude": 100.5,
                    "stationMode": "ATTENDANCE",
                }
            )
            assert ws.receive_json()["type"] == "session_ok"
            ws.send_json(
                {
                    "type": "checkin",
                    "trackId": "t1",
                    "requestId": "r1",
                    "images": [TINY_PNG_B64],
                    "latitude": 13.75,
                    "longitude": 100.5,
                }
            )
            msg = ws.receive_json()
            assert msg["type"] == "checked_in"
            assert msg["stationMode"] == "ATTENDANCE"
            assert msg["checkedIn"] is True
    assert finalize.await_count == 1
    assert sentinel_eval.await_count == 0


def test_ws_access_control_dispatches_sentinel_helper(_ws_station_env, monkeypatch):
    finalize = AsyncMock()
    monkeypatch.setattr(ws_mod, "_finalize_check_in", finalize)
    sentinel_eval = AsyncMock(
        return_value={
            "matched": True,
            "accessGranted": True,
            "decision": "ACCESS_GRANTED",
            "identityType": "EMPLOYEE",
            "subjectName": "Ada",
            "incident": {"eventType": "ACCESS_GRANTED"},
        }
    )
    monkeypatch.setattr(
        "src.routes.sentinel_routes.evaluate_unified_scan_decision",
        sentinel_eval,
    )

    token = create_access_token(str(MEMBER_ID), "admin")
    with TestClient(_ws_app()) as client:
        with client.websocket_connect("/face/ws/kiosk") as ws:
            assert ws.receive_json()["type"] == "ready"
            ws.send_json(
                {
                    "type": "session",
                    "companyId": str(COMPANY_ID),
                    "token": token,
                    "stationMode": "ACCESS_CONTROL",
                    "zoneId": str(uuid.uuid4()),
                }
            )
            assert ws.receive_json()["type"] == "session_ok"
            ws.send_json(
                {
                    "type": "checkin",
                    "trackId": "t2",
                    "requestId": "r2",
                    "images": [TINY_PNG_B64],
                    "totpOrPin": "123456",
                }
            )
            msg = ws.receive_json()
            assert msg["type"] == "checked_in"
            assert msg["stationMode"] == "ACCESS_CONTROL"
            assert msg["decision"] == "ACCESS_GRANTED"
            assert msg["accessGranted"] is True
            assert msg["subjectName"] == "Ada"
    assert finalize.await_count == 0
    assert sentinel_eval.await_count == 1
    kwargs = sentinel_eval.await_args.kwargs
    assert kwargs["station_mode"] == "ACCESS_CONTROL"
    assert kwargs["totp_or_pin"] == "123456"


def test_ws_unified_hybrid_finalize_and_decision_flag(_ws_station_env, monkeypatch):
    finalize = AsyncMock(
        return_value={
            "matched": True,
            "checkedIn": True,
            "employee": {"firstName": "Ada", "lastName": "L", "username": "ada"},
        }
    )
    monkeypatch.setattr(ws_mod, "_finalize_check_in", finalize)
    monkeypatch.setattr(
        ws_mod,
        "_maybe_attendance_door_relay",
        AsyncMock(return_value=True),
    )

    token = create_access_token(str(MEMBER_ID), "admin")
    with TestClient(_ws_app()) as client:
        with client.websocket_connect("/face/ws/kiosk") as ws:
            assert ws.receive_json()["type"] == "ready"
            ws.send_json(
                {
                    "type": "session",
                    "companyId": str(COMPANY_ID),
                    "token": token,
                    "stationMode": "UNIFIED_HYBRID",
                    "latitude": 13.75,
                    "longitude": 100.5,
                }
            )
            assert ws.receive_json()["type"] == "session_ok"
            ws.send_json(
                {
                    "type": "checkin",
                    "trackId": "t3",
                    "requestId": "r3",
                    "images": [TINY_PNG_B64],
                    "latitude": 13.75,
                    "longitude": 100.5,
                }
            )
            msg = ws.receive_json()
            assert msg["type"] == "checked_in"
            assert msg["stationMode"] == "UNIFIED_HYBRID"
            assert msg["decision"] == "ATTENDANCE_AND_ACCESS"
            assert msg["doorRelayTriggered"] is True
    assert finalize.await_count == 1
