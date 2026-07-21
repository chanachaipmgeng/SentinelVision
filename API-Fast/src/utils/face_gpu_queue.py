"""Global InsightFace / GPU job queue — serializes blocking inference."""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="face-gpu")
_queue: Optional[asyncio.Queue] = None
_started = False
_worker_count = 0
_active = 0
_completed = 0


@dataclass
class _Job:
    fn: Callable[[], Any]
    future: asyncio.Future = field(default_factory=lambda: asyncio.get_running_loop().create_future())


async def start_face_gpu_workers(*, workers: int = 1, queue_size: int = 64) -> None:
    global _queue, _started, _worker_count
    if _started:
        return
    workers = max(1, int(workers))
    _queue = asyncio.Queue(maxsize=max(8, int(queue_size)))
    _worker_count = workers
    for i in range(workers):
        asyncio.create_task(_worker_loop(i), name=f"face-gpu-worker-{i}")
    _started = True
    logger.info("Face GPU queue started workers=%s queue_size=%s", workers, queue_size)


async def _worker_loop(worker_id: int) -> None:
    global _active, _completed
    assert _queue is not None
    loop = asyncio.get_running_loop()
    while True:
        job: _Job = await _queue.get()
        _active += 1
        try:
            result = await loop.run_in_executor(_executor, job.fn)
            if not job.future.done():
                job.future.set_result(result)
        except Exception as exc:
            if not job.future.done():
                job.future.set_exception(exc)
            logger.warning("Face GPU worker %s job failed: %s", worker_id, exc)
        finally:
            _active = max(0, _active - 1)
            _completed += 1
            _queue.task_done()


async def run_on_face_gpu(fn: Callable[[], Any]) -> Any:
    """
    Enqueue a blocking InsightFace callable and await its result.
    Keeps GPU/CPU inference from stampeding under multi-person load.
    """
    if _queue is None or not _started:
        # Fallback: run directly if queue not started (tests / early calls)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(_executor, fn)

    job = _Job(fn=fn)
    await _queue.put(job)
    return await job.future


def face_gpu_queue_stats() -> dict:
    return {
        "started": _started,
        "workers": _worker_count,
        "pending": _queue.qsize() if _queue is not None else 0,
        "active": _active,
        "completed": _completed,
        "maxsize": _queue.maxsize if _queue is not None else 0,
    }
