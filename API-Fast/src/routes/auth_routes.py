import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import bcrypt
import jwt as pyjwt
from passlib.context import CryptContext

from ..config.database import get_db
from ..config.settings import settings
from ..models.hr_schedule import KioskDevice
from ..models.member import Member
from ..schemas.auth_schema import LoginRequest, Token
from ..security.deps import assert_company_access, get_current_member
from ..services import rbac_service
from ..security.jwt import (
    ALGORITHM,
    TYP_ACCESS,
    TYP_KIOSK_REFRESH,
    TYP_REFRESH,
    create_kiosk_token_pair,
    create_token_pair,
    decode_token,
    hash_kiosk_token,
    kiosk_refresh_ttl,
    kiosk_token_ttl,
    refresh_token_ttl,
    token_exp_datetime,
)
from ..security.kiosk_pairing import (
    assert_pair_attempt_allowed,
    hash_pairing_code,
    normalize_pairing_code,
)
from ..security.oidc import OidcError, OidcProvider, extract_email, get_provider, oidc_enabled
from ..security.passwords import assert_not_locked, hash_password, register_failure, register_success
from ..security.totp import build_otpauth_uri, generate_totp_secret, verify_totp
from ..services.audit_service import write_audit
from ..services import token_revocation_service as revocation
from ..services.sso_policy_service import get_sso_policy, jit_provision_member, save_sso_policy

router = APIRouter()
logger = logging.getLogger("dpu.auth")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _verify_password(plain: str, password_hash: str) -> bool:
    try:
        hashed = password_hash.encode("utf-8") if isinstance(password_hash, str) else password_hash
        return bcrypt.checkpw(plain.encode("utf-8"), hashed)
    except Exception:
        try:
            return pwd_context.verify(plain, password_hash)
        except Exception:
            return False


class RefreshRequest(BaseModel):
    refreshToken: str | None = None
    refresh_token: str | None = None


class ChangePasswordRequest(BaseModel):
    currentPassword: str
    newPassword: str


class MfaVerifyRequest(BaseModel):
    code: str


class OidcStartRequest(BaseModel):
    companyId: str | None = None
    returnTo: str | None = None


class OidcCallbackRequest(BaseModel):
    code: str = Field(min_length=1)
    state: str = Field(min_length=1)
    txn: str = Field(min_length=1)


class SsoPolicyRequest(BaseModel):
    jitProvisioning: bool = False
    allowedEmailDomains: list[str] = Field(default_factory=list)
    defaultDepartmentId: str | None = None
    defaultPositionId: str | None = None


class LogoutRequest(BaseModel):
    refreshToken: str | None = None
    refresh_token: str | None = None


class KioskPairRequest(BaseModel):
    pairingCode: str
    deviceFingerprint: str | None = None


class KioskRefreshRequest(BaseModel):
    refreshToken: str | None = None
    refresh_token: str | None = None


def _tokens(member: Member, *, family: Optional[str] = None) -> dict:
    access, refresh = create_token_pair(str(member.memberId), member.username, family=family)
    return {
        "member": member,
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "mustChangePassword": bool(getattr(member, "mustChangePassword", False)),
        "accessToken": access,
        "refreshToken": refresh,
    }


@router.post("/login", response_model=Token)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Member).where(Member.username == request.username))
    member = result.scalars().first()
    if not member or getattr(member, "deletedAt", None) is not None:
        raise HTTPException(status_code=404, detail="Member not found")
    assert_not_locked(member)
    status_val = getattr(member.status, "value", member.status)
    if status_val in (0, "DISABLED"):
        raise HTTPException(status_code=403, detail="Account disabled")
    if not _verify_password(request.password, member.passwordHash):
        register_failure(member)
        await db.commit()
        await write_audit(actor=member, action="LOGIN_FAIL", path="/auth/login", status_code=401)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if bool(getattr(member, "totpEnabled", False)) and getattr(member, "totpSecret", None):
        code = (request.totpCode or "").strip()
        if not code:
            raise HTTPException(status_code=401, detail="MFA_REQUIRED")
        if not verify_totp(member.totpSecret, code):
            register_failure(member)
            await db.commit()
            await write_audit(actor=member, action="LOGIN_MFA_FAIL", path="/auth/login", status_code=401)
            raise HTTPException(status_code=401, detail="Invalid 2FA authenticator code")

    register_success(member)
    await db.commit()
    await db.refresh(member)
    await write_audit(actor=member, action="LOGIN_OK", path="/auth/login", status_code=200)
    return _tokens(member)


