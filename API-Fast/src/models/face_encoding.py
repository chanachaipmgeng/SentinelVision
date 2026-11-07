from sqlalchemy import Column, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from ..config.database import Base
from uuid import uuid4
from datetime import datetime

FACE_EMBEDDING_DIM = 512


class FaceEncoding(Base):
    __tablename__ = "face_encoding"

    faceEncodingId = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    memberId = Column(
        UUID(as_uuid=True), ForeignKey("member.memberId"), nullable=False
    )
    # Tenant that enrolled this encoding. Nullable only for legacy rows that the
    # startup/Alembic backfill could not resolve (member without an active employee row).
    companyId = Column(
        UUID(as_uuid=True), ForeignKey("company.companyId"), nullable=True
    )
    # InsightFace buffalo_l ArcFace embedding (512-d, L2-normalized)
    embedding = Column(Vector(FACE_EMBEDDING_DIM), nullable=False)
    createdAt = Column(DateTime, nullable=False, default=datetime.utcnow)

    member = relationship("Member", back_populates="face_encodings")

    __table_args__ = (
        Index("face_encoding_member_idx", "memberId"),
        Index("face_encoding_company_member_idx", "companyId", "memberId"),
        # HNSW cosine index used by services/face_match_service.py (1:N search).
        Index(
            "face_encoding_embedding_hnsw_idx",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

