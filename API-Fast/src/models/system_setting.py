from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..config.database import Base


class SystemSetting(Base):
    """Global key/value settings shared by all companies."""

    __tablename__ = "system_setting"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)
    updatedAt: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