async def _assert_refresh_not_revoked(db: AsyncSession, payload: dict, *, refresh_ttl) -> None:
    """Reject revoked refresh tokens. Presenting an already-rotated token is reuse: a stolen
    copy is being replayed, so the whole family is revoked and both parties are logged out."""
    jti = payload.get("jti")
    fam = payload.get("fam")
    if not jti and not fam:
        return
    hit = await revocation.lookup_revocation(db, jti, fam)
    if hit is None:
        return
    if hit["scope"] == revocation.SCOPE_TOKEN and hit.get("reason") == revocation.REASON_ROTATED and fam:
        await revocation.revoke_family(
            db,
            fam,
            revocation.family_expiry_for(payload, refresh_ttl=refresh_ttl),
            reason=revocation.REASON_REUSE,
        )
        await db.commit()
        raise HTTPException(status_code=401, detail="Refresh token reuse detected; session revoked")
    raise HTTPException(status_code=401, detail="Refresh token has been revoked")


@router.post("/refresh-token")
@router.post("/refresh")
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    raw = body.refreshToken or body.refresh_token
    if not raw:
        raise HTTPException(status_code=401, detail="Refresh token required")
    payload = decode_token(raw, expected_typ=TYP_REFRESH)
    await _assert_refresh_not_revoked(db, payload, refresh_ttl=refresh_token_ttl())

    member = await db.get(Member, UUID(str(payload["memberId"])))
    if not member or getattr(member, "deletedAt", None) is not None:
        raise HTTPException(status_code=401, detail="Member not found")
    assert_not_locked(member)
    status_val = getattr(member.status, "value", member.status)
    if status_val in (0, "DISABLED"):
        raise HTTPException(status_code=403, detail="Account disabled")
    # Rotation: the presented refresh token is single-use; the new pair stays in the same family.
    await revocation.revoke_token_payload(db, payload, reason=revocation.REASON_ROTATED)
    await db.commit()
    return _tokens(member, family=payload.get("fam"))


def _bearer_payload_allow_expired(request: Request) -> Optional[dict]:
    """Signature-verified access token from the Authorization header, ignoring ``exp`` so a
    client can still log out (revoke its refresh token) after the access token lapsed."""
    header = request.headers.get("authorization") or ""
    if not header.lower().startswith("bearer "):
        return None
    raw = header.split(" ", 1)[1].strip()
    try:
        payload = pyjwt.decode(
            raw, settings.SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False}
        )
    except pyjwt.InvalidTokenError:
        return None
    if payload.get("typ", TYP_ACCESS) != TYP_ACCESS or not payload.get("memberId"):
        return None
    return payload


