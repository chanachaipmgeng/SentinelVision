from fastapi import HTTPException, status
from datetime import datetime, timedelta
from ..models.member import Member  # สมมติว่าคุณมีโมเดล Member ที่เชื่อมต่อกับฐานข้อมูลแล้ว
from ..config.database import get_db
from passlib.context import CryptContext
import jwt

# กำหนด Secret Key สำหรับ JWT
SECRET_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJtZW1iZXJfaWQiOiJkZjE0OWM4Ni02Njc0LTRmODItYTE0Yi05OWFjNmZjYjJjNjIiLCJ1c2VybmFtZSI6ImNoYW5hY2hhaSIsImlhdCI6MTcyNDYzNDI0NSwiZXhwIjoxNzI0NjM3ODQ1fQ.bxa0LGelFhlGGb8PSgNd1oq-QZKqaNKbLA6oMuzEEeo"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# สร้าง Context สำหรับเข้ารหัสรหัสผ่าน
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ฟังก์ชันสำหรับตรวจสอบรหัสผ่าน
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# ฟังก์ชันสร้าง JWT
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# ฟังก์ชันเข้าสู่ระบบ
async def login(db, username: str, password: str):
    # ค้นหาผู้ใช้จากฐานข้อมูลโดยใช้ชื่อผู้ใช้
    query = await db.execute(select(Member).where(Member.username == username))
    member = query.scalars().first()

    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # ตรวจสอบรหัสผ่าน
    if not verify_password(password, member.passwordHash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # สร้าง JWT
    access_token = create_access_token(data={"sub": member.username, "memberId": str(member.memberId)})

    return { "member" : member ,"access_token": access_token, "token_type": "bearer"}
