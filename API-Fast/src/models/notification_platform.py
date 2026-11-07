"""D3 notification platform models — templates, user prefs, in-app inbox."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from ..config.database import Base


class NotificationTemplate(Base):
    __tablename__ = "notification_template"

    templateId = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId = Column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=True,
    )
    eventKey = Column(String(80), nullable=False)
    locale = Column(String(10), nullable=False, default="th")
    channel = Column(String(20), nullable=False, default="line")
    subject = Column(String(255), nullable=True)
    bodyTemplate = Column(Text, nullable=False)
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("notification_template_company_idx", "companyId", "eventKey"),
        Index(
            "uq_notification_template_scope",
            "companyId",
            "eventKey",
            "locale",
            "channel",
            unique=True,
        ),
    )


class NotificationPreference(Base):
    __tablename__ = "notification_preference"

    preferenceId = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId = Column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    memberId = Column(
        UUID(as_uuid=True),
        ForeignKey("member.memberId", ondelete="CASCADE"),
        nullable=False,
    )
    channelEmail = Column(Boolean, nullable=False, default=True, server_default="true")
    channelLine = Column(Boolean, nullable=False, default=True, server_default="true")
    channelInApp = Column(Boolean, nullable=False, default=True, server_default="true")
    lineUserId = Column(String(64), nullable=True)
    mutedEvents = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    locale = Column(String(10), nullable=False, default="th")
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index(
            "uq_notification_preference_member",
            "companyId",
            "memberId",
            unique=True,
        ),
    )


class InAppNotification(Base):
    __tablename__ = "in_app_notification"

    notificationId = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId = Column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    memberId = Column(
        UUID(as_uuid=True),
        ForeignKey("member.memberId", ondelete="CASCADE"),
        nullable=False,
    )
    event = Column(String(80), nullable=False)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    readAt = Column(DateTime(timezone=True), nullable=True)
    createdAt = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("in_app_notification_member_created_idx", "memberId", "createdAt"),
        Index("in_app_notification_company_unread_idx", "companyId", "memberId"),
    )
