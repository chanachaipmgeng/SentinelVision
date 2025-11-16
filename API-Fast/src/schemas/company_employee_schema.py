from pydantic import BaseModel , EmailStr
from typing import Optional
from uuid import UUID
from datetime import date, datetime
from ..models.company_employee import CompanyRoleType, EmpType, StatusType
from ..models.member import RoleType
class CompanyEmployeeBase(BaseModel):
    memberId: UUID
    companyId: UUID
    positionId: UUID
    departmentId: UUID
    employeeId: str
    
class MemberInput(BaseModel):
    email: EmailStr
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    picture: Optional[str] = None


class PositionInput(BaseModel):
    positionId: UUID
    thName: str
    engName: str


class DepartmentInput(BaseModel):
    departmentId: UUID
    thName: str
    engName: str


class CompanyEmployeePost(BaseModel):
    member: MemberInput
    position: Optional[PositionInput] = None
    department: Optional[DepartmentInput] = None
    employeeId: Optional[str] = None
    salary: Optional[float] = None
    bossId: Optional[str] = None
    companyRoleType: CompanyRoleType
    empType: EmpType
    startDate: datetime

class CompanyEmployeeCreate(CompanyEmployeeBase):
    pass

class CompanyEmployeeUpdate(BaseModel):
    member: MemberInput
    position: Optional[PositionInput] = None
    department: Optional[DepartmentInput] = None
    employeeId: Optional[str] = None
    salary: Optional[float] = None
    bossId: Optional[str] = None,
    company_employeeId: UUID
    companyRoleType: CompanyRoleType
    empType: EmpType
    startDate: datetime

class MemberResponse(BaseModel):
    memberId: UUID
    email: str
    firstName: Optional[str]
    lastName: Optional[str]
    picture: Optional[str]


class PositionResponse(BaseModel):
    positionId: UUID
    thName: str
    engName: str

class DepartmentResponse(BaseModel):
    departmentId: UUID
    thName: str
    engName: str

class CompanyEmployeeResponse(BaseModel):
    member: MemberResponse
    companyId: UUID
    position: Optional[PositionResponse]
    department: Optional[DepartmentResponse]
    company_employeeId: UUID
    employeeId: str
    salary: float
    bossId: str
    companyRoleType: CompanyRoleType
    empType: EmpType
    startDate: datetime

    class Config:
        from_attributes = True