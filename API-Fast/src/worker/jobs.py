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
    orphaned import jobs."""
    from ..routes.sentinel_routes import expire_sentinel_identities_tick
    from ..services.import_job_service import fail_stale_running_jobs, purge_finished_import_payloads
    from ..services.storage_service import retention_tick

    storage = await asyncio.to_thread(retention_tick)
    sentinel = await expire_sentinel_identities_tick()
    payloads = await purge_finished_import_payloads()
    stale = await fail_stale_running_jobs()
    return {
        "storage": storage,
        "sentinel": sentinel,
        "importPayloadsRemoved": payloads,
        "importJobsOrphaned": stale,
    }


async def run_imports_tick(
    *, worker_id: Optional[str] = None, stop_event: Optional[asyncio.Event] = None
) -> Dict[str, Any]:
    """Claim and process every pending employee import job."""
    from ..services.import_job_service import process_pending_import_jobs

    processed = await process_pending_import_jobs(worker_id or "worker", stop_event=stop_event)
    return {"processed": processed}


def poll_interval(job: str) -> float:
    if job == "outbox":
        return float(max(5, int(settings.NOTIFY_POLL_SECONDS)))
    if job == "retention":
        return float(max(60, int(settings.WORKER_RETENTION_INTERVAL_SECONDS)))
    if job == "imports":
        return float(max(1, int(settings.WORKER_IMPORT_POLL_SECONDS)))
    return 60.0
