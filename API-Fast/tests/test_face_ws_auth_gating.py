"""Handshake contract for /face/ws/kiosk: nothing reaches the GPU before `session` is authenticated.

The face engine, DB session, and GPU queue are mocked; only the WebSocket state
machine in `face_ws_controller.kiosk_websocket` is exercised.
"""

from __future__ import annotations

import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock

# Avoid InsightFace/onnx at import time
_mock_insight = MagicMock()
sys.modules.setdefault("insightface", _mock_insight)
sys.modules.setdefault("insightface.app", _mock_insight.app)
sys.modules.setdefault("onnxruntime", MagicMock())

import pytest
from fastapi import FastAPI, WebSocket
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import src.config.settings as settings_mod  # noqa: E402
from src.controllers import face_ws_controller as ws_mod  # noqa: E402
from src.security.jwt import create_access_token, create_kiosk_token  # noqa: E402

COMPANY_ID = uuid.uuid4()
OTHER_COMPANY_ID = uuid.uuid4()
MEMBER_ID = uuid.uuid4()
DEVICE_ID = uuid.uuid4()
POLICY_VIOLATION = 1008

TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


class _FakeSession:
    """Minimal async-context DB stand-in for member_from_token / verify_kiosk_token_db."""

    def __init__(self, member: Any = None, device: Any = None) -> None:
        self._member = member
        self._device = device

    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        return None

    async def get(self, model: Any, key: Any) -> Any:
        name = getattr(model, "__name__", "")
        if name == "KioskDevice":
            return self._device
        return self._member

    async def commit(self) -> None:
        return None


def _fake_member() -> MagicMock:
    from src.models.member import RoleType, StatusType

    m = MagicMock()
    m.memberId = MEMBER_ID
    m.deletedAt = None
    m.status = StatusType.ENABLE
    m.role = RoleType.ADMIN_SYSTEM  # bypasses the company_employee lookup
    return m


def _fake_device(token: str) -> MagicMock:
    from src.security.jwt import hash_kiosk_token

    d = MagicMock()
    d.deviceId = DEVICE_ID
    d.companyId = COMPANY_ID
    d.revokedAt = None
    d.tokenHash = hash_kiosk_token(token)
    return d


@pytest.fixture(autouse=True)
def _isolated_ws(monkeypatch):
    """Fast auth deadline, mocked engine/DB, clean connection registry."""
    s = settings_mod.settings
    monkeypatch.setattr(s, "SECRET_KEY", "unit-test-secret-key-that-is-long-enough-0123456789")
    monkeypatch.setattr(s, "FACE_ROUTES_REQUIRE_JWT", True)
    monkeypatch.setattr(s, "FACE_CORE_ENABLED", False)
    monkeypatch.setattr(s, "WS_KIOSK_AUTH_TIMEOUT_SECONDS", 1.0)
    monkeypatch.setattr(s, "WS_KIOSK_MAX_CONN_PER_IP", 16)
    monkeypatch.setattr(s, "WS_KIOSK_MAX_CONN_PER_COMPANY", 64)

    gpu_calls: Dict[str, int] = {"detect": 0}

    async def _fake_run_on_face_gpu(fn, *, kind="detect", **kwargs):
        gpu_calls[kind] = gpu_calls.get(kind, 0) + 1
        return {"frameWidth": 1, "frameHeight": 1, "faces": []}

    monkeypatch.setattr(ws_mod, "run_on_face_gpu", _fake_run_on_face_gpu)
    monkeypatch.setattr(ws_mod, "decode_image_bytes", lambda c, **kw: object())
    # None → asyncio default thread pool; the patched decoder is trivial anyway.
    monkeypatch.setattr(ws_mod, "get_decode_executor", lambda: None)
    monkeypatch.setattr(ws_mod, "face_gpu_queue_stats", lambda: {"pending": 0, "started": True})
    monkeypatch.setattr(ws_mod, "face_core_enabled", lambda: False)

    ws_mod._conn_by_ip.clear()
    ws_mod._conn_by_company.clear()
    yield gpu_calls
    ws_mod._conn_by_ip.clear()
    ws_mod._conn_by_company.clear()


def _app() -> FastAPI:
    app = FastAPI()

    @app.websocket("/face/ws/kiosk")
    async def _ws(websocket: WebSocket):
        await ws_mod.kiosk_websocket(websocket)

    return app


def _member_session(monkeypatch, *, company_id: uuid.UUID = COMPANY_ID) -> dict:
    token = create_access_token(str(MEMBER_ID), "admin")
    monkeypatch.setattr(
        "src.config.database.async_session", lambda: _FakeSession(member=_fake_member())
    )
    return {"type": "session", "companyId": str(company_id), "token": token}


