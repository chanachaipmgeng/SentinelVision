from pydantic import BaseModel, EmailStr, field_validator
from typing import Any, Optional
from uuid import UUID
from datetime import datetime, date
from ..models.member import RoleType, StatusType


def _empty_to_none(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, str) and v.strip() == "":
        return None
    return v


class MemberBase(BaseModel):
    memberId: Optional[UUID] = None
    username: str
    email: EmailStr
    picture: Optional[str] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    phoneNumber: Optional[str] = None
    role: RoleType
    status: StatusType
    birthDate: Optional[date] = None
    address: Optional[str] = None
    emergencyContactName: Optional[str] = None
    emergencyContactPhone: Optional[str] = None
    attachmentUrls: Optional[str] = None

    @field_validator(
        "picture",
        "firstName",
        "lastName",
        "phoneNumber",
        "birthDate",
        "address",
        "emergencyContactName",
        "emergencyContactPhone",
        "attachmentUrls",
        mode="before",
    )
    @classmethod
    def blank_optional_to_none(cls, v: Any) -> Any:
        return _empty_to_none(v)


class MemberCreate(MemberBase):
    password: str


class MemberUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    picture: Optional[str] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    phoneNumber: Optional[str] = None
    role: Optional[RoleType] = None
    status: Optional[StatusType] = None
    password: Optional[str] = None
    birthDate: Optional[date] = None
    address: Optional[str] = None
    emergencyContactName: Optional[str] = None
    emergencyContactPhone: Optional[str] = None
    attachmentUrls: Optional[str] = None

    @field_validator(
        "username",
        "email",
        "picture",
        "firstName",
        "lastName",
        "phoneNumber",
        "password",
        "birthDate",
        "address",
        "emergencyContactName",
        "emergencyContactPhone",
        "attachmentUrls",
        mode="before",
    )
    @classmethod
    def blank_optional_to_none(cls, v: Any) -> Any:
        return _empty_to_none(v)


class MemberResponse(MemberBase):
    memberId: UUID
    createdAt: datetime
    updatedAt: Optional[datetime] = None
    biometricConsentAt: Optional[datetime] = None
    biometricConsentVersion: Optional[str] = None
    faceEncodingCount: int = 0

    class Config:
        from_attributes = True
