from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class DepartmentBase(BaseModel):
    thName: str
    engName: str
    companyId: UUID
    shiftId: Optional[UUID] = None

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentUpdate(BaseModel):
    thName: Optional[str] = None
    engName: Optional[str] = None
    companyId: Optional[UUID] = None
    shiftId: Optional[UUID] = None

class DepartmentResponse(DepartmentBase):
    departmentId: UUID

    class Config:
        from_attributes = True
