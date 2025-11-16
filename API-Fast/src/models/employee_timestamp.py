from sqlalchemy import Column, String, DateTime, Enum, ForeignKey , Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..config.database import Base
import uuid
import enum

# กำหนดประเภทของการลงเวลา
class TimestampType(enum.Enum):
    CHECK_IN = 1
    CHECK_OUT = 2
    WARNING = 0
    DISAPPROVE = 3

class EmployeeTimestamp(Base):
    __tablename__ = 'employee_timestamp'

    timestampId = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_employeeId = Column(UUID(as_uuid=True), ForeignKey('company_employee.company_employeeId'), nullable=False)
    companyId = Column(UUID(as_uuid=True), ForeignKey('company.companyId'), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    timestampType = Column(Enum(TimestampType), nullable=False,default=TimestampType.CHECK_IN)
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), onupdate=func.now())
    locationName = Column(String, nullable=True, default="")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    photoTimestamp = Column(String, nullable=True)
    
    company_employee = relationship("CompanyEmployee", back_populates="timestamps")
