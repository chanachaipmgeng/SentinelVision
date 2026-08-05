from pydantic import BaseModel, field_validator
from typing import Any, Optional
from uuid import UUID
from datetime import datetime, timezone

from ..models.company_location import LocationType


def _empty_to_none(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, str) and v.strip() == "":
        return None
    return v


def _default_now() -> datetime:
    return datetime.now(timezone.utc)


class CompanyLocationBase(BaseModel):
    latitude: float
    longitude: float
    radius: float = 0.5
    locationName: str
    startDate: Optional[datetime] = None
    endDate: Optional[datetime] = None
    locationType: LocationType = LocationType.PERMANENT

    @field_validator("startDate", "endDate", "locationName", mode="before")
    @classmethod
    def blank_to_none(cls, v: Any) -> Any:
        return _empty_to_none(v)

    @field_validator("radius", mode="before")
    @classmethod
    def radius_blank_to_default(cls, v: Any) -> Any:
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return 0.5
        return v


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

    @field_validator(
        "startDate",
        "endDate",
        "locationName",
        "radius",
        "latitude",
        "longitude",
        mode="before",
    )
    @classmethod
    def blank_to_none(cls, v: Any) -> Any:
        return _empty_to_none(v)


class CompanyLocationResponse(CompanyLocationBase):
    locationId: UUID
    companyId: UUID
    createdAt: datetime
    updatedAt: Optional[datetime] = None
    startDate: Optional[datetime] = None
    endDate: Optional[datetime] = None

    class Config:
        from_attributes = True
