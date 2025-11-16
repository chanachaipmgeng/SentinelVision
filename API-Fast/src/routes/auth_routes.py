from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from ..models.member import Member
from ..config.database import get_db
from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt
from ..schemas.auth_schema import Token, LoginRequest

router = APIRouter()

# Secret key and algorithm for JWT
SECRET_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJtZW1iZXJfaWQiOiJkZjE0OWM4Ni02Njc0LTRmODItYTE0Yi05OWFjNmZjYjJjNjIiLCJ1c2VybmFtZSI6ImNoYW5hY2hhaSIsImlhdCI6MTcyNDYzNDI0NSwiZXhwIjoxNzI0NjM3ODQ1fQ.bxa0LGelFhlGGb8PSgNd1oq-QZKqaNKbLA6oMuzEEeo"  # Replace with your actual secret key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 3600 *3600  # Token expiration time

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/login", response_model=Token)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    username = request.username
    password = request.password

    # Query the database for the member
    stmt = select(Member).where(Member.username == username)
    result = await db.execute(stmt)
    member = result.scalars().first()

    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    # Verify the password
    if not pwd_context.verify(password, member.passwordHash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Generate a JWT
    token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token_payload = {"memberId": str(member.memberId), "username": member.username, "exp": datetime.utcnow() + token_expires}
    token = jwt.encode(token_payload, SECRET_KEY, algorithm=ALGORITHM)

    return {"member" : member ,"access_token": token, "token_type": "bearer"}
