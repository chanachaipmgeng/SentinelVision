from __future__ import annotations

import enum
from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from passlib.hash import bcrypt
from sqlalchemy import Boolean, Date, DateTime, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..config.database import Base

if TYPE_CHECKING:
    from .company_employee import CompanyEmployee
    from .face_encoding import FaceEncoding


class RoleType(enum.Enum):
    MEMBER = 0
    ADMIN_COMPANY = 1
    ADMIN_SYSTEM = 99


class StatusType(enum.Enum):
    ENABLE = 1
    DISABLED = 0


class Member(Base):
    __tablename__ = "member"

    memberId: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    username: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    passwordHash: Mapped[str] = mapped_column(String, nullable=False)
    firstName: Mapped[str | None] = mapped_column(String, nullable=True)
    lastName: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    phoneNumber: Mapped[str | None] = mapped_column(String, nullable=True)
    role: Mapped[RoleType] = mapped_column(Enum(RoleType), nullable=False, default=RoleType.MEMBER)
    status: Mapped[StatusType] = mapped_column(Enum(StatusType), nullable=False, default=StatusType.ENABLE)
    picture: Mapped[str | None] = mapped_column(String)
    birthDate: Mapped[date | None] = mapped_column("birth_date", Date, nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    emergencyContactName: Mapped[str | None] = mapped_column("emergency_contact_name", String, nullable=True)
    emergencyContactPhone: Mapped[str | None] = mapped_column("emergency_contact_phone", String, nullable=True)
    attachmentUrls: Mapped[str | None] = mapped_column("attachment_urls", Text, nullable=True)
    mustChangePassword: Mapped[bool] = mapped_column(
        "must_change_password", Boolean, nullable=False, default=False, server_default="false"
    )
    failedLoginCount: Mapped[int] = mapped_column(
        "failed_login_count", Integer, nullable=False, default=0, server_default="0"
    )
    lockedUntil: Mapped[datetime | None] = mapped_column("locked_until", DateTime(timezone=True), nullable=True)
    biometricConsentAt: Mapped[datetime | None] = mapped_column(
        "biometric_consent_at", DateTime(timezone=True), nullable=True
    )
    biometricConsentVersion: Mapped[str | None] = mapped_column("biometric_consent_version", String(40), nullable=True)
    biometricConsentText: Mapped[str | None] = mapped_column("biometric_consent_text", Text, nullable=True)
    totpSecret: Mapped[str | None] = mapped_column("totp_secret", String(128), nullable=True)
    totpEnabled: Mapped[bool] = mapped_column(
        "totp_enabled", Boolean, nullable=False, default=False, server_default="false"
    )
    deletedAt: Mapped[datetime | None] = mapped_column("deleted_at", DateTime(timezone=True), nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updatedAt: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    companyEmployees: Mapped[list["CompanyEmployee"]] = relationship("CompanyEmployee", back_populates="member")
    face_encodings: Mapped[list["FaceEncoding"]] = relationship(
        "FaceEncoding", back_populates="member", cascade="all, delete-orphan"
    )

    def hash_password(self, password: str) -> None:
        self.passwordHash = bcrypt.hash(password)

    def verify_password(self, password: str) -> bool:
        return bcrypt.verify(password, self.passwordHash)
