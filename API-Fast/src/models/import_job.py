"""Employee bulk-import job (B7). The API persists the upload + a `pending` row; the `worker`
service claims rows with `FOR UPDATE SKIP LOCKED`, streams progress into `progress` and
finishes with `done` / `failed`. The Web-Manage import dialog polls this row."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from ..config.database import Base

STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_DONE = "done"
STATUS_FAILED = "failed"


class ImportJob(Base):
    __tablename__ = "import_job"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    companyId: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default=STATUS_PENDING)
    result: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(String, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finishedAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    requestedBy: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    fileName: Mapped[str | None] = mapped_column(String, nullable=True)
    photosFileName: Mapped[str | None] = mapped_column(String, nullable=True)
    payloadDir: Mapped[str | None] = mapped_column(String, nullable=True)
    progress: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    lockedBy: Mapped[str | None] = mapped_column(String, nullable=True)
    startedAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    heartbeatAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("import_job_status_created_idx", "status", "createdAt"),)

    def to_public(self) -> dict:
        return {
            "jobId": str(self.id),
            "companyId": str(self.companyId),
            "status": self.status,
            "progress": self.progress,
            "result": self.result,
            "error": self.error,
            "fileName": self.fileName,
            "attempts": int(self.attempts or 0),
            "createdAt": self.createdAt.isoformat() if self.createdAt else None,
            "startedAt": self.startedAt.isoformat() if self.startedAt else None,
            "finishedAt": self.finishedAt.isoformat() if self.finishedAt else None,
        }
