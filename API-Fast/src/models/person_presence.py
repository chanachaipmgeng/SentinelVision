"""Person presence trail: CCTV sightings folded into open camera sessions."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from ..config.database import Base


class PersonSighting(Base):
    """One face match on a camera frame (no embedding / snapshot in Phase 1)."""

    __tablename__ = "person_sighting"

    sightingId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
    cameraId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("camera.cameraId", ondelete="CASCADE"),
        nullable=False,
    )
    zoneId: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    siteFloorId: Mapped[uuid.UUID | None] = mapped_column(
        "site_floor_id",
        UUID(as_uuid=True),
        ForeignKey("site_floor.siteFloorId", ondelete="SET NULL"),
        nullable=True,
    )
    eventId: Mapped[uuid.UUID | None] = mapped_column(
        "event_id",
        UUID(as_uuid=True),
        ForeignKey("sentinel_event.eventId", ondelete="SET NULL"),
        nullable=True,
    )
    seenAt: Mapped[datetime] = mapped_column(
        "seen_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    distance: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        Index("person_sighting_company_member_seen_idx", "companyId", "memberId", seenAt.desc()),
        Index("person_sighting_company_camera_seen_idx", "companyId", "cameraId", seenAt.desc()),
        Index("person_sighting_seen_idx", "seen_at"),
    )


class PersonPresenceSession(Base):
    """Continuous presence of one member on one camera (gap ≤ session fold window)."""

    __tablename__ = "person_presence_session"

    sessionId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
    cameraId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("camera.cameraId", ondelete="CASCADE"),
        nullable=False,
    )
    zoneId: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    siteFloorId: Mapped[uuid.UUID | None] = mapped_column(
        "site_floor_id",
        UUID(as_uuid=True),
        ForeignKey("site_floor.siteFloorId", ondelete="SET NULL"),
        nullable=True,
    )
    eventId: Mapped[uuid.UUID | None] = mapped_column(
        "event_id",
        UUID(as_uuid=True),
        ForeignKey("sentinel_event.eventId", ondelete="SET NULL"),
        nullable=True,
    )
    presenceRole: Mapped[str] = mapped_column(
        "presence_role", String(20), nullable=False, default="LOCATE", server_default="LOCATE"
    )
    startedAt: Mapped[datetime] = mapped_column("started_at", DateTime(timezone=True), nullable=False)
    endedAt: Mapped[datetime | None] = mapped_column("ended_at", DateTime(timezone=True), nullable=True)
    lastSeenAt: Mapped[datetime] = mapped_column("last_seen_at", DateTime(timezone=True), nullable=False)
    sampleCount: Mapped[int] = mapped_column(
        "sample_count", Integer, nullable=False, default=1, server_default="1"
    )
    open: Mapped[bool] = mapped_column(
        "is_open", Boolean, nullable=False, default=True, server_default="true"
    )

    __table_args__ = (
        Index(
            "person_presence_session_company_member_idx",
            "companyId",
            "memberId",
            "last_seen_at",
        ),
        Index(
            "person_presence_session_company_camera_idx",
            "companyId",
            "cameraId",
            "last_seen_at",
        ),
        Index(
            "person_presence_session_open_idx",
            "companyId",
            "memberId",
            "is_open",
            postgresql_where=text("is_open = true"),
        ),
        Index(
            "person_presence_session_event_idx",
            "companyId",
            "event_id",
            "started_at",
            postgresql_where=text("event_id IS NOT NULL"),
        ),
    )
