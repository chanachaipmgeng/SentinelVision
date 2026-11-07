from __future__ import annotations

from sqlalchemy import Column, DateTime, Index, String
from sqlalchemy.sql import func

from ..config.database import Base

SCOPE_TOKEN = "token"
SCOPE_FAMILY = "family"


class RevokedToken(Base):
    """Deny-list for issued JWTs. Rows are kept only until the token would have expired."""

    __tablename__ = "revoked_token"

    # jti of the revoked token, or "fam:<familyId>" when the whole session family is revoked.
    jti = Column(String(96), primary_key=True)
    familyId = Column("family_id", String(64), nullable=True)
    scope = Column(String(10), nullable=False, default=SCOPE_TOKEN, server_default=SCOPE_TOKEN)
    exp = Column(DateTime(timezone=True), nullable=False)
    reason = Column(String(40), nullable=True)
    createdAt = Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("revoked_token_family_idx", "family_id", "scope"),
        Index("revoked_token_exp_idx", "exp"),
    )
