from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from uuid import UUID
from datetime import datetime
from ..models.member import RoleType, StatusType


# Base schema (shared properties)
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


# Schema for creating a new member
class MemberCreate(MemberBase):
    password: str  # Password is required during creation


# Schema for updating an existing member
class MemberUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    picture: Optional[str] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    phoneNumber: Optional[str] = None
    role: Optional[RoleType] = None
    status: Optional[StatusType] = None
    password: Optional[str] = None  # Optional password for updates


# Schema for returning member data (response)
class MemberResponse(MemberBase):
    memberId: UUID
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True  # Enable ORM mode to work seamlessly with SQLAlchemy models
