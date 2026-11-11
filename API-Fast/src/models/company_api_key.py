"""Tenant API keys for machine-to-machine read access (Phase 5).

Plaintext is shown once at create time; only sha256(hash) + prefix are stored.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from ..config.database import Base


class CompanyApiKey(Base):
    __tablename__ = "company_api_key"

    apiKeyId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    keyPrefix: Mapped[str] = mapped_column("key_prefix", String(24), nullable=False)
    keyHash: Mapped[str] = mapped_column("key_hash", String(64), nullable=False, unique=True)
    scopes: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    createdByMemberId: Mapped[uuid.UUID | None] = mapped_column(
        "created_by_member_id",
        UUID(as_uuid=True),
        ForeignKey("member.memberId", ondelete="SET NULL"),
        nullable=True,
    )
    createdAt: Mapped[datetime] = mapped_column("created_at", DateTime(timezone=True), server_default=func.now())
    lastUsedAt: Mapped[datetime | None] = mapped_column("last_used_at", DateTime(timezone=True), nullable=True)
    revokedAt: Mapped[datetime | None] = mapped_column("revoked_at", DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("company_api_key_company_idx", "companyId"),
        Index("company_api_key_prefix_idx", "key_prefix"),
    )
