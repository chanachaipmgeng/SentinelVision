"""Event / continuous video clip metadata (Phase 4 workstream B)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from ..config.database import Base

CLIP_KIND_EVENT = "event"
CLIP_KIND_CONTINUOUS_REF = "continuous_ref"
VALID_CLIP_KINDS = (CLIP_KIND_EVENT, CLIP_KIND_CONTINUOUS_REF)


class VideoClip(Base):
    """Company-scoped clip row. ``event`` rows own bytes in storage; ``continuous_ref``
    points at a MediaMTX recording segment without duplicating punch-photo policy."""

    __tablename__ = "video_clip"

    clipId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    cameraId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("camera.cameraId", ondelete="CASCADE"),
        nullable=False,
    )
    incidentId: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sentinel_incident_log.incidentId", ondelete="SET NULL"),
        nullable=True,
    )
    startedAt: Mapped[datetime] = mapped_column("started_at", DateTime(timezone=True), nullable=False)
    endedAt: Mapped[datetime] = mapped_column("ended_at", DateTime(timezone=True), nullable=False)
    storageKey: Mapped[str] = mapped_column("storage_key", String(512), nullable=False)
    durationMs: Mapped[int] = mapped_column(
        "duration_ms", BigInteger, nullable=False, default=0, server_default="0"
    )
    kind: Mapped[str] = mapped_column(
        String(32), nullable=False, default=CLIP_KIND_EVENT, server_default=CLIP_KIND_EVENT
    )
    createdAt: Mapped[datetime] = mapped_column("created_at", DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("video_clip_company_started_idx", "companyId", "started_at"),
        Index("video_clip_company_camera_idx", "companyId", "cameraId"),
        Index("video_clip_company_incident_idx", "companyId", "incidentId"),
        Index("video_clip_company_kind_idx", "companyId", "kind"),
        Index("video_clip_storage_key_uidx", "companyId", "storage_key", unique=True),
    )
