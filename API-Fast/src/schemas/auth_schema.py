from typing import Optional
from pydantic import BaseModel

from ..schemas.member_schema import MemberBase


class LoginRequest(BaseModel):
    username: str
    password: str
    totpCode: Optional[str] = None


class Token(BaseModel):
    member: MemberBase
    access_token: str
    token_type: str
    refresh_token: str | None = None
    mustChangePassword: bool = False
    accessToken: str | None = None
    refreshToken: str | None = None
    # Double-submit CSRF for cookie-based refresh/logout (also set as readable cookie).
    csrfToken: str | None = None
    # SSO only: same-origin path requested via /auth/sso/oidc/start
    returnTo: str | None = None
