"""Site floor plan registry for E-Map pins (Phase 2)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from ..config.database import Base


class SiteFloor(Base):
    """Company-scoped floor with optional plan image for Leaflet E-Map."""

    __tablename__ = "site_floor"

    siteFloorId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    buildingLabel: Mapped[str | None] = mapped_column("building_label", String(120), nullable=True)
    floorLabel: Mapped[str | None] = mapped_column("floor_label", String(60), nullable=True)
    planImageKey: Mapped[str | None] = mapped_column("plan_image_key", String(255), nullable=True)
    widthPx: Mapped[int | None] = mapped_column("width_px", Integer, nullable=True)
    heightPx: Mapped[int | None] = mapped_column("height_px", Integer, nullable=True)
    sortOrder: Mapped[int] = mapped_column("sort_order", Integer, nullable=False, default=0, server_default="0")
    createdAt: Mapped[datetime] = mapped_column("created_at", DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column("updated_at", DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now())
    deletedAt: Mapped[datetime | None] = mapped_column("deleted_at", DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("site_floor_company_sort_idx", "companyId", "sort_order"),)