@router.post("/logout")
async def logout(body: LogoutRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Revoke the current session: the access token (header), the refresh token (body) and the
    family they share. Idempotent; works with an expired access token as long as it is ours."""
    access_payload = _bearer_payload_allow_expired(request)
    refresh_payload = None
    raw_refresh = body.refreshToken or body.refresh_token
    if raw_refresh:
        try:
            refresh_payload = decode_token(raw_refresh, expected_typ=TYP_REFRESH)
        except HTTPException:
            refresh_payload = None
    if access_payload is None and refresh_payload is None:
        raise HTTPException(status_code=401, detail="No valid token to revoke")

    revoked = 0
    family = None
    family_exp = datetime.now(timezone.utc) + refresh_token_ttl()
    for payload in (access_payload, refresh_payload):
        if not payload:
            continue
        family = family or payload.get("fam")
        if payload.get("typ") == TYP_REFRESH:
            family_exp = max(family_exp, token_exp_datetime(payload))
        if payload.get("jti"):
            await revocation.revoke_token_payload(db, payload, reason=revocation.REASON_LOGOUT)
            revoked += 1
    if family:
        await revocation.revoke_family(db, family, family_exp, reason=revocation.REASON_LOGOUT)
    await db.commit()

    member_id = (access_payload or refresh_payload or {}).get("memberId")
    member = await db.get(Member, UUID(str(member_id))) if member_id else None
    if member is not None:
        await write_audit(actor=member, action="LOGOUT", path="/auth/logout", status_code=200)
    return {"ok": True, "revokedTokens": revoked, "familyRevoked": bool(family)}


# ---------------------------------------------------------------------------
# Kiosk device pairing: one-time code → device-scoped token pair (short TTL, refreshable)
# ---------------------------------------------------------------------------
def _client_ip(request: Request) -> str:
    xff = (request.headers.get("x-forwarded-for") or "").strip()
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _kiosk_session(device: KioskDevice, access: str, refresh: str) -> dict:
    return {
        "deviceToken": access,
        "deviceRefreshToken": refresh,
        "token_type": "bearer",
        "expiresIn": int(kiosk_token_ttl().total_seconds()),
        "refreshExpiresIn": int(kiosk_refresh_ttl().total_seconds()),
        "deviceId": str(device.deviceId),
        "companyId": str(device.companyId),
        "locationId": str(device.locationId) if device.locationId else None,
        "deviceName": device.name,
    }


@router.post("/kiosk/pair")
async def kiosk_pair(body: KioskPairRequest, request: Request, db: AsyncSession = Depends(get_db)):
    assert_pair_attempt_allowed(_client_ip(request))
    code = normalize_pairing_code(body.pairingCode)
    if len(code) < 6:
        raise HTTPException(status_code=401, detail="Invalid pairing code")
    device = (
        await db.execute(select(KioskDevice).where(KioskDevice.pairingCodeHash == hash_pairing_code(code)))
    ).scalars().first()
    if device is None:
        raise HTTPException(status_code=401, detail="Invalid pairing code")
    if device.revokedAt is not None:
        raise HTTPException(status_code=401, detail="Kiosk device has been revoked")
    now = datetime.now(timezone.utc)
    expires_at = device.pairingExpiresAt
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at is None or expires_at <= now:
        device.pairingCodeHash = None
        device.pairingExpiresAt = None
        await db.commit()
        raise HTTPException(status_code=401, detail="Pairing code has expired")

    # Single use: consume the code and start a fresh token family for this device.
    if device.tokenFamily:
        await revocation.revoke_family(db, device.tokenFamily, now + kiosk_refresh_ttl(), reason=revocation.REASON_REPAIR)
    access, refresh = create_kiosk_token_pair(
        str(device.deviceId),
        str(device.companyId),
        location_id=str(device.locationId) if device.locationId else None,
    )
    device.pairingCodeHash = None
    device.pairingExpiresAt = None
    device.tokenHash = hash_kiosk_token(access)
    device.tokenFamily = decode_token(access, expected_typ="kiosk").get("fam")
    device.pairedAt = now
    device.lastSeenAt = now
    await db.commit()
    await db.refresh(device)
    return _kiosk_session(device, access, refresh)


@router.post("/kiosk/refresh")
async def kiosk_refresh(body: KioskRefreshRequest, db: AsyncSession = Depends(get_db)):
    raw = body.refreshToken or body.refresh_token
    if not raw:
        raise HTTPException(status_code=401, detail="Refresh token required")
    payload = decode_token(raw, expected_typ=TYP_KIOSK_REFRESH)
    await _assert_refresh_not_revoked(db, payload, refresh_ttl=kiosk_refresh_ttl())

    device = await db.get(KioskDevice, UUID(str(payload["deviceId"])))
    if device is None or str(device.companyId) != str(payload["companyId"]):
        raise HTTPException(status_code=401, detail="Kiosk device not found")
    if device.revokedAt is not None:
        raise HTTPException(status_code=401, detail="Kiosk device has been revoked")
    if not device.tokenFamily or device.tokenFamily != payload.get("fam"):
        raise HTTPException(status_code=401, detail="Kiosk device must be paired again")

    await revocation.revoke_token_payload(db, payload, reason=revocation.REASON_ROTATED)
    access, refresh = create_kiosk_token_pair(
        str(device.deviceId),
        str(device.companyId),
        location_id=str(device.locationId) if device.locationId else None,
        family=device.tokenFamily,
    )
    device.tokenHash = hash_kiosk_token(access)
    device.lastSeenAt = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(device)
    return _kiosk_session(device, access, refresh)


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    if len(body.newPassword) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if not _verify_password(body.currentPassword, member.passwordHash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    db_member = await db.get(Member, member.memberId)
    db_member.passwordHash = hash_password(body.newPassword)
    db_member.mustChangePassword = False
    await db.commit()
    return {"ok": True}


@router.get("/mfa/status")
async def mfa_status(member: Member = Depends(get_current_member)):
    return {
        "memberId": str(member.memberId),
        "username": member.username,
        "totpEnabled": bool(getattr(member, "totpEnabled", False)),
        "oidcConfigured": oidc_enabled(),
    }


@router.post("/mfa/setup")
async def mfa_setup(
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    db_member = await db.get(Member, member.memberId)
    secret = generate_totp_secret()
    db_member.totpSecret = secret
    db_member.totpEnabled = False
    await db.commit()
    return {
        "secret": secret,
        "otpauthUri": build_otpauth_uri(secret, db_member.username),
        "totpEnabled": False,
    }


@router.post("/mfa/enable")
async def mfa_enable(
    body: MfaVerifyRequest,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    db_member = await db.get(Member, member.memberId)
    secret = getattr(db_member, "totpSecret", None)
    if not secret:
        raise HTTPException(status_code=400, detail="Run /auth/mfa/setup first")
    if not verify_totp(secret, body.code):
        raise HTTPException(status_code=400, detail="Invalid 6-digit authenticator code")
    db_member.totpEnabled = True
    await db.commit()
    await write_audit(actor=db_member, action="MFA_ENABLED", path="/auth/mfa/enable", status_code=200)
    return {"totpEnabled": True}


@router.post("/mfa/disable")
async def mfa_disable(
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    db_member = await db.get(Member, member.memberId)
    db_member.totpEnabled = False
    db_member.totpSecret = None
    await db.commit()
    await write_audit(actor=db_member, action="MFA_DISABLED", path="/auth/mfa/disable", status_code=200)
    return {"totpEnabled": False}


# --------------------------------------------------------------------------- OIDC SSO
# Authorization Code + PKCE relying party (src/security/oidc.py). The legacy
# `POST /auth/sso/oidc` that accepted a self-signed HS256 `idToken` is gone; the
# path now behaves exactly like `/auth/sso/oidc/callback`.


def _require_oidc() -> OidcProvider:
    if not oidc_enabled():
        raise HTTPException(status_code=501, detail="OIDC SSO is not enabled on this server")
    return get_provider()


def _oidc_http_error(exc: OidcError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


async def _audit_sso(**kwargs) -> None:
    # Audit must never turn a successful SSO login into a 500.
    try:
        await write_audit(**kwargs)
    except Exception:
        logger.warning("sso audit write failed", exc_info=True)


@router.get("/sso/oidc/status")
async def sso_oidc_status():
    enabled = oidc_enabled()
    return {
        "enabled": enabled,
        "issuer": (settings.OIDC_ISSUER or "").strip() if enabled else None,
        "flow": "authorization_code+pkce" if enabled else None,
    }


@router.post("/sso/oidc/start")
async def sso_oidc_start(body: OidcStartRequest | None = None):
    provider = _require_oidc()
    body = body or OidcStartRequest()
    company_id = None
    if body.companyId:
        try:
            company_id = str(UUID(str(body.companyId)))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid companyId")
    return_to = (body.returnTo or "").strip() or None
    if return_to and (not return_to.startswith("/") or return_to.startswith("//")):
        # only same-origin paths may be used as a post-login redirect
        raise HTTPException(status_code=400, detail="returnTo must be a relative path")
    try:
        return await provider.build_authorization_request(company_id=company_id, return_to=return_to)
    except OidcError as exc:
        raise _oidc_http_error(exc)


@router.post("/sso/oidc", response_model=Token)
@router.post("/sso/oidc/callback", response_model=Token)
async def sso_oidc_callback(body: OidcCallbackRequest, db: AsyncSession = Depends(get_db)):
    provider = _require_oidc()
    try:
        claims, txn = await provider.login_with_code(body.code, body.state, body.txn)
        email = extract_email(claims)
    except OidcError as exc:
        await _audit_sso(action="SSO_LOGIN_FAIL", path="/auth/sso/oidc/callback", status_code=exc.status_code)
        raise _oidc_http_error(exc)

    result = await db.execute(select(Member).where(func.lower(Member.email) == email))
    member = result.scalars().first()
    provisioned = False
    if member is None:
        member = await jit_provision_member(db, claims=claims, email=email, company_id=txn.company_id)
        provisioned = True
    elif getattr(member, "deletedAt", None) is not None:
        raise HTTPException(status_code=404, detail="No active member linked to this SSO email")

    assert_not_locked(member)
    status_val = getattr(member.status, "value", member.status)
    if status_val in (0, "DISABLED"):
        raise HTTPException(status_code=403, detail="Account disabled")

    register_success(member)
    await db.commit()
    await db.refresh(member)
    if provisioned:
        await _audit_sso(
            actor=member,
            action="SSO_JIT_PROVISIONED",
            path="/auth/sso/oidc/callback",
            status_code=200,
            company_id=txn.company_id,
            entity_type="member",
            entity_id=str(member.memberId),
            detail={"issuer": claims.get("iss"), "sub": claims.get("sub")},
        )
    await _audit_sso(
        actor=member,
        action="SSO_LOGIN_OK",
        path="/auth/sso/oidc/callback",
        status_code=200,
        detail={"issuer": claims.get("iss"), "sub": claims.get("sub")},
    )
    issued = _tokens(member)
    if txn.return_to:
        issued["returnTo"] = txn.return_to
    return issued


@router.get("/me/permissions")
async def my_permissions(
    companyId: Optional[UUID] = None,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    """Server-driven RBAC snapshot for the signed-in member (never trust localStorage)."""
    if companyId is not None and not rbac_service.is_system_admin_member(member):
        # Caller must at least belong to the company (or hold a role there).
        emp = await rbac_service.get_company_employment(db, member.memberId, companyId)
        assignments = await rbac_service.list_role_assignments(db, member.memberId, companyId)
        if emp is None and not assignments:
            raise HTTPException(status_code=403, detail="No access to this company")
    perms = sorted(
        await rbac_service.permissions_for_member(db, member, companyId)
    )
    roles = await rbac_service.roles_for_member(db, member, companyId)
    return {
        "memberId": str(member.memberId),
        "companyId": str(companyId) if companyId else None,
        "roles": roles,
        "permissions": perms,
    }


@router.get("/sso/policy/{companyId}")
async def get_company_sso_policy(
    companyId: UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    await assert_company_access(db, member, companyId)
    return await get_sso_policy(db, companyId)


@router.put("/sso/policy/{companyId}")
async def put_company_sso_policy(
    companyId: UUID,
    body: SsoPolicyRequest,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    await assert_company_access(db, member, companyId)
    return await save_sso_policy(db, companyId, body.model_dump())
