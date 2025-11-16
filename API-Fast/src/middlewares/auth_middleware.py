from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

SECRET_KEY = "***REMOVED***"  # ใช้ secret key เดียวกับที่ใช้ใน auth_routes
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
