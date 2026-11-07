from sqlalchemy import Column, String, Integer, DateTime, Date, Text, Enum, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from ..config.database import Base
from uuid import uuid4
from passlib.hash import bcrypt
from datetime import datetime
from sqlalchemy.orm import relationship
import enum

class RoleType(enum.Enum):
    MEMBER = 0
    ADMIN_COMPANY = 1
    ADMIN_SYSTEM = 99

class StatusType(enum.Enum):
    ENABLE = 1
    DISABLED = 0
    
class Member(Base):
    __tablename__ = 'member'

    memberId = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    username = Column(String, nullable=False, unique=True)
    passwordHash = Column(String, nullable=False)
    firstName = Column(String, nullable=True)
    lastName = Column(String, nullable=True)
    email = Column(String, nullable=False, unique=True)
    phoneNumber = Column(String, nullable=True)
    role = Column(Enum(RoleType), nullable=False, default=RoleType.MEMBER)
    status = Column(Enum(StatusType), nullable=False, default=StatusType.ENABLE)
    picture = Column(String)
    birthDate = Column("birth_date", Date, nullable=True)
    address = Column(Text, nullable=True)
    emergencyContactName = Column("emergency_contact_name", String, nullable=True)
    emergencyContactPhone = Column("emergency_contact_phone", String, nullable=True)
    attachmentUrls = Column("attachment_urls", Text, nullable=True)
    mustChangePassword = Column("must_change_password", Boolean, nullable=False, default=False, server_default="false")
    failedLoginCount = Column("failed_login_count", Integer, nullable=False, default=0, server_default="0")
    lockedUntil = Column("locked_until", DateTime(timezone=True), nullable=True)
    biometricConsentAt = Column("biometric_consent_at", DateTime(timezone=True), nullable=True)
    totpSecret = Column("totp_secret", String(128), nullable=True)
    totpEnabled = Column("totp_enabled", Boolean, nullable=False, default=False, server_default="false")
    deletedAt = Column("deleted_at", DateTime(timezone=True), nullable=True)
    createdAt = Column(DateTime, nullable=False, default=datetime.utcnow)
    updatedAt = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    companyEmployees = relationship("CompanyEmployee", back_populates="member")
    face_encodings = relationship("FaceEncoding", back_populates="member", cascade="all, delete-orphan")

    def hash_password(self, password):
        self.passwordHash = bcrypt.hash(password)

    def verify_password(self, password):
        return bcrypt.verify(password, self.passwordHash)
