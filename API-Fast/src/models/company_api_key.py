"""Tenant API keys for machine-to-machine read access (Phase 5).

Plaintext is shown once at create time; only sha256(hash) + prefix are stored.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from ..config.database import Base


class CompanyApiKey(Base):
    __tablename__ = "company_api_key"

    apiKeyId = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId = Column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(120), nullable=False)
    # Display-safe prefix e.g. "sv_a1b2c3d4" (never the secret).
    keyPrefix = Column("key_prefix", String(24), nullable=False)
    keyHash = Column("key_hash", String(64), nullable=False, unique=True)
    # Subset of {"cameras.read", "incidents.read"}
    scopes = Column(JSONB, nullable=False, default=list)
    createdByMemberId = Column(
        "created_by_member_id",
        UUID(as_uuid=True),
        ForeignKey("member.memberId", ondelete="SET NULL"),
        nullable=True,
    )
    createdAt = Column("created_at", DateTime(timezone=True), server_default=func.now())
    lastUsedAt = Column("last_used_at", DateTime(timezone=True), nullable=True)
    revokedAt = Column("revoked_at", DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    __table_args__ = (
        Index("company_api_key_company_idx", "companyId"),
        Index("company_api_key_prefix_idx", "key_prefix"),
    )
