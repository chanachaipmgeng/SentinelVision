"""Job bodies executed by :mod:`src.worker.runner` (and in-process by the API when enabled)."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from ..config.settings import settings

logger = logging.getLogger("dpu.worker.jobs")


async def run_outbox_tick() -> Dict[str, Any]:
    """Deliver pending notifications, enqueue daily cutoff notices, publish backlog gauges."""
    from ..services.notification_service import (
        attendance_cutoff_tick,
        drain_outbox,
        refresh_outbox_backlog,
    )

    sent = await drain_outbox()
    queued = await attendance_cutoff_tick()
    pending, _oldest = await refresh_outbox_backlog()
    return {"sent": sent, "cutoffQueued": queued, "pending": pending}


async def run_retention_tick() -> Dict[str, Any]:
    """Storage retention (off the event loop), sentinel expiry, import payload clean-up,
    orphaned import jobs, and per-company PDPA retention (D4)."""
    from sqlalchemy import select

    from ..config.database import async_session
    from ..models.company import Company
    from ..services.sentinel_identity_service import expire_sentinel_identities_tick
    from ..services.import_job_service import fail_stale_running_jobs, purge_finished_import_payloads
    from ..services.pdpa_service import company_retention_tick
    from ..services.storage_service import retention_tick

    from ..services.error_log_service import purge_old_error_logs

    storage = await asyncio.to_thread(retention_tick)
    sentinel = await expire_sentinel_identities_tick()
    payloads = await purge_finished_import_payloads()
    stale = await fail_stale_running_jobs()
    error_logs_removed = await purge_old_error_logs()
    pdpa_stats: list[dict] = []
    async with async_session() as db:
        company_ids = (
            await db.execute(select(Company.companyId).where(Company.deletedAt.is_(None)))
        ).scalars().all()
        for cid in company_ids:
            try:
                pdpa_stats.append({"companyId": str(cid), **(await company_retention_tick(db, cid))})
            except Exception as exc:  # noqa: BLE001 — one tenant must not stop the tick
                logger.warning("pdpa retention failed for %s: %s", cid, exc)
    return {
        "storage": storage,
        "sentinel": sentinel,
        "importPayloadsRemoved": payloads,
        "importJobsOrphaned": stale,
        "errorLogsRemoved": error_logs_removed,
        "pdpa": pdpa_stats,
    }


async def run_imports_tick(
    *, worker_id: Optional[str] = None, stop_event: Optional[asyncio.Event] = None
) -> Dict[str, Any]:
    """Claim and process every pending employee import job."""
    from ..services.import_job_service import process_pending_import_jobs

    processed = await process_pending_import_jobs(worker_id or "worker", stop_event=stop_event)
    return {"processed": processed}


async def run_attendance_summary_tick() -> Dict[str, Any]:
    """C1 nightly: recompute yesterday's ``attendance_daily`` rows for every active employee."""
    from ..services.attendance_summary_service import recompute_yesterday_all

    return await recompute_yesterday_all(lookback_days=1)


async def run_cctv_analysis_tick(
    *, worker_id: Optional[str] = None, stop_event: Optional[asyncio.Event] = None
) -> Dict[str, Any]:
    """Phase 4A: pull frames from analysis-enabled cameras → InsightFace → incident/attendance."""
    from ..services.cctv_analysis_service import run_cctv_analysis_tick as _tick

    _ = worker_id
    return await _tick(stop_event=stop_event)


async def run_people_count_tick(
    *, worker_id: Optional[str] = None, stop_event: Optional[asyncio.Event] = None
) -> Dict[str, Any]:
    """Phase 6D: dedicated YOLO people lane (line/zone/loiter) — not InsightFace queue."""
    from ..services.people_count_service import run_people_count_tick as _tick

    _ = worker_id
    return await _tick(stop_event=stop_event)


def poll_interval(job: str) -> float:
    if job == "outbox":
        return float(max(5, int(settings.NOTIFY_POLL_SECONDS)))
    if job == "retention":
        return float(max(60, int(settings.WORKER_RETENTION_INTERVAL_SECONDS)))
    if job == "imports":
        return float(max(1, int(settings.WORKER_IMPORT_POLL_SECONDS)))
    if job == "attendance_summary":
        return float(max(300, int(settings.WORKER_ATTENDANCE_SUMMARY_INTERVAL_SECONDS)))
    if job == "cctv":
        return float(max(5, int(settings.WORKER_CCTV_INTERVAL_SECONDS)))
    if job == "people":
        return float(max(5, int(settings.WORKER_PEOPLE_INTERVAL_SECONDS)))
    return 60.0
