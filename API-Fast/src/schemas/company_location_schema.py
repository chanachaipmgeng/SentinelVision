from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

from ..models.company_location import LocationType

class CompanyLocationBase(BaseModel):
    latitude: float
    longitude: float
    radius: float
    locationName: str
    startDate: datetime
    endDate: datetime
    locationType: LocationType

class CompanyLocationCreate(CompanyLocationBase):
    pass

class CompanyLocationUpdate(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius: Optional[float] = None
    locationName: Optional[str] = None
    startDate: Optional[datetime] = None
    endDate: Optional[datetime] = None
    locationType: Optional[LocationType] = None

class CompanyLocationResponse(CompanyLocationBase):
    locationId: UUID
    companyId: UUID
    createdAt: datetime
    updatedAt: Optional[datetime] = None

    class Config:
        from_attributes = True
