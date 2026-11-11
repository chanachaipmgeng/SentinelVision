from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Float, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..config.database import Base

if TYPE_CHECKING:
    from .company_employee import CompanyEmployee
    from .department import Department
    from .position import Position


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

    companyId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyName: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    companyCode: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    companyInfo: Mapped[str] = mapped_column(String, nullable=False)
    picture: Mapped[str | None] = mapped_column(String)
    address: Mapped[str] = mapped_column(String, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False, default=0.00)
    longitude: Mapped[float] = mapped_column(Float, nullable=False, default=0.00)
    status: Mapped[PublicType] = mapped_column(Enum(PublicType), nullable=False, default=PublicType.PUBLIC)
    createdAt: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updatedAt: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deletedAt: Mapped[datetime | None] = mapped_column("deleted_at", DateTime(timezone=True), nullable=True)
    ownerName: Mapped[str] = mapped_column(String, default="")
    contact: Mapped[str] = mapped_column(String, default="")

    lifecycleStatus: Mapped[str] = mapped_column(
        "lifecycle_status", String(20), nullable=False, default=LifecycleStatus.ACTIVE, server_default="ACTIVE"
    )
    suspendedAt: Mapped[datetime | None] = mapped_column("suspended_at", DateTime(timezone=True), nullable=True)
    offboardedAt: Mapped[datetime | None] = mapped_column("offboarded_at", DateTime(timezone=True), nullable=True)
    maxDevices: Mapped[int | None] = mapped_column("max_devices", Integer, nullable=True)
    maxEmployees: Mapped[int | None] = mapped_column("max_employees", Integer, nullable=True)
    gpuPriority: Mapped[int] = mapped_column(
        "gpu_priority", Integer, nullable=False, default=0, server_default="0"
    )
    packageCode: Mapped[str | None] = mapped_column("package_code", String(64), nullable=True)

    __table_args__ = (
        Index(
            "company_lifecycle_idx",
            "lifecycle_status",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    departments: Mapped[list["Department"]] = relationship("Department", back_populates="company", cascade="all, delete")
    positions: Mapped[list["Position"]] = relationship("Position", back_populates="company", cascade="all, delete")
    companyEmployees: Mapped[list["CompanyEmployee"]] = relationship("CompanyEmployee", back_populates="company")
