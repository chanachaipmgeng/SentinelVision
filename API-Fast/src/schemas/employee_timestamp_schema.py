from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime
from ..models.employee_timestamp import TimestampType

class EmployeeTimestampBase(BaseModel):
    company_employeeId: UUID
    timestampType: TimestampType
    locationName: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    photoTimestamp: Optional[str] = None

class EmployeeTimestampCreate(EmployeeTimestampBase):
    pass

class EmployeeTimestampUpdate(BaseModel):
    timestampType: Optional[TimestampType] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    locationName: Optional[str] = None
    photoTimestamp: Optional[str] = None
    
class MemberResponse(BaseModel):
    memberId: UUID
    username: str
    email: str
    firstName: Optional[str]
    lastName: Optional[str]

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
    employeeId: str
    bossId: str


class EmployeeTimestampResponse(EmployeeTimestampBase):
    employee: EmployeeModel
    timestampId: UUID
    companyId: UUID
    timestamp: datetime
    createdAt: datetime
    updatedAt: Optional[datetime] = None

    class Config:
        from_attributes = True
