"""Phase D1 RBAC: roles, permissions, and scoped member assignments."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
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

    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RbacRole(Base):
    __tablename__ = "rbac_role"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    permissions: Mapped[list[RbacRolePermission]] = relationship(
        "RbacRolePermission",
        back_populates="role",
        cascade="all, delete-orphan",
    )
    assignments: Mapped[list[MemberRoleAssignment]] = relationship(
        "MemberRoleAssignment",
        back_populates="role",
        cascade="all, delete-orphan",
    )


class RbacRolePermission(Base):
    __tablename__ = "rbac_role_permission"

    roleCode: Mapped[str] = mapped_column(
        "role_code",
        String(32),
        ForeignKey("rbac_role.code", ondelete="CASCADE"),
        primary_key=True,
    )
    permissionCode: Mapped[str] = mapped_column(
        "permission_code",
        String(64),
        ForeignKey("rbac_permission.code", ondelete="CASCADE"),
        primary_key=True,
    )

    role: Mapped[RbacRole] = relationship("RbacRole", back_populates="permissions")
    permission: Mapped[RbacPermission] = relationship("RbacPermission")


class MemberRoleAssignment(Base):
    """Assign a RBAC role to a member within a company, optionally scoped to one department."""

    __tablename__ = "member_role_assignment"

    assignmentId: Mapped[uuid.UUID] = mapped_column(
        "assignment_id",
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    memberId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("member.memberId", ondelete="CASCADE"),
        nullable=False,
    )
    companyId: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=True,
    )
    roleCode: Mapped[str] = mapped_column(
        "role_code",
        String(32),
        ForeignKey("rbac_role.code", ondelete="CASCADE"),
        nullable=False,
    )
    departmentId: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("department.departmentId", ondelete="CASCADE"),
        nullable=True,
    )
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    role: Mapped[RbacRole] = relationship("RbacRole", back_populates="assignments")

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
