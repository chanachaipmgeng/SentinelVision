"""C1: persisted per-employee daily attendance summary (Asia/Bangkok work date)."""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId = Column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    # Stores company_employee.company_employeeId (contract column name: employeeId).
    employeeId = Column(
        UUID(as_uuid=True),
        ForeignKey("company_employee.company_employeeId", ondelete="CASCADE"),
        nullable=False,
    )
    workDate = Column("work_date", Date, nullable=False)
    firstIn = Column("first_in", DateTime(timezone=True), nullable=True)
    lastOut = Column("last_out", DateTime(timezone=True), nullable=True)
    workMinutes = Column("work_minutes", Integer, nullable=False, default=0, server_default="0")
    breakMinutes = Column("break_minutes", Integer, nullable=False, default=0, server_default="0")
    lateMinutes = Column("late_minutes", Integer, nullable=False, default=0, server_default="0")
    otMinutes = Column("ot_minutes", Integer, nullable=False, default=0, server_default="0")
    status = Column(String(20), nullable=False, default=AttendanceDailyStatus.ABSENT.value)
    createdAt = Column("created_at", DateTime(timezone=True), server_default=func.now())
    updatedAt = Column("updated_at", DateTime(timezone=True), onupdate=func.now())

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
