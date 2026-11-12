from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from ..config.database import Base


class LocationType(enum.Enum):
    PERMANENT = 0
    TEMPORARY = 1


class CompanyLocation(Base):
    __tablename__ = "company_location"

    locationId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("company.companyId"), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    locationName: Mapped[str] = mapped_column(String, nullable=False)
    radius: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    locationType: Mapped[LocationType] = mapped_column(
        Enum(LocationType), nullable=False, default=LocationType.PERMANENT
    )
    startDate: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    endDate: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now())
    deletedAt: Mapped[datetime | None] = mapped_column("deleted_at", DateTime(timezone=True), nullable=True)
