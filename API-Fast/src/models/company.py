from sqlalchemy import Column, String, DateTime, Enum , Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from ..config.database import Base
import uuid
import enum
from datetime import datetime
class PublicType(enum.Enum):
    PUBLIC = 1
    PENDING = 0
class Company(Base):
    __tablename__ = 'company'

    companyId = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyName = Column(String, nullable=False, unique=True)
    companyCode = Column(String, nullable=False, unique=True)
    companyInfo = Column(String, nullable=False)
    picture = Column(String)
    address = Column(String, nullable=False)
    latitude = Column(Float, nullable=False, default=0.00)
    longitude = Column(Float, nullable=False, default=0.00)
    status = Column(Enum(PublicType), nullable=False, default=PublicType.PUBLIC)  # Default as Enum instance
    createdAt = Column(DateTime, nullable=False, default=datetime.utcnow)
    updatedAt = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deletedAt = Column("deleted_at", DateTime(timezone=True), nullable=True)
    ownerName = Column(String, default="")
    contact = Column(String, default="")

    # ความสัมพันธ์
    departments = relationship("Department", back_populates="company", cascade="all, delete")
    positions = relationship("Position", back_populates="company", cascade="all, delete")
    companyEmployees = relationship("CompanyEmployee", back_populates="company")