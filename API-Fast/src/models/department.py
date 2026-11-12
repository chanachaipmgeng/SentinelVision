from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..config.database import Base

if TYPE_CHECKING:
    from .company import Company
    from .company_employee import CompanyEmployee


class Department(Base):
    __tablename__ = "department"

    departmentId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thName: Mapped[str] = mapped_column(String, nullable=False)
    engName: Mapped[str] = mapped_column(String, nullable=False)
    companyId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("company.companyId", ondelete="CASCADE"), nullable=False
    )
    shiftId: Mapped[uuid.UUID | None] = mapped_column("shift_id", UUID(as_uuid=True), nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now())
    deletedAt: Mapped[datetime | None] = mapped_column("deleted_at", DateTime(timezone=True), nullable=True)

    company: Mapped["Company"] = relationship("Company", back_populates="departments")
    companyEmployees: Mapped[list["CompanyEmployee"]] = relationship("CompanyEmployee", back_populates="department")
