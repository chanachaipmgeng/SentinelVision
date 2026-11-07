from pydantic import BaseModel, field_validator
from typing import Any, Optional
from uuid import UUID
from datetime import datetime
from ..models.employee_timestamp import TimestampType, ApprovalStatus


class EmployeeTimestampBase(BaseModel):
    company_employeeId: UUID
    timestampType: Optional[TimestampType] = TimestampType.CHECK_IN
    locationName: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    photoTimestamp: Optional[str] = None
    note: Optional[str] = None
    approvalStatus: Optional[ApprovalStatus] = ApprovalStatus.NONE
    isLate: Optional[bool] = False
    lateMinutes: Optional[int] = 0
    overtimeMinutes: Optional[int] = 0
    shiftName: Optional[str] = None


class EmployeeTimestampCreate(EmployeeTimestampBase):
    punchType: Optional[str] = None


class EmployeeTimestampUpdate(BaseModel):
    timestampType: Optional[TimestampType] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    locationName: Optional[str] = None
    photoTimestamp: Optional[str] = None
    note: Optional[str] = None
    approvalStatus: Optional[ApprovalStatus] = None
    rejectReason: Optional[str] = None


class TimestampApprovalAction(BaseModel):
    approve: bool
    rejectReason: Optional[str] = None
    approvedBy: Optional[UUID] = None


class MemberResponse(BaseModel):
    memberId: UUID
    username: str
    email: str
    firstName: Optional[str]
    lastName: Optional[str]
    phoneNumber: Optional[str] = None
    picture: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    birthDate: Optional[datetime] = None
    address: Optional[str] = None
    emergencyContactName: Optional[str] = None
    emergencyContactPhone: Optional[str] = None
    attachmentUrls: Optional[str] = None


class PositionResponse(BaseModel):
    positionId: UUID
    thName: str
    engName: str


class DepartmentResponse(BaseModel):
    departmentId: UUID
    thName: str
    engName: str


class EmployeeModel(BaseModel):
    member: MemberResponse
    position: Optional[PositionResponse]
    department: Optional[DepartmentResponse]
    company_employeeId: UUID
    employeeId: str = ""
    bossId: str = ""

    @field_validator("employeeId", "bossId", mode="before")
    @classmethod
    def null_string_to_empty(cls, v: Any) -> str:
        return "" if v is None else v

    class Config:
        from_attributes = True


class EmployeeTimestampResponse(EmployeeTimestampBase):
    employee: EmployeeModel
    timestampId: UUID
    companyId: UUID
    timestamp: datetime
    createdAt: datetime
    updatedAt: Optional[datetime] = None
    approvedBy: Optional[UUID] = None
    approvedAt: Optional[datetime] = None
    rejectReason: Optional[str] = None

    class Config:
        from_attributes = True
