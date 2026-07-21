from sqlalchemy import Column, DateTime, ForeignKey, text
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
    # InsightFace buffalo_l ArcFace embedding (512-d, L2-normalized)
    embedding = Column(Vector(FACE_EMBEDDING_DIM), nullable=False)
    createdAt = Column(DateTime, nullable=False, default=datetime.utcnow)

    member = relationship("Member", back_populates="face_encodings")


async def prepare_pgvector(connection) -> None:
    """Enable extension and drop legacy face_encoding schema if needed."""
    await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    table_exists = (
        await connection.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = 'face_encoding'
                )
                """
            )
        )
    ).scalar()

    if not table_exists:
        return

    columns = (
        await connection.execute(
            text(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'face_encoding'
                """
            )
        )
    ).fetchall()
    column_names = {row[0] for row in columns}

    # Old face_recognition JSON column or missing embedding → recreate table
    if "embedding" not in column_names:
        await connection.execute(text("DROP TABLE face_encoding CASCADE"))


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
