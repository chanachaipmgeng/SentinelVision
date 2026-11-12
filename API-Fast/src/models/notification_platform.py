"""D3 notification platform models — templates, user prefs, in-app inbox."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from ..config.database import Base


class NotificationTemplate(Base):
    __tablename__ = "notification_template"

    templateId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=True,
    )
    eventKey: Mapped[str] = mapped_column(String(80), nullable=False)
    locale: Mapped[str] = mapped_column(String(10), nullable=False, default="th")
    channel: Mapped[str] = mapped_column(String(20), nullable=False, default="line")
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bodyTemplate: Mapped[str] = mapped_column(Text, nullable=False)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now())

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

    preferenceId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    memberId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("member.memberId", ondelete="CASCADE"),
        nullable=False,
    )
    channelEmail: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    channelLine: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    channelInApp: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    lineUserId: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mutedEvents: Mapped[Any] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    locale: Mapped[str] = mapped_column(String(10), nullable=False, default="th")
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now())

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

    notificationId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    memberId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("member.memberId", ondelete="CASCADE"),
        nullable=False,
    )
    event: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    readAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("in_app_notification_member_created_idx", "memberId", "createdAt"),
        Index("in_app_notification_company_unread_idx", "companyId", "memberId"),
    )
