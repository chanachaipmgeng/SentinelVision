"""System-admin biometric consent (company-less) for console face enroll."""

from __future__ import annotations

import sys
import types
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

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
    jose = types.ModuleType("authlib.jose")
    jose_errors = types.ModuleType("authlib.jose.errors")

    class JoseError(Exception):
        pass

    jose_errors.JoseError = JoseError
    jose.JsonWebKey = object
    jose.JsonWebToken = object
    jose.errors = jose_errors
    oidc_core = types.ModuleType("authlib.oidc.core")
    oidc_core.CodeIDToken = object
    authlib.deprecate = deprecate
    authlib.jose = jose
    authlib.oidc = types.ModuleType("authlib.oidc")
    authlib.oidc.core = oidc_core
    sys.modules["authlib"] = authlib
    sys.modules["authlib.deprecate"] = deprecate
    sys.modules["authlib.jose"] = jose
    sys.modules["authlib.jose.errors"] = jose_errors
    sys.modules["authlib.oidc"] = authlib.oidc
    sys.modules["authlib.oidc.core"] = oidc_core


_ensure_authlib_stub()

from src.models.member import RoleType, StatusType  # noqa: E402
from src.routes import member_routes  # noqa: E402


def _member(*, role=RoleType.ADMIN_SYSTEM):
    m = MagicMock()
    m.memberId = uuid.uuid4()
    m.role = role
    m.status = StatusType.ENABLE
    m.deletedAt = None
    m.biometricConsentAt = None
    m.biometricConsentVersion = None
    m.biometricConsentText = None
    return m


@pytest.mark.asyncio
async def test_grant_consent_system_admin_ok(monkeypatch):
    admin = _member()
    db = AsyncMock()
    db.get = AsyncMock(return_value=admin)
    recorded = {}

    async def _record(db_, member, company_id, *, locale="th"):
        recorded["company_id"] = company_id
        recorded["locale"] = locale
        recorded["memberId"] = member.memberId
        return {"memberId": str(member.memberId), "hasConsent": True}

    monkeypatch.setattr(member_routes.pdpa_service, "record_biometric_consent", _record)

    req = MagicMock()
    req.json = AsyncMock(return_value={"locale": "th"})
    out = await member_routes.grant_system_admin_biometric_consent(
        memberId=admin.memberId, request=req, db=db
    )
    assert out["hasConsent"] is True
    assert recorded["company_id"] == "system"


@pytest.mark.asyncio
async def test_grant_consent_rejects_non_admin():
    emp = _member(role=RoleType.MEMBER)
    db = AsyncMock()
    db.get = AsyncMock(return_value=emp)
    req = MagicMock()
    req.json = AsyncMock(return_value={})
    with pytest.raises(HTTPException) as exc:
        await member_routes.grant_system_admin_biometric_consent(
            memberId=emp.memberId, request=req, db=db
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_revoke_clears_consent_and_local_encodings(monkeypatch):
    admin = _member()
    db = AsyncMock()
    db.get = AsyncMock(return_value=admin)
    db.commit = AsyncMock()
    monkeypatch.setattr(member_routes, "face_core_enabled", lambda: False)
    monkeypatch.setattr(
        member_routes, "_clear_local_face_encodings", AsyncMock(return_value=2)
    )

    out = await member_routes.revoke_system_admin_biometric_consent(
        memberId=admin.memberId, db=db
    )
    assert out["hasConsent"] is False
    assert out["deletedEncodings"] == 2
    assert admin.biometricConsentAt is None
    db.commit.assert_awaited()
