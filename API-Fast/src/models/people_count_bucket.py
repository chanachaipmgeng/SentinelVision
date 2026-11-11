"""Phase 6D: per-camera people-count time buckets (line / zone aggregates)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from ..config.database import Base


class PeopleCountBucket(Base):
    """Minute-level (configurable) aggregates for people counting per camera."""

    __tablename__ = "people_count_bucket"

    bucketId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
    bucketStart: Mapped[datetime] = mapped_column("bucket_start", DateTime(timezone=True), nullable=False)
    inCount: Mapped[int] = mapped_column("in_count", Integer, nullable=False, default=0, server_default="0")
    outCount: Mapped[int] = mapped_column("out_count", Integer, nullable=False, default=0, server_default="0")
    zoneOccupancy: Mapped[int] = mapped_column(
        "zone_occupancy", Integer, nullable=False, default=0, server_default="0"
    )
    crossingCount: Mapped[int] = mapped_column(
        "crossing_count", Integer, nullable=False, default=0, server_default="0"
    )
    detections: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    createdAt: Mapped[datetime] = mapped_column("created_at", DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column("updated_at", DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("cameraId", "bucket_start", name="people_count_bucket_cam_start_uq"),
        Index("people_count_bucket_company_start_idx", "companyId", "bucket_start"),
        Index("people_count_bucket_camera_start_idx", "cameraId", "bucket_start"),
    )
