from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from ..config.database import Base


class WorkShift(Base):
    __tablename__ = "work_shift"

    shiftId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    startTime: Mapped[str] = mapped_column("start_time", String(10), nullable=False, default="09:00")
    endTime: Mapped[str] = mapped_column("end_time", String(10), nullable=False, default="18:00")
    graceMinutes: Mapped[int] = mapped_column("grace_minutes", Integer, nullable=False, default=15)
    roundingMinutes: Mapped[int] = mapped_column("rounding_minutes", Integer, nullable=False, default=0)
    breakMinutes: Mapped[int] = mapped_column("break_minutes", Integer, nullable=False, default=0)
    breakWindows: Mapped[Any] = mapped_column("break_windows", JSONB, nullable=False, default=list)
    otThresholdMinutes: Mapped[int] = mapped_column("ot_threshold_minutes", Integer, nullable=False, default=0)
    isCrossMidnight: Mapped[bool] = mapped_column("is_cross_midnight", Boolean, nullable=False, default=False)
    isDefault: Mapped[bool] = mapped_column("is_default", Boolean, nullable=False, default=False)
    createdAt: Mapped[datetime] = mapped_column("created_at", DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column("updated_at", DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now())
    deletedAt: Mapped[datetime | None] = mapped_column("deleted_at", DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("work_shift_company_idx", "companyId"),)


class CompanyHoliday(Base):
    __tablename__ = "company_holiday"

    holidayId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    holidayDate: Mapped[date] = mapped_column("holiday_date", Date, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="MANUAL", server_default="MANUAL")
    createdAt: Mapped[datetime] = mapped_column("created_at", DateTime(timezone=True), server_default=func.now())
    deletedAt: Mapped[datetime | None] = mapped_column("deleted_at", DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("company_holiday_company_date_idx", "companyId", "holiday_date"),)


class LeaveRequest(Base):
    __tablename__ = "leave_request"

    leaveId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
    leaveType: Mapped[str] = mapped_column("leave_type", String(30), nullable=False, default="ANNUAL")
    startDate: Mapped[date] = mapped_column("start_date", Date, nullable=False)
    endDate: Mapped[date] = mapped_column("end_date", Date, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    approvedBy: Mapped[uuid.UUID | None] = mapped_column("approved_by", UUID(as_uuid=True), nullable=True)
    approvedAt: Mapped[datetime | None] = mapped_column("approved_at", DateTime(timezone=True), nullable=True)
    rejectReason: Mapped[str | None] = mapped_column("reject_reason", String, nullable=True)
    createdAt: Mapped[datetime] = mapped_column("created_at", DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column("updated_at", DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("leave_request_company_dates_idx", "companyId", "start_date", "end_date", "status"),
    )


class KioskDevice(Base):
    __tablename__ = "kiosk_device"

    deviceId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    locationId: Mapped[uuid.UUID | None] = mapped_column("location_id", UUID(as_uuid=True), nullable=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    locationLabel: Mapped[str | None] = mapped_column("location_label", String(255), nullable=True)
    fingerprint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    appVersion: Mapped[str | None] = mapped_column("app_version", String(64), nullable=True)
    heartbeatAt: Mapped[datetime | None] = mapped_column("heartbeat_at", DateTime(timezone=True), nullable=True)
    config: Mapped[Any] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb"), default=dict
    )
    stationMode: Mapped[str | None] = mapped_column("station_mode", String(40), nullable=True)
    zoneId: Mapped[uuid.UUID | None] = mapped_column("zone_id", UUID(as_uuid=True), nullable=True)
    siteFloorId: Mapped[uuid.UUID | None] = mapped_column(
        "site_floor_id",
        UUID(as_uuid=True),
        ForeignKey("site_floor.siteFloorId", ondelete="SET NULL"),
        nullable=True,
    )
    mapPosX: Mapped[float | None] = mapped_column("map_pos_x", Float, nullable=True)
    mapPosY: Mapped[float | None] = mapped_column("map_pos_y", Float, nullable=True)
    tokenHash: Mapped[str | None] = mapped_column("token_hash", String(128), nullable=True)
    tokenFamily: Mapped[str | None] = mapped_column("token_family", String(64), nullable=True)
    pairingCodeHash: Mapped[str | None] = mapped_column("pairing_code_hash", String(128), nullable=True)
    pairingExpiresAt: Mapped[datetime | None] = mapped_column("pairing_expires_at", DateTime(timezone=True), nullable=True)
    pairedAt: Mapped[datetime | None] = mapped_column("paired_at", DateTime(timezone=True), nullable=True)
    lastSeenAt: Mapped[datetime | None] = mapped_column("last_seen_at", DateTime(timezone=True), nullable=True)
    revokedAt: Mapped[datetime | None] = mapped_column("revoked_at", DateTime(timezone=True), nullable=True)
    createdAt: Mapped[datetime] = mapped_column("created_at", DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("kiosk_device_company_idx", "companyId", "revoked_at"),
        Index("kiosk_device_station_mode_idx", "companyId", "station_mode"),
        Index(
            "kiosk_device_zone_idx",
            "companyId",
            "zone_id",
            postgresql_where=text("zone_id IS NOT NULL"),
        ),
        Index(
            "kiosk_device_floor_idx",
            "companyId",
            "site_floor_id",
            postgresql_where=text("site_floor_id IS NOT NULL"),
        ),
        Index(
            "kiosk_device_pairing_code_idx",
            "pairing_code_hash",
            postgresql_where=text("pairing_code_hash IS NOT NULL"),
        ),
    )
