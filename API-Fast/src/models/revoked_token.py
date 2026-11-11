from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from ..config.database import Base

SCOPE_TOKEN = "token"
SCOPE_FAMILY = "family"


class RevokedToken(Base):
    """Deny-list for issued JWTs. Rows are kept only until the token would have expired."""

    __tablename__ = "revoked_token"

    jti: Mapped[str] = mapped_column(String(96), primary_key=True)
    familyId: Mapped[str | None] = mapped_column("family_id", String(64), nullable=True)
    scope: Mapped[str] = mapped_column(String(10), nullable=False, default=SCOPE_TOKEN, server_default=SCOPE_TOKEN)
    exp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(40), nullable=True)
    createdAt: Mapped[datetime] = mapped_column(
        "created_at", DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("revoked_token_family_idx", "family_id", "scope"),
        Index("revoked_token_exp_idx", "exp"),
    )
