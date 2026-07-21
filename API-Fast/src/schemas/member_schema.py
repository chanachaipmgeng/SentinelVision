from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime, date
from ..models.member import RoleType, StatusType


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


class MemberResponse(MemberBase):
    memberId: UUID
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True
