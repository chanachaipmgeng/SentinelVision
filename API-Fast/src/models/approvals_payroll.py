"""C4/C5 models: thin approvals (regularization, leave balance, OT) + payroll period lock."""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
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

    balanceId = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId = Column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    company_employeeId = Column(
        UUID(as_uuid=True),
        ForeignKey("company_employee.company_employeeId", ondelete="CASCADE"),
        nullable=False,
    )
    leaveType = Column(String(30), nullable=False, default="ANNUAL")
    year = Column(Integer, nullable=False)
    entitledDays = Column(Float, nullable=False, default=0)
    usedDays = Column(Float, nullable=False, default=0)
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), onupdate=func.now())

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

    requestId = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId = Column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    company_employeeId = Column(
        UUID(as_uuid=True),
        ForeignKey("company_employee.company_employeeId", ondelete="CASCADE"),
        nullable=False,
    )
    workDate = Column(Date, nullable=False)
    requestedTimestamp = Column(DateTime(timezone=True), nullable=False)
    requestedType = Column(Integer, nullable=False, default=1)  # TimestampType value
    reason = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default=ApprovalRequestStatus.PENDING.value, server_default="PENDING")
    originalTimestampId = Column(UUID(as_uuid=True), nullable=True)
    approvedBy = Column(UUID(as_uuid=True), nullable=True)
    approvedAt = Column(DateTime(timezone=True), nullable=True)
    rejectReason = Column(String, nullable=True)
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("regularization_company_status_idx", "companyId", "status"),
        Index("regularization_company_emp_date_idx", "companyId", "company_employeeId", "workDate"),
    )


class OtApprovalRequest(Base):
    """OT approval tied to WorkShift.otThresholdMinutes when that column is present."""

    __tablename__ = "ot_approval_request"

    requestId = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId = Column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    company_employeeId = Column(
        UUID(as_uuid=True),
        ForeignKey("company_employee.company_employeeId", ondelete="CASCADE"),
        nullable=False,
    )
    workDate = Column(Date, nullable=False)
    otMinutes = Column(Integer, nullable=False, default=0)
    thresholdMinutes = Column(Integer, nullable=True)
    reason = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default=ApprovalRequestStatus.PENDING.value, server_default="PENDING")
    requiresApproval = Column(Boolean, nullable=False, default=True, server_default="true")
    approvedBy = Column(UUID(as_uuid=True), nullable=True)
    approvedAt = Column(DateTime(timezone=True), nullable=True)
    rejectReason = Column(String, nullable=True)
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("ot_approval_company_status_idx", "companyId", "status"),
        Index("ot_approval_company_emp_date_idx", "companyId", "company_employeeId", "workDate"),
    )


class PayrollPeriod(Base):
    __tablename__ = "payroll_period"

    periodId = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId = Column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(120), nullable=True)
    startDate = Column(Date, nullable=False)
    endDate = Column(Date, nullable=False)
    status = Column(String(20), nullable=False, default=PayrollPeriodStatus.OPEN.value, server_default="OPEN")
    lockedAt = Column(DateTime(timezone=True), nullable=True)
    lockedBy = Column(UUID(as_uuid=True), nullable=True)
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), onupdate=func.now())

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
