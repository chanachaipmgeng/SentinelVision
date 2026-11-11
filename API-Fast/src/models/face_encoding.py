from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..config.database import Base

if TYPE_CHECKING:
    from .member import Member

FACE_EMBEDDING_DIM = 512
DEFAULT_FACE_MODEL_VERSION = "buffalo_l"


class FaceEncoding(Base):
    __tablename__ = "face_encoding"

    faceEncodingId: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    memberId: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("member.memberId"), nullable=False)
    companyId: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("company.companyId"), nullable=True
    )
    embedding: Mapped[Any] = mapped_column(Vector(FACE_EMBEDDING_DIM), nullable=False)
    modelVersion: Mapped[str | None] = mapped_column(
        String(64), nullable=True, default=DEFAULT_FACE_MODEL_VERSION
    )
    createdAt: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    member: Mapped["Member"] = relationship("Member", back_populates="face_encodings")

    __table_args__ = (
        Index("face_encoding_member_idx", "memberId"),
        Index("face_encoding_company_member_idx", "companyId", "memberId"),
        Index(
            "face_encoding_embedding_hnsw_idx",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
