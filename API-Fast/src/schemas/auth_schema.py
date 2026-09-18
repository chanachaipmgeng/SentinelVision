from pydantic import BaseModel

from ..schemas.member_schema import MemberBase


class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    member: MemberBase
    access_token: str
    token_type: str
    refresh_token: str | None = None
    mustChangePassword: bool = False
    accessToken: str | None = None
    refreshToken: str | None = None
