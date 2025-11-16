from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime
from ..models.company import PublicType

class CompanyBase(BaseModel):
    companyName: str
    companyCode: str
    companyInfo: str
    address: str
    latitude: float
    longitude: float
    picture: str
    status: PublicType
    ownerName: str
    contact: str

class CompanyUpdate(BaseModel):
    companyName: Optional[str] = None
    companyCode: Optional[str] = None
    companyInfo: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    picture: Optional[str] = None
    status: Optional[PublicType] = None
    ownerName: Optional[str] = None
    contact: Optional[str] = None

class CompanyResponse(CompanyBase):
    companyId: UUID
    createdAt: datetime
    updatedAt: datetime
    class Config:
        from_attributes = True
