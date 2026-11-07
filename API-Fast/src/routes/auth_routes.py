from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import bcrypt
import jwt as pyjwt
from passlib.context import CryptContext

from ..config.database import get_db
from ..config.settings import settings
from ..models.member import Member
from ..schemas.auth_schema import LoginRequest, Token
from ..security.deps import get_current_member
from ..security.jwt import create_access_token, create_refresh_token, decode_token
from ..security.passwords import assert_not_locked, hash_password, register_failure, register_success
from ..security.totp import build_otpauth_uri, generate_totp_secret, verify_totp
from ..services.audit_service import write_audit

router = APIRouter()
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


class OidcLoginRequest(BaseModel):
    idToken: str


def _tokens(member: Member) -> dict:
    access = create_access_token(str(member.memberId), member.username)
    refresh = create_refresh_token(str(member.memberId), member.username)
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


@router.post("/refresh-token")
@router.post("/refresh")
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    raw = body.refreshToken or body.refresh_token
    if not raw:
        raise HTTPException(status_code=401, detail="Refresh token required")
    payload = decode_token(raw, expected_typ="refresh")
    from uuid import UUID

    member = await db.get(Member, UUID(str(payload["memberId"])))
    if not member or getattr(member, "deletedAt", None) is not None:
        raise HTTPException(status_code=401, detail="Member not found")
    assert_not_locked(member)
    status_val = getattr(member.status, "value", member.status)
    if status_val in (0, "DISABLED"):
        raise HTTPException(status_code=403, detail="Account disabled")
    issued = _tokens(member)
    return issued


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
        "oidcConfigured": bool((settings.OIDC_ISSUER or "").strip()),
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


@router.post("/sso/oidc", response_model=Token)
async def sso_oidc_login(body: OidcLoginRequest, db: AsyncSession = Depends(get_db)):
    issuer = (settings.OIDC_ISSUER or "").strip()
    if not issuer:
        raise HTTPException(status_code=501, detail="OIDC SSO is not configured on this server")
    try:
        claims = pyjwt.decode(
            body.idToken,
            settings.SECRET_KEY,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Invalid OIDC token: {exc}")
    if claims.get("iss") != issuer:
        raise HTTPException(status_code=401, detail="OIDC issuer mismatch")
    email = (claims.get("email") or claims.get("upn") or "").strip()
    if not email:
        raise HTTPException(status_code=400, detail="OIDC token missing email claim")
    result = await db.execute(select(Member).where(Member.email == email))
    member = result.scalars().first()
    if not member or getattr(member, "deletedAt", None) is not None:
        raise HTTPException(status_code=404, detail="No active member linked to this SSO email")
    assert_not_locked(member)
    status_val = getattr(member.status, "value", member.status)
    if status_val in (0, "DISABLED"):
        raise HTTPException(status_code=403, detail="Account disabled")
    await write_audit(actor=member, action="SSO_LOGIN_OK", path="/auth/sso/oidc", status_code=200)
    return _tokens(member)
