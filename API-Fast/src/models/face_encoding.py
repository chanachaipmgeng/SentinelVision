from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..config.database import Base
from uuid import uuid4
from datetime import datetime

class FaceEncoding(Base):
    __tablename__ = 'face_encoding'

    faceEncodingId = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    memberId = Column(UUID(as_uuid=True), ForeignKey('member.memberId'), nullable=False)
    encoding = Column(Text, nullable=False)  # Stores the JSON string of the encoding vector
    createdAt = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationship to the Member model
    member = relationship("Member", back_populates="face_encodings")
