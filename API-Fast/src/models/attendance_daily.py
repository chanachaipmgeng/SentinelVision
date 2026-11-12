"""C1: persisted per-employee daily attendance summary (Asia/Bangkok work date)."""
from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from ..config.database import Base


class AttendanceDailyStatus(str, enum.Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    LEAVE = "LEAVE"
    HOLIDAY = "HOLIDAY"
    WFH = "WFH"


class AttendanceDaily(Base):
    __tablename__ = "attendance_daily"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    employeeId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company_employee.company_employeeId", ondelete="CASCADE"),
        nullable=False,
    )
    workDate: Mapped[date] = mapped_column("work_date", Date, nullable=False)
    firstIn: Mapped[datetime | None] = mapped_column("first_in", DateTime(timezone=True), nullable=True)
    lastOut: Mapped[datetime | None] = mapped_column("last_out", DateTime(timezone=True), nullable=True)
    workMinutes: Mapped[int] = mapped_column(
        "work_minutes", Integer, nullable=False, default=0, server_default="0"
    )
    breakMinutes: Mapped[int] = mapped_column(
        "break_minutes", Integer, nullable=False, default=0, server_default="0"
    )
    lateMinutes: Mapped[int] = mapped_column(
        "late_minutes", Integer, nullable=False, default=0, server_default="0"
    )
    otMinutes: Mapped[int] = mapped_column("ot_minutes", Integer, nullable=False, default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=AttendanceDailyStatus.ABSENT.value)
    createdAt: Mapped[datetime] = mapped_column("created_at", DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column("updated_at", DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index(
            "attendance_daily_company_emp_date_uidx",
            "companyId",
            "employeeId",
            "work_date",
            unique=True,
        ),
        Index("attendance_daily_company_date_idx", "companyId", "work_date"),
    )
