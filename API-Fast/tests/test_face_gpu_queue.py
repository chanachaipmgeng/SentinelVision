"""Unit tests for face GPU queue priority + fair company scheduling."""

from __future__ import annotations

import asyncio
import threading
import time

import pytest
import pytest_asyncio

from src.utils import face_gpu_queue as q


@pytest_asyncio.fixture(autouse=True)
async def _reset_queue():
    await q.stop_face_gpu_workers_for_tests()
    await q.start_face_gpu_workers(workers=1, queue_size=64, devices=["cpu"])
    assert q.face_gpu_queue_stats()["started"] is True
    yield
    await q.stop_face_gpu_workers_for_tests()


@pytest.mark.asyncio
async def test_priority_checkin_before_detect():
    release = threading.Event()
    markers: dict[str, float] = {}
    t0 = time.monotonic()

    def hold():
        release.wait(timeout=2.0)

    def mark(name: str):
        def work():
            markers[name] = time.monotonic() - t0
            time.sleep(0.01)
            return name

        return work

    hold_task = asyncio.create_task(
        q.run_on_face_gpu(hold, kind="other", company_id="hold")
    )
    await asyncio.sleep(0.02)  # worker is blocked on hold

    detect_task = asyncio.create_task(
        q.run_on_face_gpu(mark("d"), kind="detect", company_id="a")
    )
    check_task = asyncio.create_task(
        q.run_on_face_gpu(mark("c"), kind="checkin", company_id="a")
    )
    await asyncio.sleep(0.02)  # both waiting in buckets
    assert q.face_gpu_queue_stats()["pending"] >= 2

    release.set()
    await hold_task
    await asyncio.gather(detect_task, check_task)
    assert markers["c"] < markers["d"]


@pytest.mark.asyncio
async def test_round_robin_companies():
    release = threading.Event()
    order: list[str] = []

    def hold():
        release.wait(timeout=2.0)

    def make(label: str):
        def work():
            order.append(label)
            time.sleep(0.005)
            return label

        return work

    busy = asyncio.create_task(
        q.run_on_face_gpu(hold, kind="detect", company_id="busy")
    )
    await asyncio.sleep(0.02)
    tasks = [
        asyncio.create_task(
            q.run_on_face_gpu(make("A1"), kind="detect", company_id="A")
        ),
        asyncio.create_task(
            q.run_on_face_gpu(make("A2"), kind="detect", company_id="A")
        ),
        asyncio.create_task(
            q.run_on_face_gpu(make("B1"), kind="detect", company_id="B")
        ),
    ]
    await asyncio.sleep(0.02)
    release.set()
    await busy
    await asyncio.gather(*tasks)
    # After busy, fair RR should interleave B before both A jobs finish.
    assert order.index("B1") < order.index("A2")


@pytest.mark.asyncio
async def test_stale_detect_dropped():
    release = threading.Event()

    def hold():
        release.wait(timeout=2.0)

    block = asyncio.create_task(
        q.run_on_face_gpu(hold, kind="checkin", company_id="x")
    )
    await asyncio.sleep(0.02)

    stale_task = asyncio.create_task(
        q.run_on_face_gpu(
            lambda: "should-not-run",
            kind="detect",
            company_id="x",
            stale_ms=30,
        )
    )
    await asyncio.sleep(0.08)  # exceed stale while still held
    release.set()
    await block
    with pytest.raises(q.StaleFaceJob):
        await stale_task


@pytest.mark.asyncio
async def test_stats_include_devices_and_breakdown():
    await q.run_on_face_gpu(lambda: None, kind="detect", company_id="c1")
    stats = q.face_gpu_queue_stats()
    assert stats["started"] is True
    assert stats["workers"] == 1
    assert stats["devices"] == ["cpu"]
    assert "pendingByKind" in stats
    assert "pendingByCompany" in stats
