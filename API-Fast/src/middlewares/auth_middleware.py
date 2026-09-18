"""JWT gate. Secrets live in settings."""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..security.jwt import decode_token

security = HTTPBearer(auto_error=False)


async def authenticate_jwt(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authorization required")
    return decode_token(credentials.credentials, expected_typ="access")
