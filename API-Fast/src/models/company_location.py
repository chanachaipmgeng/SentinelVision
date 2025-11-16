from sqlalchemy import Column, String, DateTime, Float, ForeignKey , Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from ..config.database import Base
import uuid
import enum
class LocationType(enum.Enum):
    PERMANENT = 0
    TEMPORARY = 1
    
class CompanyLocation(Base):
    __tablename__ = 'company_location'

    locationId = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId = Column(UUID(as_uuid=True), ForeignKey('company.companyId'), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    locationName = Column(String, nullable=False)
    radius = Column(Float, nullable=False ,default=0.5)
    locationType = Column(Enum(LocationType), nullable=False, default=LocationType.PERMANENT)
    startDate = Column(DateTime(timezone=True), server_default=func.now())
    endDate = Column(DateTime(timezone=True), server_default=func.now())
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), onupdate=func.now())
