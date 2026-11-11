"""IP / RTSP camera registry for MediaMTX live wall (Phase 3)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from ..config.database import Base


class Camera(Base):
    """Company-scoped CCTV camera. Live paths sync into MediaMTX; AI comes in Phase 4."""

    __tablename__ = "camera"

    cameraId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    streamUrl: Mapped[str] = mapped_column("stream_url", Text, nullable=False)
    protocol: Mapped[str] = mapped_column(String(20), nullable=False, default="rtsp", server_default="rtsp")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    credentialsEnc: Mapped[str | None] = mapped_column("credentials_enc", Text, nullable=True)
    siteFloorId: Mapped[uuid.UUID | None] = mapped_column(
        "site_floor_id",
        UUID(as_uuid=True),
        ForeignKey("site_floor.siteFloorId", ondelete="SET NULL"),
        nullable=True,
    )
    zoneId: Mapped[uuid.UUID | None] = mapped_column("zone_id", UUID(as_uuid=True), nullable=True)
    stationMode: Mapped[str | None] = mapped_column("station_mode", String(30), nullable=True)
    mapPosX: Mapped[float | None] = mapped_column("map_pos_x", Float, nullable=True)
    mapPosY: Mapped[float | None] = mapped_column("map_pos_y", Float, nullable=True)
    recordMode: Mapped[str] = mapped_column(
        "record_mode", String(20), nullable=False, default="event", server_default="event"
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown", server_default="unknown")
    lastPingAt: Mapped[datetime | None] = mapped_column("last_ping_at", DateTime(timezone=True), nullable=True)
    lastPingLatencyMs: Mapped[float | None] = mapped_column("last_ping_latency_ms", Float, nullable=True)
    previewImageUrl: Mapped[str | None] = mapped_column("preview_image_url", String(255), nullable=True)
    isActive: Mapped[bool] = mapped_column(
        "is_active", Boolean, nullable=False, default=True, server_default="true"
    )
    analysisEnabled: Mapped[bool] = mapped_column(
        "analysis_enabled", Boolean, nullable=False, default=False, server_default="false"
    )
    lastAnalyzedAt: Mapped[datetime | None] = mapped_column("last_analyzed_at", DateTime(timezone=True), nullable=True)
    aiConfig: Mapped[Any | None] = mapped_column("ai_config", JSONB, nullable=True)
    createdAt: Mapped[datetime] = mapped_column("created_at", DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column("updated_at", DateTime(timezone=True), onupdate=func.now())
    deletedAt: Mapped[datetime | None] = mapped_column("deleted_at", DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("camera_company_active_idx", "companyId", "is_active"),
        Index("camera_company_status_idx", "companyId", "status"),
        Index(
            "camera_analysis_due_idx",
            "analysis_enabled",
            "is_active",
            "last_analyzed_at",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )
