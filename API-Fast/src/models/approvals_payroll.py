"""C4/C5 models: thin approvals (regularization, leave balance, OT) + payroll period lock."""
from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from ..config.database import Base


class ApprovalRequestStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class PayrollPeriodStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    LOCKED = "LOCKED"


class LeaveBalance(Base):
    __tablename__ = "leave_balance"

    balanceId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    company_employeeId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company_employee.company_employeeId", ondelete="CASCADE"),
        nullable=False,
    )
    leaveType: Mapped[str] = mapped_column(String(30), nullable=False, default="ANNUAL")
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    entitledDays: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    usedDays: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index(
            "uq_leave_balance_emp_type_year",
            "companyId",
            "company_employeeId",
            "leaveType",
            "year",
            unique=True,
        ),
        Index("leave_balance_company_emp_idx", "companyId", "company_employeeId"),
    )

    @property
    def remainingDays(self) -> float:
        return float(self.entitledDays or 0) - float(self.usedDays or 0)


class RegularizationRequest(Base):
    """Employee request to correct / insert a punch (attendance regularization)."""

    __tablename__ = "regularization_request"

    requestId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    company_employeeId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company_employee.company_employeeId", ondelete="CASCADE"),
        nullable=False,
    )
    workDate: Mapped[date] = mapped_column(Date, nullable=False)
    requestedTimestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    requestedType: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ApprovalRequestStatus.PENDING.value, server_default="PENDING"
    )
    originalTimestampId: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    approvedBy: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    approvedAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejectReason: Mapped[str | None] = mapped_column(String, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("regularization_company_status_idx", "companyId", "status"),
        Index("regularization_company_emp_date_idx", "companyId", "company_employeeId", "workDate"),
    )


class OtApprovalRequest(Base):
    """OT approval tied to WorkShift.otThresholdMinutes when that column is present."""

    __tablename__ = "ot_approval_request"

    requestId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    company_employeeId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company_employee.company_employeeId", ondelete="CASCADE"),
        nullable=False,
    )
    workDate: Mapped[date] = mapped_column(Date, nullable=False)
    otMinutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    thresholdMinutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ApprovalRequestStatus.PENDING.value, server_default="PENDING"
    )
    requiresApproval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    approvedBy: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    approvedAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejectReason: Mapped[str | None] = mapped_column(String, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ot_approval_company_status_idx", "companyId", "status"),
        Index("ot_approval_company_emp_date_idx", "companyId", "company_employeeId", "workDate"),
    )


class PayrollPeriod(Base):
    __tablename__ = "payroll_period"

    periodId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    startDate: Mapped[date] = mapped_column(Date, nullable=False)
    endDate: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=PayrollPeriodStatus.OPEN.value, server_default="OPEN"
    )
    lockedAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lockedBy: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index(
            "uq_payroll_period_range",
            "companyId",
            "startDate",
            "endDate",
            unique=True,
        ),
        Index("payroll_period_company_status_idx", "companyId", "status"),
    )
