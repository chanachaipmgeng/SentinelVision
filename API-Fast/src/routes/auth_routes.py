from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import bcrypt
from passlib.context import CryptContext

from ..config.database import get_db
from ..models.member import Member
from ..schemas.auth_schema import LoginRequest, Token
from ..security.deps import get_current_member
from ..security.jwt import create_access_token, create_refresh_token, decode_token
from ..security.passwords import assert_not_locked, hash_password, register_failure, register_success
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
    if not _verify_password(request.password, member.passwordHash):
        register_failure(member)
        await db.commit()
        await write_audit(actor=member, action="LOGIN_FAIL", path="/auth/login", status_code=401)
        raise HTTPException(status_code=401, detail="Invalid credentials")
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