def _expect_policy_close(ws, code: str) -> None:
    with pytest.raises(WebSocketDisconnect) as exc:
        # The server sends a final error frame before closing; drain until the close.
        for _ in range(3):
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert msg["code"] == code
    assert exc.value.code == POLICY_VIOLATION
    assert exc.value.reason == code


def test_detect_before_session_is_rejected_and_never_hits_gpu(_isolated_ws):
    gpu_calls = _isolated_ws
    with TestClient(_app()) as client:
        with client.websocket_connect("/face/ws/kiosk") as ws:
            ready = ws.receive_json()
            assert ready["type"] == "ready"
            ws.send_json({"type": "detect", "requestId": "d-1", "image": TINY_PNG_B64})
            _expect_policy_close(ws, "unauthenticated")
    assert gpu_calls.get("detect", 0) == 0
    assert ws_mod.kiosk_ws_connection_counts() == {"byIp": {}, "byCompany": {}}


@pytest.mark.parametrize("payload", ["not json", '{"type": "ping"}', '{"type": "identify", "trackId": 1}'])
def test_any_non_session_message_before_auth_closes_socket(payload):
    with TestClient(_app()) as client:
        with client.websocket_connect("/face/ws/kiosk") as ws:
            assert ws.receive_json()["type"] == "ready"
            ws.send_text(payload)
            _expect_policy_close(ws, "unauthenticated")


def test_invalid_token_session_closes_socket(monkeypatch):
    monkeypatch.setattr("src.config.database.async_session", lambda: _FakeSession())
    with TestClient(_app()) as client:
        with client.websocket_connect("/face/ws/kiosk") as ws:
            assert ws.receive_json()["type"] == "ready"
            ws.send_json({"type": "session", "companyId": str(COMPANY_ID), "token": "garbage"})
            _expect_policy_close(ws, "invalid_session")


def test_expired_token_session_closes_socket(monkeypatch):
    import jwt as pyjwt

    expired = pyjwt.encode(
        {"memberId": str(MEMBER_ID), "username": "x", "typ": "access", "exp": int(time.time()) - 60},
        settings_mod.settings.SECRET_KEY,
        algorithm="HS256",
    )
    monkeypatch.setattr("src.config.database.async_session", lambda: _FakeSession(member=_fake_member()))
    with TestClient(_app()) as client:
        with client.websocket_connect("/face/ws/kiosk") as ws:
            assert ws.receive_json()["type"] == "ready"
            ws.send_json({"type": "session", "companyId": str(COMPANY_ID), "token": expired})
            _expect_policy_close(ws, "invalid_session")


def test_idle_unauthenticated_socket_times_out(monkeypatch):
    monkeypatch.setattr(settings_mod.settings, "WS_KIOSK_AUTH_TIMEOUT_SECONDS", 0.3)
    with TestClient(_app()) as client:
        with client.websocket_connect("/face/ws/kiosk") as ws:
            ready = ws.receive_json()
            assert ready["type"] == "ready"
            assert ready["authTimeoutSeconds"] == pytest.approx(0.3)
            started = time.monotonic()
            _expect_policy_close(ws, "auth_timeout")
            assert time.monotonic() - started < 3.0


def test_authenticated_member_flow_reaches_detect(monkeypatch, _isolated_ws):
    gpu_calls = _isolated_ws
    session = _member_session(monkeypatch)
    with TestClient(_app()) as client:
        with client.websocket_connect("/face/ws/kiosk") as ws:
            assert ws.receive_json()["type"] == "ready"
            ws.send_json(session)
            ok = ws.receive_json()
            assert ok["type"] == "session_ok"
            assert ok["companyId"] == str(COMPANY_ID)
            assert ws_mod.kiosk_ws_connection_counts()["byCompany"] == {str(COMPANY_ID): 1}

            ws.send_json({"type": "ping"})
            assert ws.receive_json()["type"] == "pong"

            ws.send_json({"type": "detect", "requestId": "d-1", "image": TINY_PNG_B64})
            detected = ws.receive_json()
            assert detected["type"] == "detected"
            assert detected["requestId"] == "d-1"
            assert not detected.get("dropped")
    assert gpu_calls["detect"] == 1
    assert ws_mod.kiosk_ws_connection_counts() == {"byIp": {}, "byCompany": {}}


