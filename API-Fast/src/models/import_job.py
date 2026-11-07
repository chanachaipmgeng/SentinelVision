"""Employee bulk-import job (B7). The API persists the upload + a `pending` row; the `worker`
service claims rows with `FOR UPDATE SKIP LOCKED`, streams progress into `progress` and
finishes with `done` / `failed`. The Web-Manage import dialog polls this row."""
from __future__ import annotations

from uuid import uuid4

from sqlalchemy import Column, DateTime, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.sql import func

from ..config.database import Base

STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_DONE = "done"
STATUS_FAILED = "failed"


class ImportJob(Base):
    __tablename__ = "import_job"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    companyId = Column(PGUUID(as_uuid=True), nullable=False)
    status = Column(String, nullable=False, default=STATUS_PENDING)
    result = Column(JSONB, nullable=True)
    error = Column(String, nullable=True)
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    finishedAt = Column(DateTime(timezone=True), nullable=True)
    # B7: hand-off to the worker.
    requestedBy = Column(PGUUID(as_uuid=True), nullable=True)
    fileName = Column(String, nullable=True)
    photosFileName = Column(String, nullable=True)
    # Sub-directory under settings.IMPORT_JOB_DIR (shared api/worker volume) holding the files.
    payloadDir = Column(String, nullable=True)
    progress = Column(JSONB, nullable=True)
    attempts = Column(Integer, nullable=False, default=0, server_default="0")
    lockedBy = Column(String, nullable=True)
    startedAt = Column(DateTime(timezone=True), nullable=True)
    heartbeatAt = Column(DateTime(timezone=True), nullable=True)

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
