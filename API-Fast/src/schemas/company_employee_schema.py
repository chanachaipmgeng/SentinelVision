from pydantic import BaseModel, EmailStr, field_validator, model_validator
from typing import Any, List, Optional
from uuid import UUID
from datetime import date, datetime

from ..models.company_employee import CompanyRoleType, EmpType


def _empty_to_none(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, str) and v.strip() == "":
        return None
    return v


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
    phoneNumber: Optional[str] = None
    birthDate: Optional[date] = None
    address: Optional[str] = None
    emergencyContactName: Optional[str] = None
    emergencyContactPhone: Optional[str] = None
    attachmentUrls: Optional[str] = None

    @field_validator(
        "firstName",
        "lastName",
        "picture",
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


class PositionInput(BaseModel):
    positionId: UUID
    thName: Optional[str] = None
    engName: Optional[str] = None

    @field_validator("thName", "engName", mode="before")
    @classmethod
    def blank_to_none(cls, v: Any) -> Any:
        return _empty_to_none(v)


class DepartmentInput(BaseModel):
    departmentId: UUID
    thName: Optional[str] = None
    engName: Optional[str] = None

    @field_validator("thName", "engName", mode="before")
    @classmethod
    def blank_to_none(cls, v: Any) -> Any:
        return _empty_to_none(v)


class CompanyEmployeePost(BaseModel):
    member: MemberInput
    position: Optional[PositionInput] = None
    department: Optional[DepartmentInput] = None
    employeeId: Optional[str] = None
    salary: Optional[float] = 0
    bossId: Optional[str] = None
    companyRoleType: CompanyRoleType = CompanyRoleType.EMP
    empType: EmpType = EmpType.PERMONTH
    startDate: Optional[datetime] = None

    @field_validator("position", "department", mode="before")
    @classmethod
    def empty_object_to_none(cls, v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, dict):
            # Angular often sends {} or {positionId: null, ...} when unset
            useful = {k: val for k, val in v.items() if _empty_to_none(val) is not None}
            if "positionId" not in useful and "departmentId" not in useful:
                return None
            return useful
        return v

    @field_validator("employeeId", "bossId", "startDate", mode="before")
    @classmethod
    def blank_to_none(cls, v: Any) -> Any:
        return _empty_to_none(v)

    @field_validator("salary", mode="before")
    @classmethod
    def salary_blank_to_zero(cls, v: Any) -> Any:
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return 0
        return v

    @model_validator(mode="after")
    def require_position_and_department(self) -> "CompanyEmployeePost":
        if self.position is None or self.position.positionId is None:
            raise ValueError("กรุณาเลือกตำแหน่ง (position)")
        if self.department is None or self.department.departmentId is None:
            raise ValueError("กรุณาเลือกแผนก (department)")
        return self


class CompanyEmployeeCreate(CompanyEmployeeBase):
    pass


class CompanyEmployeeUpdate(BaseModel):
    member: MemberInput
    position: Optional[PositionInput] = None
    department: Optional[DepartmentInput] = None
    employeeId: Optional[str] = None
    salary: Optional[float] = 0
    bossId: Optional[str] = None
    company_employeeId: UUID
    companyRoleType: CompanyRoleType = CompanyRoleType.EMP
    empType: EmpType = EmpType.PERMONTH
    startDate: Optional[datetime] = None

    @field_validator("position", "department", mode="before")
    @classmethod
    def empty_object_to_none(cls, v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, dict):
            useful = {k: val for k, val in v.items() if _empty_to_none(val) is not None}
            if "positionId" not in useful and "departmentId" not in useful:
                return None
            return useful
        return v

    @field_validator("employeeId", "bossId", "startDate", mode="before")
    @classmethod
    def blank_to_none(cls, v: Any) -> Any:
        return _empty_to_none(v)

    @field_validator("salary", mode="before")
    @classmethod
    def salary_blank_to_zero(cls, v: Any) -> Any:
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return 0
        return v


class MemberResponse(BaseModel):
    memberId: UUID
    email: str
    firstName: Optional[str]
    lastName: Optional[str]
    picture: Optional[str]
    phoneNumber: Optional[str] = None
    birthDate: Optional[date] = None
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


class EmployeeImportCreatedRow(BaseModel):
    row: int
    email: str
    company_employeeId: str
    employeeId: str = ""


class EmployeeImportErrorRow(BaseModel):
    row: int
    email: str = ""
    message: str


class EmployeeImportResult(BaseModel):
    total: int
    success: int
    failed: int
    created: List[EmployeeImportCreatedRow] = []
    errors: List[EmployeeImportErrorRow] = []
