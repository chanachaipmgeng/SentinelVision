"""IP / RTSP camera registry for MediaMTX live wall (Phase 3)."""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from ..config.database import Base


class Camera(Base):
    """Company-scoped CCTV camera. Live paths sync into MediaMTX; AI comes in Phase 4."""

    __tablename__ = "camera"

    cameraId = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId = Column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(160), nullable=False)
    streamUrl = Column("stream_url", Text, nullable=False)
    protocol = Column(String(20), nullable=False, default="rtsp", server_default="rtsp")
    description = Column(Text, nullable=True)
    # Fernet-sealed JSON: {"username": "...", "password": "..."}
    credentialsEnc = Column("credentials_enc", Text, nullable=True)
    siteFloorId = Column(
        "site_floor_id",
        UUID(as_uuid=True),
        ForeignKey("site_floor.siteFloorId", ondelete="SET NULL"),
        nullable=True,
    )
    zoneId = Column("zone_id", UUID(as_uuid=True), nullable=True)
    stationMode = Column("station_mode", String(30), nullable=True)
    mapPosX = Column("map_pos_x", Float, nullable=True)
    mapPosY = Column("map_pos_y", Float, nullable=True)
    # off | event | continuous — continuous enables MediaMTX path recording
    recordMode = Column("record_mode", String(20), nullable=False, default="event", server_default="event")
    status = Column(String(20), nullable=False, default="unknown", server_default="unknown")
    lastPingAt = Column("last_ping_at", DateTime(timezone=True), nullable=True)
    lastPingLatencyMs = Column("last_ping_latency_ms", Float, nullable=True)
    previewImageUrl = Column("preview_image_url", String(255), nullable=True)
    isActive = Column("is_active", Boolean, nullable=False, default=True, server_default="true")
    # Phase 4A: CCTV → InsightFace worker (opt-in per camera)
    analysisEnabled = Column(
        "analysis_enabled", Boolean, nullable=False, default=False, server_default="false"
    )
    lastAnalyzedAt = Column("last_analyzed_at", DateTime(timezone=True), nullable=True)
    createdAt = Column("created_at", DateTime(timezone=True), server_default=func.now())
    updatedAt = Column("updated_at", DateTime(timezone=True), onupdate=func.now())
    deletedAt = Column("deleted_at", DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("camera_company_active_idx", "companyId", "is_active"),
        Index("camera_company_status_idx", "companyId", "status"),
        # Matches 0021_camera_analysis — CCTV worker due-queue scan.
        Index(
            "camera_analysis_due_idx",
            "analysis_enabled",
            "is_active",
            "last_analyzed_at",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )
