"""Employee import jobs (B7): API persists upload + job row, the worker claims and processes.

Flow
----
1. ``POST /employees/company/{id}/import-jobs`` → :func:`create_import_job` writes the workbook
   (and optional photos ZIP) under ``IMPORT_JOB_DIR/<jobId>/`` — a volume shared by ``api`` and
   ``worker`` — and inserts an ``import_job`` row with ``status=pending``.
2. The worker's ``imports`` job calls :func:`process_pending_import_jobs`: it claims one row at a
   time with ``SELECT … FOR UPDATE SKIP LOCKED`` (several workers / API replicas are safe), runs
   :func:`import_employees_from_excel` and streams ``progress`` + ``heartbeatAt`` into the row.
3. ``GET …/import-jobs/{jobId}`` returns ``status`` / ``progress`` / ``result`` for the UI poll.

A job whose heartbeat is older than ``WORKER_IMPORT_LEASE_SECONDS`` while ``running`` is marked
``failed`` (the worker died mid-import; rows already committed stay, so we do not auto-retry).
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import logging
from pathlib import Path
import shutil
import time
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import func, select, update

from ..config.database import async_session
from ..config.settings import settings
from ..models.import_job import (
    STATUS_DONE,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_RUNNING,
    ImportJob,
)
from .observability import (
    import_job_duration_seconds,
    import_job_rows_total,
    import_jobs_pending,
    import_jobs_running,
    import_jobs_total,
    set_company_context,
    reset_company_context,
)

logger = logging.getLogger("dpu.import_jobs")

PHOTOS_FILE_NAME = "photos.zip"


class BytesUpload:
    """Minimal ``UploadFile`` stand-in for files already on disk / in memory."""

    def __init__(self, name: str, data: bytes):
        self.filename = name
        self._data = data

    async def read(self) -> bytes:
        return self._data


def import_job_root() -> Path:
    return Path(settings.IMPORT_JOB_DIR or "import_jobs")


def _job_dir(job_id: UUID | str) -> Path:
    return import_job_root() / str(job_id)


def _safe_name(name: Optional[str], default: str) -> str:
    base = Path(name or "").name.strip()
    return base or default


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------------------
# API side
# --------------------------------------------------------------------------------------
async def create_import_job(
    company_id: str | UUID,
    *,
    file_name: Optional[str],
    data: bytes,
    photos_name: Optional[str] = None,
    photos_data: Optional[bytes] = None,
    requested_by: Optional[UUID | str] = None,
) -> ImportJob:
    job_id = uuid4()
    job_dir = _job_dir(job_id)
    job_dir.mkdir(parents=True, exist_ok=True)
    safe_file = _safe_name(file_name, "import.xlsx")
    (job_dir / safe_file).write_bytes(data)
    safe_photos = None
    if photos_data:
        safe_photos = PHOTOS_FILE_NAME
        (job_dir / safe_photos).write_bytes(photos_data)

    job = ImportJob(
        id=job_id,
        companyId=UUID(str(company_id)),
        status=STATUS_PENDING,
        requestedBy=UUID(str(requested_by)) if requested_by else None,
        fileName=safe_file,
        photosFileName=safe_photos,
        payloadDir=str(job_id),
        progress={"processed": 0, "total": None, "success": 0, "failed": 0, "facesEnrolled": 0},
        attempts=0,
    )
    try:
        async with async_session() as db:
            db.add(job)
            await db.commit()
    except Exception:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise
    import_jobs_pending.inc()
    return job


async def get_import_job(db, job_id: str | UUID) -> Optional[ImportJob]:
    try:
        jid = UUID(str(job_id))
    except ValueError:
        return None
    return await db.get(ImportJob, jid)


# --------------------------------------------------------------------------------------
# Worker side
# --------------------------------------------------------------------------------------
async def refresh_import_job_gauges() -> dict:
    async with async_session() as db:
        rows = (
            await db.execute(
                select(ImportJob.status, func.count())
                .where(ImportJob.status.in_([STATUS_PENDING, STATUS_RUNNING]))
                .group_by(ImportJob.status)
            )
        ).all()
    counts = {status: int(n) for status, n in rows}
    import_jobs_pending.set(counts.get(STATUS_PENDING, 0))
    import_jobs_running.set(counts.get(STATUS_RUNNING, 0))
    return counts


async def claim_next_import_job(worker_id: str) -> Optional[ImportJob]:
    """Atomically move the oldest pending job to ``running`` for this worker."""
    async with async_session() as db:
        job = (
            await db.execute(
                select(ImportJob)
                .where(ImportJob.status == STATUS_PENDING)
                .order_by(ImportJob.createdAt)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
        ).scalar_one_or_none()
        if job is None:
            return None
        now = _now()
        job.status = STATUS_RUNNING
        job.attempts = int(job.attempts or 0) + 1
        job.lockedBy = worker_id
        job.startedAt = now
        job.heartbeatAt = now
        await db.commit()
        await db.refresh(job)
        return job


async def _update_job(job_id: UUID, **values: Any) -> None:
    async with async_session() as db:
        await db.execute(update(ImportJob).where(ImportJob.id == job_id).values(**values))
        await db.commit()


async def fail_stale_running_jobs(lease_seconds: Optional[int] = None) -> int:
    """Mark ``running`` jobs without a recent heartbeat as failed (worker lost)."""
    lease = int(lease_seconds or settings.WORKER_IMPORT_LEASE_SECONDS)
    cutoff = _now() - timedelta(seconds=max(60, lease))
    async with async_session() as db:
        result = await db.execute(
            update(ImportJob)
            .where(
                ImportJob.status == STATUS_RUNNING,
                func.coalesce(ImportJob.heartbeatAt, ImportJob.startedAt, ImportJob.createdAt) < cutoff,
            )
            .values(
                status=STATUS_FAILED,
                error=f"worker lease expired after {lease}s (worker restarted or crashed mid-import)",
                finishedAt=_now(),
            )
        )
        await db.commit()
    n = int(result.rowcount or 0)
    if n:
        logger.warning("marked %s orphaned import job(s) as failed", n)
        import_jobs_total.labels(result="failed").inc(n)
    return n


def _read_payload(job: ImportJob) -> tuple[bytes, Optional[bytes]]:
    job_dir = _job_dir(job.payloadDir or job.id)
    xlsx_path = job_dir / _safe_name(job.fileName, "import.xlsx")
    if not xlsx_path.is_file():
        raise FileNotFoundError(
            f"import payload missing: {xlsx_path} (is IMPORT_JOB_DIR shared between api and worker?)"
        )
    photos = None
    if job.photosFileName:
        photos_path = job_dir / _safe_name(job.photosFileName, PHOTOS_FILE_NAME)
        if photos_path.is_file():
            photos = photos_path.read_bytes()
    return xlsx_path.read_bytes(), photos


async def run_import_job(job: ImportJob) -> ImportJob:
    """Process one claimed job to completion (``done`` / ``failed``). Never raises."""
    from ..controllers.employee_import_controller import import_employees_from_excel

    company_id = str(job.companyId)
    ctx = set_company_context(company_id)
    import_jobs_running.inc()
    t0 = time.perf_counter()
    last_beat = 0.0

    async def progress_cb(progress: dict) -> None:
        nonlocal last_beat
        # Throttle DB writes: every row for the first 20, then at most twice a second.
        now = time.monotonic()
        if int(progress.get("processed") or 0) > 20 and now - last_beat < 0.5:
            return
        last_beat = now
        await _update_job(job.id, progress=progress, heartbeatAt=_now())

    try:
        data, photos = await asyncio.to_thread(_read_payload, job)
        async with async_session() as db:
            result = await import_employees_from_excel(
                company_id,
                BytesUpload(job.fileName or "import.xlsx", data),
                db,
                photos=BytesUpload(job.photosFileName or PHOTOS_FILE_NAME, photos) if photos else None,
                progress_cb=progress_cb,
            )
        result = result if isinstance(result, dict) else {"ok": True}
        await _update_job(
            job.id,
            status=STATUS_DONE,
            result=result,
            error=None,
            progress={
                "processed": int(result.get("total") or 0),
                "total": int(result.get("total") or 0),
                "success": int(result.get("success") or 0),
                "failed": int(result.get("failed") or 0),
                "facesEnrolled": int(result.get("facesEnrolled") or 0),
            },
            finishedAt=_now(),
            heartbeatAt=_now(),
        )
        import_jobs_total.labels(result="done").inc()
        import_job_rows_total.labels(result="success").inc(int(result.get("success") or 0))
        import_job_rows_total.labels(result="failed").inc(int(result.get("failed") or 0))
        job.status = STATUS_DONE
        job.result = result
        logger.info(
            "import job finished",
            extra={"jobId": str(job.id), "total": result.get("total"), "success": result.get("success"), "failed": result.get("failed")},
        )
        try:
            from .notification_service import enqueue

            await enqueue(
                "import.finished",
                "line",
                {
                    "body": f"Import finished for company {company_id}: "
                    f"{result.get('success', 0)}/{result.get('total', 0)} rows",
                    "data": {
                        "jobId": str(job.id),
                        "total": result.get("total"),
                        "success": result.get("success"),
                        "failed": result.get("failed"),
                    },
                },
                company_id=company_id,
            )
        except Exception:
            logger.exception("import.finished notification enqueue failed")
    except Exception as exc:
        detail = getattr(exc, "detail", None)
        message = str(detail if detail else exc)[:500]
        logger.exception("import job %s failed: %s", job.id, message)
        try:
            await _update_job(
                job.id, status=STATUS_FAILED, error=message, finishedAt=_now(), heartbeatAt=_now()
            )
        except Exception:
            logger.exception("could not persist import job failure")
        import_jobs_total.labels(result="failed").inc()
        job.status = STATUS_FAILED
        job.error = message
    finally:
        import_job_duration_seconds.observe(time.perf_counter() - t0)
        import_jobs_running.dec()
        reset_company_context(ctx)
    return job


async def process_pending_import_jobs(
    worker_id: str,
    *,
    stop_event: Optional[asyncio.Event] = None,
    max_jobs: Optional[int] = None,
) -> int:
    """Claim and run pending jobs until the queue is empty / stop requested. Returns jobs run."""
    done = 0
    while max_jobs is None or done < max_jobs:
        if stop_event is not None and stop_event.is_set():
            break
        job = await claim_next_import_job(worker_id)
        if job is None:
            break
        await run_import_job(job)
        done += 1
    await refresh_import_job_gauges()
    return done


# --------------------------------------------------------------------------------------
# Retention
# --------------------------------------------------------------------------------------
async def purge_finished_import_payloads(retention_days: Optional[int] = None) -> int:
    """Delete payload directories of finished jobs older than ``IMPORT_JOB_RETENTION_DAYS``."""
    days = int(retention_days if retention_days is not None else settings.IMPORT_JOB_RETENTION_DAYS)
    cutoff = _now() - timedelta(days=max(0, days))
    async with async_session() as db:
        rows = (
            await db.execute(
                select(ImportJob.id, ImportJob.payloadDir).where(
                    ImportJob.status.in_([STATUS_DONE, STATUS_FAILED]),
                    func.coalesce(ImportJob.finishedAt, ImportJob.createdAt) < cutoff,
                    ImportJob.payloadDir.is_not(None),
                )
            )
        ).all()
        removed = 0
        for job_id, payload_dir in rows:
            path = _job_dir(payload_dir or job_id)
            if path.exists():
                await asyncio.to_thread(shutil.rmtree, path, True)
            removed += 1
        if rows:
            await db.execute(
                update(ImportJob)
                .where(ImportJob.id.in_([r[0] for r in rows]))
                .values(payloadDir=None)
            )
            await db.commit()
    return removed
