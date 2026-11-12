"""System-admin face login: gallery search + login_face auth gate."""

from __future__ import annotations

import sys
import types
import uuid
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, UploadFile
from fastapi.testclient import TestClient
from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _ensure_authlib_stub() -> None:
    if "authlib" in sys.modules:
        return
    try:
        import authlib  # noqa: F401
        return
    except Exception:
        pass
    authlib = types.ModuleType("authlib")
    deprecate = types.ModuleType("authlib.deprecate")

    class AuthlibDeprecationWarning(DeprecationWarning):
        pass

    deprecate.AuthlibDeprecationWarning = AuthlibDeprecationWarning
    integrations = types.ModuleType("authlib.integrations")
    httpx_client = types.ModuleType("authlib.integrations.httpx_client")

    class AsyncOAuth2Client:  # pragma: no cover - import placeholder
        def __init__(self, *args, **kwargs):
            raise RuntimeError("authlib stub")

    httpx_client.AsyncOAuth2Client = AsyncOAuth2Client
    integrations.httpx_client = httpx_client
    authlib.deprecate = deprecate
    authlib.integrations = integrations
    sys.modules["authlib"] = authlib
    sys.modules["authlib.deprecate"] = deprecate
    sys.modules["authlib.integrations"] = integrations
    sys.modules["authlib.integrations.httpx_client"] = httpx_client


_ensure_authlib_stub()

from src.models.member import RoleType, StatusType  # noqa: E402
from src.services import face_match_service as fms  # noqa: E402
from src.routes import auth_routes  # noqa: E402


def _row(face_id, member_id, distance):
    return (face_id, member_id, distance)


@pytest.mark.asyncio
async def test_search_system_admin_accepts_clear_top_hit():
    admin_id = uuid.uuid4()
    face_id = uuid.uuid4()
    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            MagicMock(),  # SET LOCAL
            MagicMock(all=MagicMock(return_value=[_row(face_id, admin_id, 0.10)])),
        ]
    )
    hit = await fms.search_system_admin_face_pgvector(
        db, [0.1] * 512, threshold=0.32, ambiguity_margin=0.08
    )
    assert hit is not None
    assert hit[1] == admin_id
    assert hit[2] == pytest.approx(0.10)


@pytest.mark.asyncio
async def test_search_system_admin_rejects_above_threshold():
    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            MagicMock(),
            MagicMock(all=MagicMock(return_value=[_row(uuid.uuid4(), uuid.uuid4(), 0.40)])),
        ]
    )
    hit = await fms.search_system_admin_face_pgvector(
        db, [0.1] * 512, threshold=0.32, ambiguity_margin=0.08
    )
    assert hit is None


@pytest.mark.asyncio
async def test_search_system_admin_rejects_ambiguous_second():
    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            MagicMock(),
            MagicMock(
                all=MagicMock(
                    return_value=[
                        _row(uuid.uuid4(), uuid.uuid4(), 0.10),
                        _row(uuid.uuid4(), uuid.uuid4(), 0.14),  # delta 0.04 < 0.08
                    ]
                )
            ),
        ]
    )
    hit = await fms.search_system_admin_face_pgvector(
        db, [0.1] * 512, threshold=0.32, ambiguity_margin=0.08
    )
    assert hit is None


@pytest.mark.asyncio
async def test_search_system_admin_accepts_when_second_far_enough():
    admin_id = uuid.uuid4()
    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            MagicMock(),
            MagicMock(
                all=MagicMock(
                    return_value=[
                        _row(uuid.uuid4(), admin_id, 0.10),
                        _row(uuid.uuid4(), uuid.uuid4(), 0.25),  # delta 0.15 >= 0.08
                    ]
                )
            ),
        ]
    )
    hit = await fms.search_system_admin_face_pgvector(
        db, [0.1] * 512, threshold=0.32, ambiguity_margin=0.08
    )
    assert hit is not None
    assert hit[1] == admin_id


def _fake_upload() -> UploadFile:
    return UploadFile(filename="f.jpg", file=BytesIO(b"\xff\xd8\xfffakejpeg"))


def _admin_member(*, totp: bool = False):
    m = MagicMock()
    m.memberId = uuid.uuid4()
    m.username = "sysadmin"
    m.role = RoleType.ADMIN_SYSTEM
    m.status = StatusType.ENABLE
    m.deletedAt = None
    m.mustChangePassword = False
    m.totpEnabled = totp
    m.totpSecret = "BASE32SECRET2345" if totp else None
    m.failedLoginCount = 0
    m.lockedUntil = None
    return m


@pytest.mark.asyncio
async def test_login_face_success_issues_tokens(monkeypatch):
    admin = _admin_member()
    response = MagicMock()
    db = AsyncMock()
    db.get = AsyncMock(return_value=admin)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    monkeypatch.setattr(auth_routes, "write_audit", AsyncMock())
    monkeypatch.setattr(
        auth_routes,
        "_parse_face_login_challenge",
        lambda token: admin.memberId,
    )
    monkeypatch.setattr(
        auth_routes,
        "_tokens",
        lambda member, **kw: {
            "member": member,
            "access_token": "access",
            "refresh_token": "refresh",
            "token_type": "bearer",
            "mustChangePassword": False,
            "accessToken": "access",
            "refreshToken": "refresh",
        },
    )
    monkeypatch.setattr(
        auth_routes,
        "_attach_session_cookies",
        lambda response, payload: {**payload, "csrfToken": "csrf"},
    )
    monkeypatch.setattr(auth_routes, "register_success", lambda m: None)

    out = await auth_routes.login_face(
        response=response,
        db=db,
        _rl=None,
        challengeToken="chal",
        totpCode=None,
    )
    assert out["access_token"] == "access"
    assert out["csrfToken"] == "csrf"
    assert any(
        call.kwargs.get("action") == "LOGIN_FACE_OK"
        for call in auth_routes.write_audit.await_args_list
    )


@pytest.mark.asyncio
async def test_login_face_rejects_missing_member(monkeypatch):
    db = AsyncMock()
    db.get = AsyncMock(return_value=None)
    monkeypatch.setattr(auth_routes, "write_audit", AsyncMock())
    monkeypatch.setattr(
        auth_routes, "_parse_face_login_challenge", lambda token: uuid.uuid4()
    )

    with pytest.raises(HTTPException) as exc:
        await auth_routes.login_face(
            response=MagicMock(),
            db=db,
            _rl=None,
            challengeToken="chal",
            totpCode=None,
        )
    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid credentials"


@pytest.mark.asyncio
async def test_login_face_identify_returns_challenge(monkeypatch):
    admin = _admin_member()
    admin.firstName = "Sys"
    admin.lastName = "Admin"
    admin.picture = "a.jpg"
    frames = [_fake_upload() for _ in range(2)]
    db = AsyncMock()
    db.get = AsyncMock(return_value=admin)

    monkeypatch.setattr(
        auth_routes,
        "_save_face_login_frames",
        AsyncMock(return_value=["/tmp/a.jpg"] * 2),
    )
    monkeypatch.setattr(auth_routes, "_cleanup_face_login_paths", lambda paths: None)
    monkeypatch.setattr(
        auth_routes,
        "run_on_face_gpu",
        AsyncMock(return_value=[0.01] * 512),
    )
    monkeypatch.setattr(
        auth_routes,
        "search_system_admin_face_pgvector",
        AsyncMock(return_value=(uuid.uuid4(), admin.memberId, 0.11)),
    )
    monkeypatch.setattr(auth_routes, "write_audit", AsyncMock())
    monkeypatch.setattr(
        auth_routes, "create_face_login_challenge", lambda mid: f"chal-{mid}"
    )

    out = await auth_routes.login_face_identify(db=db, _rl=None, frames=frames)
    assert out["displayName"] == "Sys Admin"
    assert out["picture"] == "a.jpg"
    assert out["challengeToken"].startswith("chal-")
    assert "access" not in out
    assert "accessToken" not in out


@pytest.mark.asyncio
async def test_login_face_rejects_non_system_admin(monkeypatch):
    member = _admin_member()
    member.role = RoleType.MEMBER
    db = AsyncMock()
    db.get = AsyncMock(return_value=member)
    monkeypatch.setattr(auth_routes, "write_audit", AsyncMock())
    monkeypatch.setattr(
        auth_routes, "_parse_face_login_challenge", lambda token: member.memberId
    )

    with pytest.raises(HTTPException) as exc:
        await auth_routes.login_face(
            response=MagicMock(),
            db=db,
            _rl=None,
            challengeToken="chal",
            totpCode=None,
        )
    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid credentials"


@pytest.mark.asyncio
async def test_login_face_mfa_required_when_totp_enabled(monkeypatch):
    admin = _admin_member(totp=True)
    db = AsyncMock()
    db.get = AsyncMock(return_value=admin)

    monkeypatch.setattr(auth_routes, "write_audit", AsyncMock())
    monkeypatch.setattr(
        auth_routes, "_parse_face_login_challenge", lambda token: admin.memberId
    )

    with pytest.raises(HTTPException) as exc:
        await auth_routes.login_face(
            response=MagicMock(),
            db=db,
            _rl=None,
            challengeToken="chal",
            totpCode=None,
        )
    assert exc.value.status_code == 401
    assert exc.value.detail == "MFA_REQUIRED"


def test_rate_limit_face_login_bucket(monkeypatch):
    from src.config import settings as settings_mod
    from src.services import rate_limit_service as rl

    rl.reset_rate_limits_for_tests()
    monkeypatch.setattr(settings_mod.settings, "RATE_LIMIT_FACE_LOGIN_PER_MINUTE", 2)
    monkeypatch.setattr(settings_mod.settings, "REDIS_URL", "")

    app = FastAPI()

    @app.post("/auth/login/face")
    async def face(_=Depends(rl.rate_limit_face_login)):
        return {"ok": True}

    @app.exception_handler(HTTPException)
    async def _http(request: Request, exc: HTTPException):
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

    client = TestClient(app, raise_server_exceptions=False)
    assert client.post("/auth/login/face").status_code == 200
    assert client.post("/auth/login/face").status_code == 200
    blocked = client.post("/auth/login/face")
    assert blocked.status_code == 429