def test_kiosk_device_token_flow(monkeypatch, _isolated_ws):
    token = create_kiosk_token(device_id=str(DEVICE_ID), company_id=str(COMPANY_ID), expires_days=1)
    monkeypatch.setattr(
        "src.config.database.async_session", lambda: _FakeSession(device=_fake_device(token))
    )
    with TestClient(_app()) as client:
        with client.websocket_connect("/face/ws/kiosk") as ws:
            assert ws.receive_json()["type"] == "ready"
            # Kiosk tokens are company-bound: a mismatching companyId is refused.
            ws.send_json({"type": "session", "companyId": str(OTHER_COMPANY_ID), "token": token})
            _expect_policy_close(ws, "invalid_session")

        with client.websocket_connect("/face/ws/kiosk") as ws:
            assert ws.receive_json()["type"] == "ready"
            ws.send_json({"type": "session", "token": token})
            ok = ws.receive_json()
            assert ok["type"] == "session_ok"
            assert ok["companyId"] == str(COMPANY_ID)
            ws.send_json({"type": "detect", "requestId": "d-2", "image": TINY_PNG_B64})
            assert ws.receive_json()["type"] == "detected"
    assert _isolated_ws["detect"] == 1


def test_re_session_after_auth_keeps_socket_on_bad_token(monkeypatch, _isolated_ws):
    session = _member_session(monkeypatch)
    with TestClient(_app()) as client:
        with client.websocket_connect("/face/ws/kiosk") as ws:
            assert ws.receive_json()["type"] == "ready"
            ws.send_json(session)
            assert ws.receive_json()["type"] == "session_ok"
            # Token refresh with a broken token: report, but keep the authenticated socket alive.
            ws.send_json({**session, "token": "broken"})
            err = ws.receive_json()
            assert err["type"] == "error"
            assert err["code"] == "invalid_session"
            ws.send_json({"type": "ping"})
            assert ws.receive_json()["type"] == "pong"


def test_per_ip_connection_cap(monkeypatch):
    monkeypatch.setattr(settings_mod.settings, "WS_KIOSK_MAX_CONN_PER_IP", 2)
    with TestClient(_app()) as client:
        with client.websocket_connect("/face/ws/kiosk") as ws1, client.websocket_connect(
            "/face/ws/kiosk"
        ) as ws2:
            assert ws1.receive_json()["type"] == "ready"
            assert ws2.receive_json()["type"] == "ready"
            assert sum(ws_mod.kiosk_ws_connection_counts()["byIp"].values()) == 2
            with client.websocket_connect("/face/ws/kiosk") as ws3:
                _expect_policy_close(ws3, "too_many_connections")
            # Rejected handshake must not leak a slot.
            assert sum(ws_mod.kiosk_ws_connection_counts()["byIp"].values()) == 2
    assert ws_mod.kiosk_ws_connection_counts()["byIp"] == {}


def test_per_ip_cap_uses_x_real_ip_from_gateway(monkeypatch):
    monkeypatch.setattr(settings_mod.settings, "WS_KIOSK_MAX_CONN_PER_IP", 1)
    with TestClient(_app()) as client:
        with client.websocket_connect("/face/ws/kiosk", headers={"X-Real-IP": "10.1.1.5"}) as ws1:
            assert ws1.receive_json()["type"] == "ready"
            # Different kiosk behind the same gateway: its own bucket, so it is admitted.
            with client.websocket_connect("/face/ws/kiosk", headers={"X-Real-IP": "10.1.1.6"}) as ws2:
                assert ws2.receive_json()["type"] == "ready"
                assert ws_mod.kiosk_ws_connection_counts()["byIp"] == {"10.1.1.5": 1, "10.1.1.6": 1}
            with client.websocket_connect("/face/ws/kiosk", headers={"X-Real-IP": "10.1.1.5"}) as ws3:
                _expect_policy_close(ws3, "too_many_connections")


def test_per_company_connection_cap(monkeypatch):
    monkeypatch.setattr(settings_mod.settings, "WS_KIOSK_MAX_CONN_PER_COMPANY", 1)
    session = _member_session(monkeypatch)
    with TestClient(_app()) as client:
        with client.websocket_connect("/face/ws/kiosk") as ws1:
            assert ws1.receive_json()["type"] == "ready"
            ws1.send_json(session)
            assert ws1.receive_json()["type"] == "session_ok"
            with client.websocket_connect("/face/ws/kiosk") as ws2:
                assert ws2.receive_json()["type"] == "ready"
                ws2.send_json(session)
                _expect_policy_close(ws2, "too_many_connections")
            assert ws_mod.kiosk_ws_connection_counts()["byCompany"] == {str(COMPANY_ID): 1}
    assert ws_mod.kiosk_ws_connection_counts()["byCompany"] == {}
