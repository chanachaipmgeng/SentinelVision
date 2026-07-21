from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from ..models.member import Member
from ..config.database import get_db
from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt
import bcrypt
from ..schemas.auth_schema import Token, LoginRequest

router = APIRouter()

# Secret key and algorithm for JWT
SECRET_KEY = "***REMOVED***"  # Replace with your actual secret key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 3600 * 3600

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _verify_password(plain: str, password_hash: str) -> bool:
    """Prefer bcrypt.checkpw — avoids passlib backend bugs with newer bcrypt."""
    try:
        hashed = password_hash.encode("utf-8") if isinstance(password_hash, str) else password_hash
        return bcrypt.checkpw(plain.encode("utf-8"), hashed)
    except Exception:
        try:
            return pwd_context.verify(plain, password_hash)
        except Exception:
            return False


@router.post("/login", response_model=Token)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    username = request.username
    password = request.password

    stmt = select(Member).where(Member.username == username)
    result = await db.execute(stmt)
    member = result.scalars().first()

    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    if not _verify_password(password, member.passwordHash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token_payload = {
        "memberId": str(member.memberId),
        "username": member.username,
        "exp": datetime.utcnow() + token_expires,
    }
    token = jwt.encode(token_payload, SECRET_KEY, algorithm=ALGORITHM)

    return {"member": member, "access_token": token, "token_type": "bearer"}
