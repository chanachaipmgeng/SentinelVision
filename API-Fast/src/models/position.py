from sqlalchemy import Column, String, ForeignKey , DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from ..config.database import Base
from sqlalchemy.sql import func
import uuid

class Position(Base):
    __tablename__ = 'position'

    positionId = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thName = Column(String, nullable=False)
    engName = Column(String, nullable=False)
    companyId = Column(UUID(as_uuid=True), ForeignKey('company.companyId', ondelete="CASCADE"), nullable=False)
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), onupdate=func.now())
    deletedAt = Column("deleted_at", DateTime(timezone=True), nullable=True)

    # ความสัมพันธ์กับ Company
    company = relationship("Company", back_populates="positions")
    companyEmployees = relationship("CompanyEmployee", back_populates="position")
