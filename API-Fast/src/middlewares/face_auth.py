"""Optional JWT gate for /face/* HTTP routes (kiosk WS stays open)."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..config.settings import settings
from ..middlewares.auth_middleware import authenticate_jwt

_bearer = HTTPBearer(auto_error=False)


async def face_route_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Optional[dict[str, Any]]:
    if not settings.FACE_ROUTES_REQUIRE_JWT:
        return None
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization required for face routes",
        )
    return await authenticate_jwt(credentials)
