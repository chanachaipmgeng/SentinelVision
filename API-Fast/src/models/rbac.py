"""Phase D1 RBAC: roles, permissions, and scoped member assignments."""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..config.database import Base


class RbacRoleCode(str, enum.Enum):
    SYSTEM_ADMIN = "SYSTEM_ADMIN"
    HR_ADMIN = "HR_ADMIN"
    MANAGER = "MANAGER"
    APPROVER = "APPROVER"
    AUDITOR = "AUDITOR"
    DEVICE_OPERATOR = "DEVICE_OPERATOR"


class RbacPermission(Base):
    __tablename__ = "rbac_permission"

    code = Column(String(64), primary_key=True)
    description = Column(Text, nullable=True)
    createdAt = Column(DateTime(timezone=True), server_default=func.now())


class RbacRole(Base):
    __tablename__ = "rbac_role"

    code = Column(String(32), primary_key=True)
    description = Column(Text, nullable=True)
    createdAt = Column(DateTime(timezone=True), server_default=func.now())

    permissions = relationship(
        "RbacRolePermission",
        back_populates="role",
        cascade="all, delete-orphan",
    )
    assignments = relationship(
        "MemberRoleAssignment",
        back_populates="role",
        cascade="all, delete-orphan",
    )


class RbacRolePermission(Base):
    __tablename__ = "rbac_role_permission"

    roleCode = Column(
        "role_code",
        String(32),
        ForeignKey("rbac_role.code", ondelete="CASCADE"),
        primary_key=True,
    )
    permissionCode = Column(
        "permission_code",
        String(64),
        ForeignKey("rbac_permission.code", ondelete="CASCADE"),
        primary_key=True,
    )

    role = relationship("RbacRole", back_populates="permissions")
    permission = relationship("RbacPermission")


class MemberRoleAssignment(Base):
    """Assign a RBAC role to a member within a company, optionally scoped to one department."""

    __tablename__ = "member_role_assignment"

    assignmentId = Column(
        "assignment_id",
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    memberId = Column(
        UUID(as_uuid=True),
        ForeignKey("member.memberId", ondelete="CASCADE"),
        nullable=False,
    )
    companyId = Column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=True,
    )
    roleCode = Column(
        "role_code",
        String(32),
        ForeignKey("rbac_role.code", ondelete="CASCADE"),
        nullable=False,
    )
    departmentId = Column(
        UUID(as_uuid=True),
        ForeignKey("department.departmentId", ondelete="CASCADE"),
        nullable=True,
    )
    createdAt = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updatedAt = Column(DateTime(timezone=True), onupdate=func.now())

    role = relationship("RbacRole", back_populates="assignments")

    __table_args__ = (
        UniqueConstraint(
            "memberId",
            "companyId",
            "role_code",
            "departmentId",
            name="uq_member_role_scope",
        ),
        Index("member_role_member_company_idx", "memberId", "companyId"),
        Index("member_role_company_role_idx", "companyId", "role_code"),
    )
