from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..config.database import Base

if TYPE_CHECKING:
    from .company_employee import CompanyEmployee


class TimestampType(enum.Enum):
    CHECK_IN = 1
    CHECK_OUT = 2
    WARNING = 0
    DISAPPROVE = 3
    BREAK_OUT = 4
    BREAK_IN = 5


class ApprovalStatus(str, enum.Enum):
    NONE = "NONE"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class EmployeeTimestamp(Base):
    __tablename__ = "employee_timestamp"

    timestampId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_employeeId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("company_employee.company_employeeId"), nullable=False
    )
    companyId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("company.companyId"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    timestampType: Mapped[TimestampType] = mapped_column(
        Enum(TimestampType), nullable=False, default=TimestampType.CHECK_IN
    )
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now())
    locationName: Mapped[str | None] = mapped_column(String, nullable=True, default="")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    photoTimestamp: Mapped[str | None] = mapped_column(String, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    approvalStatus: Mapped[str] = mapped_column(
        "approval_status",
        String(20),
        nullable=False,
        default=ApprovalStatus.NONE.value,
    )
    approvedBy: Mapped[uuid.UUID | None] = mapped_column(
        "approved_by",
        UUID(as_uuid=True),
        ForeignKey("member.memberId", name="employee_timestamp_approved_by_fkey"),
        nullable=True,
    )
    approvedAt: Mapped[datetime | None] = mapped_column("approved_at", DateTime(timezone=True), nullable=True)
    rejectReason: Mapped[str | None] = mapped_column("reject_reason", String, nullable=True)
    isLate: Mapped[bool] = mapped_column("is_late", Boolean, nullable=False, default=False, server_default="false")
    lateMinutes: Mapped[int] = mapped_column(
        "late_minutes", Integer, nullable=False, default=0, server_default="0"
    )
    overtimeMinutes: Mapped[int] = mapped_column(
        "overtime_minutes", Integer, nullable=False, default=0, server_default="0"
    )
    shiftName: Mapped[str | None] = mapped_column("shift_name", String(100), nullable=True)

    company_employee: Mapped["CompanyEmployee"] = relationship("CompanyEmployee", back_populates="timestamps")

    __table_args__ = (
        Index("employee_timestamp_company_ts_idx", "companyId", "timestamp"),
        Index("employee_timestamp_emp_ts_idx", "company_employeeId", "timestamp"),
    )
