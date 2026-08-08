from datetime import datetime

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB

from ..config.database import Base


class SystemSetting(Base):
    """Global key/value settings shared by all companies."""

    __tablename__ = "system_setting"

    key = Column(String, primary_key=True)
    value = Column(JSONB, nullable=False, default=dict)
    updatedAt = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
