from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..config.database import Base

if TYPE_CHECKING:
    from .company import Company
    from .department import Department
    from .employee_timestamp import EmployeeTimestamp
    from .member import Member
    from .position import Position


class StatusType(enum.Enum):
    ENABLE = 1
    DISABLED = 0


class EmpType(enum.Enum):
    PERMONTH = 1
    PERDAY = 0


class CompanyRoleType(enum.Enum):
    EMP = 0
    ADMIN_COMPANY = 1


class CompanyEmployee(Base):
    __tablename__ = "company_employee"

    company_employeeId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    memberId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("member.memberId"), nullable=False)
    companyId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("company.companyId"), nullable=False)
    positionId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("position.positionId"), nullable=False)
    departmentId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("department.departmentId"), nullable=False
    )
    shiftId: Mapped[uuid.UUID | None] = mapped_column("shift_id", UUID(as_uuid=True), nullable=True)
    employeeId: Mapped[str | None] = mapped_column(String, nullable=True, default="")
    startDate: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    empType: Mapped[EmpType] = mapped_column(Enum(EmpType), nullable=False, default=EmpType.PERMONTH)
    companyRoleType: Mapped[CompanyRoleType] = mapped_column(
        Enum(CompanyRoleType), nullable=False, default=CompanyRoleType.EMP
    )
    salary: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    bossId: Mapped[str | None] = mapped_column(String, nullable=True, default="")
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    deletedAt: Mapped[datetime | None] = mapped_column("deleted_at", DateTime(timezone=True), nullable=True)

    member: Mapped["Member"] = relationship("Member", back_populates="companyEmployees")
    company: Mapped["Company"] = relationship("Company", back_populates="companyEmployees")
    position: Mapped["Position"] = relationship("Position", back_populates="companyEmployees")
    department: Mapped["Department"] = relationship("Department", back_populates="companyEmployees")
    timestamps: Mapped[list["EmployeeTimestamp"]] = relationship(
        "EmployeeTimestamp", back_populates="company_employee", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("uq_company_employee_member_company", "memberId", "companyId", unique=True),
        Index(
            "uq_company_employee_code",
            "companyId",
            "employeeId",
            unique=True,
            postgresql_where=text("\"employeeId\" IS NOT NULL AND \"employeeId\" <> ''"),
        ),
    )
