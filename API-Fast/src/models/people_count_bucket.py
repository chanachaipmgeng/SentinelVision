"""Phase 6D: per-camera people-count time buckets (line / zone aggregates)."""
from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from ..config.database import Base


class PeopleCountBucket(Base):
    """Minute-level (configurable) aggregates for people counting per camera."""

    __tablename__ = "people_count_bucket"

    bucketId = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId = Column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    cameraId = Column(
        UUID(as_uuid=True),
        ForeignKey("camera.cameraId", ondelete="CASCADE"),
        nullable=False,
    )
    bucketStart = Column("bucket_start", DateTime(timezone=True), nullable=False)
    inCount = Column("in_count", Integer, nullable=False, default=0, server_default="0")
    outCount = Column("out_count", Integer, nullable=False, default=0, server_default="0")
    zoneOccupancy = Column(
        "zone_occupancy", Integer, nullable=False, default=0, server_default="0"
    )
    crossingCount = Column(
        "crossing_count", Integer, nullable=False, default=0, server_default="0"
    )
    detections = Column(Integer, nullable=False, default=0, server_default="0")
    createdAt = Column("created_at", DateTime(timezone=True), server_default=func.now())
    updatedAt = Column("updated_at", DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("cameraId", "bucket_start", name="people_count_bucket_cam_start_uq"),
        Index("people_count_bucket_company_start_idx", "companyId", "bucket_start"),
        Index("people_count_bucket_camera_start_idx", "cameraId", "bucket_start"),
    )
