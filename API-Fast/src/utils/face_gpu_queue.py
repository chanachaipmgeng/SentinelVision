"""Global InsightFace / GPU job queue — priority + fair multi-company scheduling."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, Literal, Optional
from uuid import UUID

from ..services.observability import observe_face_gpu_job

logger = logging.getLogger(__name__)

JobKind = Literal["checkin", "identify", "detect", "other"]
_KIND_ORDER: tuple[JobKind, ...] = ("checkin", "identify", "detect", "other")

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="face-gpu")
_started = False
_worker_count = 0
_active = 0
_completed = 0
_wake: Optional[asyncio.Event] = None
_maxsize = 64
_pending_total = 0

# kind -> company_key -> deque of jobs
_buckets: Dict[JobKind, Dict[str, Deque["_Job"]]] = {
    k: defaultdict(deque) for k in _KIND_ORDER
}
_rr_company: Dict[JobKind, int] = {k: 0 for k in _KIND_ORDER}
_company_order: Dict[JobKind, list[str]] = {k: [] for k in _KIND_ORDER}

_devices: list[str] = ["cpu"]
_rr_device = 0
_worker_tasks: list[asyncio.Task] = []


@dataclass
class _Job:
    fn: Callable[[], Any]
    device: str = "cpu"
    kind: JobKind = "other"
    company_key: str = "_"
    enqueued_at: float = field(default_factory=time.monotonic)
    stale_ms: Optional[float] = None
    future: asyncio.Future = field(
        default_factory=lambda: asyncio.get_running_loop().create_future()
    )


class StaleFaceJob(Exception):
    """Detect frame waited longer than FACE_DETECT_STALE_MS."""


def _call_on_device(fn: Callable[[], Any], device: str) -> Any:
    try:
        from .face_engine import set_thread_device
    except ImportError:
        # Host unit tests without InsightFace installed.
        return fn()
    set_thread_device(device)
    return fn()


def _next_device() -> str:
    global _rr_device
    if not _devices:
        return "cpu"
    device = _devices[_rr_device % len(_devices)]
    _rr_device += 1
    return device


def _company_key(company_id: Optional[UUID | str]) -> str:
    if company_id is None:
        return "_"
    return str(company_id)


def _normalize_kind(kind: Optional[str]) -> JobKind:
    if kind in _KIND_ORDER:
        return kind  # type: ignore[return-value]
    return "other"


async def start_face_gpu_workers(
    *, workers: int = 1, queue_size: int = 64, devices: Optional[list] = None
) -> None:
    global _started, _worker_count, _devices, _executor, _wake, _maxsize, _worker_tasks
    if _started:
        return
    workers = max(1, int(workers))
    _devices = list(devices or ["cpu"])
    if len(_devices) > 1 and workers < len(_devices):
        workers = len(_devices)
    _executor = ThreadPoolExecutor(max_workers=max(workers, 2), thread_name_prefix="face-gpu")
    _maxsize = max(8, int(queue_size))
    _wake = asyncio.Event()
    _worker_count = workers
    _worker_tasks = []
    for i in range(workers):
        task = asyncio.create_task(_worker_loop(i), name=f"face-gpu-worker-{i}")
        _worker_tasks.append(task)
    _started = True
    logger.info(
        "Face GPU queue started workers=%s queue_size=%s devices=%s",
        workers,
        _maxsize,
        _devices,
    )


async def stop_face_gpu_workers_for_tests() -> None:
    """Cancel workers and clear buckets (test harness only)."""
    global _started, _worker_count, _active, _completed, _pending_total, _wake, _worker_tasks
    for task in _worker_tasks:
        task.cancel()
    if _worker_tasks:
        await asyncio.gather(*_worker_tasks, return_exceptions=True)
    _worker_tasks = []
    for kind in _KIND_ORDER:
        for dq in list(_buckets[kind].values()):
            while dq:
                job = dq.popleft()
                if not job.future.done():
                    job.future.cancel()
        _buckets[kind].clear()
        _rr_company[kind] = 0
        _company_order[kind] = []
    _pending_total = 0
    _active = 0
    _completed = 0
    _worker_count = 0
    _wake = None
    _started = False


def _pending_count() -> int:
    return _pending_total


def _pop_next_job() -> Optional[_Job]:
    """Pick highest-priority kind, then round-robin across companies."""
    global _pending_total
    for kind in _KIND_ORDER:
        buckets = _buckets[kind]
        order = [k for k in _company_order[kind] if buckets.get(k)]
        for key in list(buckets.keys()):
            if key not in order and buckets[key]:
                order.append(key)
        if not order:
            continue
        _company_order[kind] = order
        n = len(order)
        start = _rr_company[kind] % n
        for i in range(n):
            idx = (start + i) % n
            key = order[idx]
            dq = buckets.get(key)
            if not dq:
                continue
            job = dq.popleft()
            _pending_total = max(0, _pending_total - 1)
            if not dq:
                buckets.pop(key, None)
                _company_order[kind] = [k for k in order if k in buckets]
            _rr_company[kind] = (idx + 1) % max(1, len(_company_order[kind]) or 1)
            return job
    return None


async def _wait_for_job() -> _Job:
    assert _wake is not None
    while True:
        job = _pop_next_job()
        if job is not None:
            return job
        _wake.clear()
        # Re-check after clear to avoid lost wakeups.
        job = _pop_next_job()
        if job is not None:
            return job
        await _wake.wait()


async def _worker_loop(worker_id: int) -> None:
    global _active, _completed
    loop = asyncio.get_running_loop()
    while True:
        job = await _wait_for_job()
        # Drop stale detect frames before they burn a GPU slot.
        if (
            job.kind == "detect"
            and job.stale_ms is not None
            and (time.monotonic() - job.enqueued_at) * 1000.0 > job.stale_ms
        ):
            if not job.future.done():
                job.future.set_exception(StaleFaceJob("detect frame stale"))
            _completed += 1
            observe_face_gpu_job(
                job.kind,
                wait_seconds=time.monotonic() - job.enqueued_at,
                processing_seconds=0.0,
                result="stale",
            )
            continue

        device = job.device or _devices[worker_id % len(_devices)]
        _active += 1
        waited = time.monotonic() - job.enqueued_at
        t0 = time.perf_counter()
        outcome = "ok"
        try:
            result = await loop.run_in_executor(
                _executor, lambda fn=job.fn, device=device: _call_on_device(fn, device)
            )
            if not job.future.done():
                job.future.set_result(result)
        except Exception as exc:
            outcome = "error"
            if not job.future.done():
                job.future.set_exception(exc)
            logger.warning("Face GPU worker %s job failed: %s", worker_id, exc)
        finally:
            observe_face_gpu_job(
                job.kind,
                wait_seconds=waited,
                processing_seconds=time.perf_counter() - t0,
                result=outcome,
            )
            _active = max(0, _active - 1)
            _completed += 1


async def run_on_face_gpu(
    fn: Callable[[], Any],
    *,
    kind: str = "other",
    company_id: Optional[UUID | str] = None,
    stale_ms: Optional[float] = None,
) -> Any:
    """
    Enqueue a blocking InsightFace callable and await its result.
    Priority: checkin > identify > detect > other; fair round-robin per company.
    """
    global _pending_total
    if not _started or _wake is None:
        loop = asyncio.get_running_loop()
        t0 = time.perf_counter()
        outcome = "ok"
        try:
            return await loop.run_in_executor(_executor, fn)
        except Exception:
            outcome = "error"
            raise
        finally:
            observe_face_gpu_job(
                _normalize_kind(kind),
                wait_seconds=0.0,
                processing_seconds=time.perf_counter() - t0,
                result=outcome,
            )

    # Soft backpressure: wait until under maxsize (same as old Queue.put).
    while _pending_total >= _maxsize:
        await asyncio.sleep(0.01)

    job_kind = _normalize_kind(kind)
    key = _company_key(company_id)
    job = _Job(
        fn=fn,
        device=_next_device(),
        kind=job_kind,
        company_key=key,
        stale_ms=stale_ms,
    )
    buckets = _buckets[job_kind]
    if key not in buckets:
        _company_order[job_kind].append(key)
    buckets[key].append(job)
    _pending_total += 1
    _wake.set()
    return await job.future


def face_gpu_queue_stats() -> dict:
    pending_by_kind: Dict[str, int] = {}
    pending_by_company: Dict[str, int] = {}
    for kind in _KIND_ORDER:
        total_kind = 0
        for key, dq in _buckets[kind].items():
            n = len(dq)
            total_kind += n
            pending_by_company[key] = pending_by_company.get(key, 0) + n
        pending_by_kind[kind] = total_kind
    return {
        "started": _started,
        "workers": _worker_count,
        "pending": _pending_total,
        "active": _active,
        "completed": _completed,
        "maxsize": _maxsize,
        "devices": list(_devices),
        "pendingByKind": pending_by_kind,
        "pendingByCompany": pending_by_company,
    }
