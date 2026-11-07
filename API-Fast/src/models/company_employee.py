from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Enum, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..config.database import Base
import uuid
import enum

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
    __tablename__ = 'company_employee'

    company_employeeId = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    memberId = Column(UUID(as_uuid=True), ForeignKey('member.memberId'), nullable=False)
    companyId = Column(UUID(as_uuid=True), ForeignKey('company.companyId'), nullable=False)
    positionId = Column(UUID(as_uuid=True), ForeignKey('position.positionId'), nullable=False)
    departmentId = Column(UUID(as_uuid=True), ForeignKey('department.departmentId'), nullable=False)
    shiftId = Column("shift_id", UUID(as_uuid=True), nullable=True)
    employeeId = Column(String, nullable=True, default="")
    startDate = Column(DateTime(timezone=True), server_default=func.now())
    empType = Column(Enum(EmpType), nullable=False, default=EmpType.PERMONTH)
    companyRoleType = Column(Enum(CompanyRoleType), nullable=False, default=CompanyRoleType.EMP)
    salary = Column(Float, nullable=False, default=0)
    bossId = Column(String, nullable=True, default="")
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), onupdate=func.now())
    deletedAt = Column("deleted_at", DateTime(timezone=True), nullable=True)

    member = relationship("Member", back_populates="companyEmployees")
    company = relationship("Company", back_populates="companyEmployees")
    position = relationship("Position", back_populates="companyEmployees")
    department = relationship("Department", back_populates="companyEmployees")
    timestamps = relationship("EmployeeTimestamp", back_populates="company_employee", cascade="all, delete-orphan")
