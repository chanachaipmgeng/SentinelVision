from __future__ import annotations

import uuid
from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from ..config.database import Base


class WorkShift(Base):
    __tablename__ = "work_shift"

    shiftId = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId = Column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(100), nullable=False)
    startTime = Column("start_time", String(10), nullable=False, default="09:00")
    endTime = Column("end_time", String(10), nullable=False, default="18:00")
    graceMinutes = Column("grace_minutes", Integer, nullable=False, default=15)
    isCrossMidnight = Column("is_cross_midnight", Boolean, nullable=False, default=False)
    isDefault = Column("is_default", Boolean, nullable=False, default=False)
    createdAt = Column("created_at", DateTime(timezone=True), server_default=func.now())
    updatedAt = Column("updated_at", DateTime(timezone=True), onupdate=func.now())
    deletedAt = Column("deleted_at", DateTime(timezone=True), nullable=True)


class CompanyHoliday(Base):
    __tablename__ = "company_holiday"

    holidayId = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId = Column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    holidayDate = Column("holiday_date", Date, nullable=False)
    name = Column(String(150), nullable=False)
    createdAt = Column("created_at", DateTime(timezone=True), server_default=func.now())
    deletedAt = Column("deleted_at", DateTime(timezone=True), nullable=True)


class LeaveRequest(Base):
    __tablename__ = "leave_request"

    leaveId = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
    leaveType = Column("leave_type", String(30), nullable=False, default="ANNUAL")
    startDate = Column("start_date", Date, nullable=False)
    endDate = Column("end_date", Date, nullable=False)
    reason = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="PENDING")
    approvedBy = Column("approved_by", UUID(as_uuid=True), nullable=True)
    approvedAt = Column("approved_at", DateTime(timezone=True), nullable=True)
    rejectReason = Column("reject_reason", String, nullable=True)
    createdAt = Column("created_at", DateTime(timezone=True), server_default=func.now())
    updatedAt = Column("updated_at", DateTime(timezone=True), onupdate=func.now())


class KioskDevice(Base):
    __tablename__ = "kiosk_device"

    deviceId = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId = Column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    locationId = Column("location_id", UUID(as_uuid=True), nullable=True)
    name = Column(String(120), nullable=False)
    tokenHash = Column("token_hash", String(128), nullable=False)
    lastSeenAt = Column("last_seen_at", DateTime(timezone=True), nullable=True)
    revokedAt = Column("revoked_at", DateTime(timezone=True), nullable=True)
    createdAt = Column("created_at", DateTime(timezone=True), server_default=func.now())
