from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class PositionBase(BaseModel):
    thName: str
    engName: str
    companyId: UUID

class PositionCreate(PositionBase):
    pass

class PositionUpdate(BaseModel):
    thName: Optional[str] = None
    engName: Optional[str] = None
    companyId: Optional[UUID] = None

class PositionResponse(PositionBase):
    positionId: UUID

    class Config:
        from_attributes = True
