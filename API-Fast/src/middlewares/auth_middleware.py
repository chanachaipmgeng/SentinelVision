from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

SECRET_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJtZW1iZXJfaWQiOiJkZjE0OWM4Ni02Njc0LTRmODItYTE0Yi05OWFjNmZjYjJjNjIiLCJ1c2VybmFtZSI6ImNoYW5hY2hhaSIsImlhdCI6MTcyNDYzNDI0NSwiZXhwIjoxNzI0NjM3ODQ1fQ.bxa0LGelFhlGGb8PSgNd1oq-QZKqaNKbLA6oMuzEEeo"  # ใช้ secret key เดียวกับที่ใช้ใน auth_routes
ALGORITHM = "HS256"

security = HTTPBearer()

async def authenticate_jwt(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        # Decode and validate the JWT
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload  # คืน payload ที่ถอดรหัสแล้ว
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
