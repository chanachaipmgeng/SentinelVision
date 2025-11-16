from sqlalchemy import Column, String, Integer, DateTime, Text , Enum
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
    role = Column(Enum(RoleType), nullable=False, default=RoleType.MEMBER)  # Default as Enum instance
    status = Column(Enum(StatusType), nullable=False, default=StatusType.ENABLE)  # Default as Enum instance
    picture = Column(String)
    faceEmbedding = Column(Text, nullable=True)  # เก็บข้อมูล Face Embedding
    createdAt = Column(DateTime, nullable=False, default=datetime.utcnow)
    updatedAt = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    companyEmployees = relationship("CompanyEmployee", back_populates="member")

    # ฟังก์ชันเพื่อแฮชรหัสผ่านก่อนบันทึก
    def hash_password(self, password):
        self.passwordHash = bcrypt.hash(password)

    # ฟังก์ชันเพื่อตรวจสอบรหัสผ่าน
    def verify_password(self, password):
        return bcrypt.verify(password, self.passwordHash)

