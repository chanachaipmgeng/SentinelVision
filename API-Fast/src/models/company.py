from sqlalchemy import Column, String, DateTime, Enum, Float, Integer, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from ..config.database import Base
import uuid
import enum
from datetime import datetime


class PublicType(enum.Enum):
    PUBLIC = 1
    PENDING = 0


class LifecycleStatus:
    """Tenant lifecycle (string column; not a PG enum so D1 can still evolve freely)."""

    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    OFFBOARDED = "OFFBOARDED"
    ALL = (ACTIVE, SUSPENDED, OFFBOARDED)


class Company(Base):
    __tablename__ = "company"

    companyId = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyName = Column(String, nullable=False, unique=True)
    companyCode = Column(String, nullable=False, unique=True)
    companyInfo = Column(String, nullable=False)
    picture = Column(String)
    address = Column(String, nullable=False)
    latitude = Column(Float, nullable=False, default=0.00)
    longitude = Column(Float, nullable=False, default=0.00)
    status = Column(Enum(PublicType), nullable=False, default=PublicType.PUBLIC)
    createdAt = Column(DateTime, nullable=False, default=datetime.utcnow)
    updatedAt = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deletedAt = Column("deleted_at", DateTime(timezone=True), nullable=True)
    ownerName = Column(String, default="")
    contact = Column(String, default="")

    # D5 tenant lifecycle + quotas
    lifecycleStatus = Column(
        "lifecycle_status", String(20), nullable=False, default=LifecycleStatus.ACTIVE, server_default="ACTIVE"
    )
    suspendedAt = Column("suspended_at", DateTime(timezone=True), nullable=True)
    offboardedAt = Column("offboarded_at", DateTime(timezone=True), nullable=True)
    maxDevices = Column("max_devices", Integer, nullable=True)
    maxEmployees = Column("max_employees", Integer, nullable=True)
    gpuPriority = Column("gpu_priority", Integer, nullable=False, default=0, server_default="0")
    packageCode = Column("package_code", String(64), nullable=True)

    __table_args__ = (
        Index(
            "company_lifecycle_idx",
            "lifecycle_status",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    departments = relationship("Department", back_populates="company", cascade="all, delete")
    positions = relationship("Position", back_populates="company", cascade="all, delete")
    companyEmployees = relationship("CompanyEmployee", back_populates="company")