"""Site floor plan registry for E-Map pins (Phase 2)."""
from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from ..config.database import Base


class SiteFloor(Base):
    """Company-scoped floor with optional plan image for Leaflet E-Map."""

    __tablename__ = "site_floor"

    siteFloorId = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId = Column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(160), nullable=False)
    buildingLabel = Column("building_label", String(120), nullable=True)
    floorLabel = Column("floor_label", String(60), nullable=True)
    # Filename under uploaded_images (floorplan_*); served as /images/{key}
    planImageKey = Column("plan_image_key", String(255), nullable=True)
    widthPx = Column("width_px", Integer, nullable=True)
    heightPx = Column("height_px", Integer, nullable=True)
    sortOrder = Column("sort_order", Integer, nullable=False, default=0, server_default="0")
    createdAt = Column("created_at", DateTime(timezone=True), server_default=func.now())
    updatedAt = Column("updated_at", DateTime(timezone=True), onupdate=func.now())
    deletedAt = Column("deleted_at", DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("site_floor_company_sort_idx", "companyId", "sort_order"),
    )
