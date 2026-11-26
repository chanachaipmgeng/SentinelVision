"""Wave 1 (v7.0.0) Zero-Trust security, multi-tenancy, MediaMTX auth, SSRF, and RBAC tests."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from src.models.member import RoleType
from src.routes import auth_routes, mediamtx_auth_routes
from src.security.client_ip import client_ip_from_request
from src.security.jwt import TYP_STREAM, create_face_login_challenge, create_stream_token, decode_token
from src.security.ssrf import validate_outbound_url
from src.services import api_key_service, audit_service, rbac_service


def test_saml_acs_disabled_rejects_unverified_payload():
    app = FastAPI()
    app.include_router(auth_routes.router, prefix="/auth")
    client = TestClient(app)
    resp = client.post(
        "/auth/sso/saml/acs",
        json={"companyId": str(uuid.uuid4()), "email": "admin@example.com"},
    )
    assert resp.status_code == 403
    assert "SAML_NOT_CONFIGURED" in resp.text


def test_stream_token_roundtrip_and_mediamtx_auth(monkeypatch):
    cid = uuid.uuid4()
    cam_id = uuid.uuid4()
    tok = create_stream_token(str(cid), str(cam_id), ttl_minutes=5)
    payload = decode_token(tok, expected_typ=TYP_STREAM)
    assert payload["companyId"] == str(cid)
    assert payload["cameraId"] == str(cam_id)

    cam_obj = MagicMock()
    cam_obj.cameraId = cam_id
    cam_obj.companyId = cid
    cam_obj.deletedAt = None
    cam_obj.isActive = True

    fake_db = AsyncMock()
    fake_db.get = AsyncMock(return_value=cam_obj)

    async def _fake_db():
        yield fake_db

    app = FastAPI()
    app.include_router(mediamtx_auth_routes.router, prefix="/internal/mediamtx")
    app.dependency_overrides[mediamtx_auth_routes.get_db] = _fake_db
    client = TestClient(app)

    # 1. External/WebRTC publish (WHIP) must always be denied.
    r_pub = client.post(
        "/internal/mediamtx/auth",
        json={"action": "publish", "protocol": "webrtc", "ip": "203.0.113.10", "path": cam_id.hex},
    )
    assert r_pub.status_code == 401

    # 2. Browser read without stream JWT must be denied.
    r_no_tok = client.post(
        "/internal/mediamtx/auth",
        json={"action": "read", "protocol": "webrtc", "ip": "203.0.113.10", "path": cam_id.hex, "query": ""},
    )
    assert r_no_tok.status_code == 401

    # 3. Valid stream JWT for matching camera succeeds.
    r_ok = client.post(
        "/internal/mediamtx/auth",
        json={
            "action": "read",
            "protocol": "webrtc",
            "ip": "203.0.113.10",
            "path": cam_id.hex,
            "query": f"jwt={tok}",
        },
    )
    assert r_ok.status_code == 200

    # 4. Stream JWT for a different camera path fails.
    r_mismatch = client.post(
        "/internal/mediamtx/auth",
        json={
            "action": "read",
            "protocol": "webrtc",
            "ip": "203.0.113.10",
            "path": uuid.uuid4().hex,
            "query": f"jwt={tok}",
        },
    )
    assert r_mismatch.status_code == 401


@pytest.mark.parametrize(
    "bad_url",
    [
        "http://127.0.0.1:8000/metrics",
        "http://169.254.169.254/latest/meta-data/",
        "http://localhost/admin",
        "http://mediamtx:9997/v3/paths/list",
        "http://10.0.0.5/hook",
        "http://192.168.1.50/hook",
        "ftp://example.com/file",
    ],
)
def test_ssrf_blocks_internal_and_private_webhook_targets(bad_url: str):
    with pytest.raises(HTTPException) as exc:
        validate_outbound_url(bad_url, allow_private_lan=False)
    assert exc.value.status_code == 400


def test_ssrf_allows_lan_device_only_when_explicit_and_still_blocks_metadata():
    assert validate_outbound_url("http://192.168.1.50/onvif/ptz_service", allow_private_lan=True).startswith(
        "http://192.168.1.50"
    )
    with pytest.raises(HTTPException):
        validate_outbound_url("http://169.254.169.254/latest/meta-data/", allow_private_lan=True)
    with pytest.raises(HTTPException):
        validate_outbound_url("http://mediamtx:9997/v3/paths/list", allow_private_lan=True)


def test_trusted_client_ip_prefers_x_real_ip_and_rightmost_xff():
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/auth/login",
        "headers": [
            (b"x-forwarded-for", b"1.2.3.4, 198.51.100.25"),
            (b"x-real-ip", b"198.51.100.25"),
        ],
        "client": ("172.18.0.5", 12345),
    }
    assert client_ip_from_request(Request(scope)) == "198.51.100.25"

    scope_no_real = {
        "type": "http",
        "method": "GET",
        "path": "/auth/login",
        "headers": [(b"x-forwarded-for", b"1.2.3.4, 198.51.100.99")],
        "client": ("172.18.0.5", 12345),
    }
    assert client_ip_from_request(Request(scope_no_real)) == "198.51.100.99"


@pytest.mark.asyncio
async def test_allowed_location_ids_handles_dict_roles(monkeypatch):
    cid = uuid.uuid4()
    loc_id = uuid.uuid4()
    mgr = MagicMock()
    mgr.memberId = uuid.uuid4()
    mgr.role = RoleType.MEMBER

    emp = MagicMock()
    emp.companyRoleType = 0
    emp.locationId = loc_id

    monkeypatch.setattr(rbac_service, "get_company_employment", AsyncMock(return_value=emp))
    monkeypatch.setattr(
        rbac_service,
        "roles_for_member",
        AsyncMock(return_value=[{"role": "MANAGER", "companyId": str(cid)}]),
    )
    scoped = await rbac_service.allowed_location_ids(MagicMock(), mgr, cid)
    assert scoped == {loc_id}

    monkeypatch.setattr(
        rbac_service,
        "roles_for_member",
        AsyncMock(return_value=[{"role": "HR_ADMIN", "companyId": str(cid)}]),
    )
    assert await rbac_service.allowed_location_ids(MagicMock(), mgr, cid) is None


def test_api_key_valid_scopes_includes_scim_write():
    assert "scim.write" in api_key_service.VALID_SCOPES


@pytest.mark.asyncio
async def test_face_login_rejects_replayed_challenge(monkeypatch):
    admin_id = uuid.uuid4()
    chal = create_face_login_challenge(str(admin_id))

    db = AsyncMock()
    monkeypatch.setattr(auth_routes, "write_audit", AsyncMock())
    monkeypatch.setattr(auth_routes.revocation, "is_token_revoked", AsyncMock(return_value=True))

    with pytest.raises(HTTPException) as exc:
        await auth_routes.login_face(
            response=MagicMock(),
            db=db,
            _rl=None,
            challengeToken=chal,
            totpCode=None,
        )
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_mfa_disable_requires_confirmation():
    member = MagicMock()
    member.memberId = uuid.uuid4()
    member.passwordHash = "$2b$12$invalidhashvalue000000000000000000000000000000000000"
    member.totpSecret = "JBSWY3DPEHPK3PXP"
    db = AsyncMock()
    db.get = AsyncMock(return_value=member)

    with pytest.raises(HTTPException) as exc:
        await auth_routes.mfa_disable(body=None, member=member, db=db)
    assert exc.value.status_code == 401


def test_audit_hash_v1_and_v2_compatibility():
    now_iso = datetime.now(timezone.utc).isoformat()
    h1 = audit_service.compute_audit_hash(
        "GENESIS",
        company_id="comp-1",
        action="POST",
        actor_member_id="mem-1",
        entity_type="zone",
        entity_id="z-1",
        path="/sentinel/company/comp-1/zones",
        status_code="200",
        detail_payload={"ok": True},
        algo="sha256-v1",
    )
    h2 = audit_service.compute_audit_hash(
        h1,
        company_id="comp-1",
        action="POST",
        actor_member_id="mem-1",
        entity_type="zone",
        entity_id="z-1",
        path="/sentinel/company/comp-1/zones",
        status_code="200",
        detail_payload={"ok": True},
        entry_id="row-2",
        occurred_at=now_iso,
        ip="198.51.100.1",
        user_agent="pytest",
        request_id="req-2",
        algo="sha256-v2",
    )
    assert len(h1) == 64 and len(h2) == 64 and h1 != h2
