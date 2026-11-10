"""Job scheduler with graceful shutdown, per-job Prometheus metrics and a single-run mode."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
import os
import signal
import socket
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional

from ..config.settings import settings
from ..services.observability import track_job
from . import jobs as job_bodies

logger = logging.getLogger("dpu.worker")

JobFn = Callable[..., Awaitable[Any]]


@dataclass(frozen=True)
class JobSpec:
    name: str
    run: JobFn
    # Jobs that want to stop early on shutdown accept worker_id / stop_event kwargs.
    takes_context: bool = False


JOBS: Dict[str, JobSpec] = {
    "outbox": JobSpec("outbox", job_bodies.run_outbox_tick),
    "retention": JobSpec("retention", job_bodies.run_retention_tick),
    "imports": JobSpec("imports", job_bodies.run_imports_tick, takes_context=True),
    "attendance_summary": JobSpec("attendance_summary", job_bodies.run_attendance_summary_tick),
    "cctv": JobSpec("cctv", job_bodies.run_cctv_analysis_tick, takes_context=True),
    "people": JobSpec("people", job_bodies.run_people_count_tick, takes_context=True),
}


def parse_job_list(raw: Optional[str]) -> List[str]:
    names = [p.strip() for p in (raw or "").split(",") if p.strip()]
    if not names or names == ["all"]:
        names = list(JOBS)
    unknown = [n for n in names if n not in JOBS]
    if unknown:
        raise ValueError(f"unknown job(s) {unknown}; available: {', '.join(JOBS)}")
    return names


def default_worker_id() -> str:
    return settings.WORKER_ID or f"{socket.gethostname()}:{os.getpid()}"


async def _run_job(spec: JobSpec, *, worker_id: str, stop_event: asyncio.Event) -> bool:
    """Execute one job run inside ``track_job``; returns True on success (never raises)."""
    try:
        with track_job(spec.name):
            if spec.takes_context:
                result = await spec.run(worker_id=worker_id, stop_event=stop_event)
            else:
                result = await spec.run()
        if result:
            logger.info("job %s ok", spec.name, extra={"result": result})
        return True
    except Exception:
        logger.exception("job %s failed", spec.name)
        return False


async def wait_for_database(*, attempts: int = 60, delay: float = 2.0) -> None:
    """Block until ``SELECT 1`` succeeds (DB container / migrations still starting)."""
    from sqlalchemy import text

    from ..config.database import async_session

    last: Optional[Exception] = None
    for _ in range(max(1, attempts)):
        try:
            async with async_session() as db:
                await db.execute(text("SELECT 1"))
            return
        except Exception as exc:  # noqa: BLE001
            last = exc
            await asyncio.sleep(delay)
    raise RuntimeError(f"database not reachable: {last}")


class WorkerRunner:
    """Runs each configured job in its own loop until :meth:`stop` (or SIGTERM/SIGINT)."""

    def __init__(self, job_names: Optional[Iterable[str]] = None, *, worker_id: Optional[str] = None):
        self.job_names = list(job_names) if job_names is not None else parse_job_list(settings.WORKER_JOBS)
        self.worker_id = worker_id or default_worker_id()
        self.stop_event = asyncio.Event()
        self._tasks: List[asyncio.Task] = []
        self._wakeups: Dict[str, asyncio.Event] = {}

    # -- lifecycle -------------------------------------------------------------------
    def install_signal_handlers(self) -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, self.request_stop, sig.name)
            except (NotImplementedError, RuntimeError):  # pragma: no cover - Windows / nested loops
                signal.signal(sig, lambda s, _f: self.request_stop(signal.Signals(s).name))

    def request_stop(self, reason: str = "stop") -> None:
        if not self.stop_event.is_set():
            logger.info("worker stopping (%s)", reason)
            self.stop_event.set()
            for ev in self._wakeups.values():
                ev.set()

    def trigger(self, job: str) -> None:
        """Wake a job loop early (tests / future NOTIFY hook)."""
        ev = self._wakeups.get(job)
        if ev is not None:
            ev.set()

    async def start(self) -> None:
        for name in self.job_names:
            spec = JOBS[name]
            self._wakeups[name] = asyncio.Event()
            self._tasks.append(asyncio.create_task(self._loop(spec), name=f"worker-{name}"))
        logger.info(
            "worker started", extra={"workerId": self.worker_id, "jobs": self.job_names}
        )

    async def _loop(self, spec: JobSpec) -> None:
        wake = self._wakeups[spec.name]
        while not self.stop_event.is_set():
            await _run_job(spec, worker_id=self.worker_id, stop_event=self.stop_event)
            if self.stop_event.is_set():
                break
            wake.clear()
            try:
                await asyncio.wait_for(wake.wait(), timeout=job_bodies.poll_interval(spec.name))
            except asyncio.TimeoutError:
                pass

    async def stop(self, grace_seconds: Optional[float] = None) -> None:
        """Let in-flight runs finish for ``grace_seconds`` then cancel what is left."""
        self.request_stop("shutdown")
        if not self._tasks:
            return
        grace = float(
            grace_seconds if grace_seconds is not None else settings.WORKER_SHUTDOWN_GRACE_SECONDS
        )
        done, pending = await asyncio.wait(self._tasks, timeout=max(0.0, grace))
        for task in pending:
            logger.warning("job task %s did not finish within %ss; cancelling", task.get_name(), grace)
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        self._tasks = []

    async def run_forever(self, *, handle_signals: bool = True) -> None:
        if handle_signals:
            self.install_signal_handlers()
        await self.start()
        await self.stop_event.wait()
        await self.stop()


async def run_jobs_once(job_names: Optional[Iterable[str]] = None, *, worker_id: Optional[str] = None) -> Dict[str, bool]:
    """Single-run mode for cron: execute each job once, return {job: ok}."""
    names = list(job_names) if job_names is not None else parse_job_list(settings.WORKER_JOBS)
    wid = worker_id or default_worker_id()
    stop_event = asyncio.Event()
    results: Dict[str, bool] = {}
    for name in names:
        results[name] = await _run_job(JOBS[name], worker_id=wid, stop_event=stop_event)
    return results
