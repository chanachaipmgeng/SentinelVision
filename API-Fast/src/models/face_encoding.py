from sqlalchemy import Column, DateTime, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from ..config.database import Base, DB_SCHEMA
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
        Index("face_encoding_company_member_idx", "companyId", "memberId"),
    )


async def prepare_pgvector(connection) -> None:
    """Enable extension and verify face_encoding schema."""
    await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    target_schema = DB_SCHEMA or "public"
    table_exists = (
        await connection.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = :schema AND table_name = 'face_encoding'
                )
                """
            ),
            {"schema": target_schema},
        )
    ).scalar()

    if not table_exists:
        return

    columns = (
        await connection.execute(
            text(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = :schema AND table_name = 'face_encoding'
                """
            ),
            {"schema": target_schema},
        )
    ).fetchall()
    column_names = {row[0] for row in columns}

    # Old face_recognition JSON column — do not drop in place (enterprise: migrate via Alembic).
    if "embedding" not in column_names:
        raise RuntimeError(
            "face_encoding.embedding is missing. Run a migration instead of dropping the table."
        )


async def ensure_face_embedding_index(connection) -> None:
    """HNSW index for cosine search (safe after create_all)."""
    await connection.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS face_encoding_embedding_hnsw_idx
            ON face_encoding
            USING hnsw (embedding vector_cosine_ops)
            """
        )
    )
