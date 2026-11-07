from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..config.database import Base
import uuid

class Department(Base):
    __tablename__ = 'department'

    departmentId = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thName = Column(String, nullable=False)
    engName = Column(String, nullable=False)
    companyId = Column(UUID(as_uuid=True), ForeignKey('company.companyId', ondelete="CASCADE"), nullable=False)
    shiftId = Column("shift_id", UUID(as_uuid=True), nullable=True)
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), onupdate=func.now())
    deletedAt = Column("deleted_at", DateTime(timezone=True), nullable=True)

    company = relationship("Company", back_populates="departments")
    companyEmployees = relationship("CompanyEmployee", back_populates="department")
