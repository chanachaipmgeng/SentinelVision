"""C4/C5 models: thin approvals (regularization, leave balance, OT) + payroll period lock."""
from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
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
    approvalLevel: Mapped[int] = mapped_column("approval_level", Integer, nullable=False, default=1, server_default="1")
    maxApprovalLevel: Mapped[int] = mapped_column(
        "max_approval_level", Integer, nullable=False, default=1, server_default="1"
    )
    approvalHistory: Mapped[Any] = mapped_column(
        "approval_history",
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
        default=list,
    )
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
    approvalLevel: Mapped[int] = mapped_column("approval_level", Integer, nullable=False, default=1, server_default="1")
    maxApprovalLevel: Mapped[int] = mapped_column(
        "max_approval_level", Integer, nullable=False, default=1, server_default="1"
    )
    approvalHistory: Mapped[Any] = mapped_column(
        "approval_history",
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
        default=list,
    )
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


class ApprovalPolicy(Base):
    """Multi-level approval chain configuration per company and request type."""

    __tablename__ = "approval_policy"

    policyId: Mapped[uuid.UUID] = mapped_column(
        "policy_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    companyId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    requestType: Mapped[str] = mapped_column(
        "request_type", String(30), nullable=False, default="ALL", server_default="ALL"
    )
    levels: Mapped[Any] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
        default=list,
    )
    isActive: Mapped[bool] = mapped_column(
        "is_active", Boolean, nullable=False, default=True, server_default="true"
    )
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("uq_approval_policy_company_type", "companyId", "request_type", unique=True),
    )


class ApprovalDelegation(Base):
    """Delegate approver assignment when a manager/approver is on leave."""

    __tablename__ = "approval_delegation"

    delegationId: Mapped[uuid.UUID] = mapped_column(
        "delegation_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    companyId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    delegatorMemberId: Mapped[uuid.UUID] = mapped_column(
        "delegator_member_id",
        UUID(as_uuid=True),
        ForeignKey("member.memberId", ondelete="CASCADE"),
        nullable=False,
    )
    delegateMemberId: Mapped[uuid.UUID] = mapped_column(
        "delegate_member_id",
        UUID(as_uuid=True),
        ForeignKey("member.memberId", ondelete="CASCADE"),
        nullable=False,
    )
    startDate: Mapped[date] = mapped_column("start_date", Date, nullable=False)
    endDate: Mapped[date] = mapped_column("end_date", Date, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    isActive: Mapped[bool] = mapped_column(
        "is_active", Boolean, nullable=False, default=True, server_default="true"
    )
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("approval_delegation_company_delegate_idx", "companyId", "delegate_member_id", "is_active"),
        Index("approval_delegation_company_delegator_idx", "companyId", "delegator_member_id", "is_active"),
    )
