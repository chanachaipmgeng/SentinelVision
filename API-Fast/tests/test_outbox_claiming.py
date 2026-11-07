"""B2: notification outbox — enqueue rules, backoff gate and ``SELECT … FOR UPDATE SKIP LOCKED``
claiming so two API replicas never deliver the same row twice.
"""
from __future__ import annotations

import asyncio
import os
import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select, text

if not os.environ.get("DPU_TEST_DB_READY"):
    pytest.skip(
        "No test database: set TEST_DATABASE_URL or `pip install pgserver`",
        allow_module_level=True,
    )

from src.config.database import async_session, engine  # noqa: E402
from src.models.system_setting import SystemSetting  # noqa: E402
from src.services import notification_service as ns  # noqa: E402
from src.services.notification_service import (  # noqa: E402
    NotificationOutbox,
    _backoff_ready,
    drain_outbox,
    emit_company_webhook_event,
)

db_test = pytest.mark.asyncio(loop_scope="module")


@pytest_asyncio.fixture(scope="module", loop_scope="module", autouse=True)
async def _fresh_pool():
    """asyncpg connections are bound to the loop that created them; drop any pooled ones left by
    earlier test modules before this module's loop starts using the engine."""
    await engine.dispose(close=False)
    yield
    await engine.dispose()


# ---------------------------------------------------------------- backoff gate (pure)
def _row(attempts: int, age_seconds: float) -> NotificationOutbox:
    r = NotificationOutbox(event="e", channel="webhook", payload={}, status="pending", attempts=attempts)
    r.createdAt = datetime.now(timezone.utc) - timedelta(seconds=age_seconds)
    return r


@pytest.mark.parametrize(
    "attempts,age,ready",
    [
        (0, 0, True),
        (1, 14, False),
        (1, 15, True),
        (2, 29, False),
        (2, 30, True),
        (3, 59, False),
        (4, 120, True),
        (6, 299, False),  # capped at 300s
        (6, 300, True),
    ],
)
def test_backoff_schedule(attempts, age, ready):
    assert _backoff_ready(_row(attempts, age), datetime.now(timezone.utc)) is ready


def test_backoff_naive_created_at_treated_as_utc():
    r = _row(1, 0)
    r.createdAt = (datetime.now(timezone.utc) - timedelta(seconds=20)).replace(tzinfo=None)
    assert _backoff_ready(r, datetime.now(timezone.utc)) is True


# ---------------------------------------------------------------- DB-backed
class _Recorder:
    def __init__(self, *, fail: bool = False, delay: float = 0.0):
        self.calls: list[tuple[str, str]] = []
        self.fail = fail
        self.delay = delay

    def __call__(self, payload: dict, *, delivery_id: str = "") -> None:
        if self.delay:
            time.sleep(self.delay)
        self.calls.append((delivery_id, payload.get("event", "")))
        if self.fail:
            raise RuntimeError("upstream 503")


async def _purge(ids: list[uuid.UUID]) -> None:
    async with async_session() as db:
        await db.execute(NotificationOutbox.__table__.delete().where(NotificationOutbox.id.in_(ids)))
        await db.commit()


async def _enqueue(n: int, *, attempts: int = 0, age_seconds: float = 0.0, channel: str = "webhook") -> list[uuid.UUID]:
    ids = []
    async with async_session() as db:
        for i in range(n):
            row = NotificationOutbox(
                id=uuid.uuid4(),
                companyId=uuid.uuid4(),
                event=f"test.event.{i}",
                channel=channel,
                payload={"webhookUrl": "https://example.invalid/hook", "event": f"test.event.{i}"},
                status="pending",
                attempts=attempts,
            )
            db.add(row)
            ids.append(row.id)
        await db.flush()
        if age_seconds:
            await db.execute(
                NotificationOutbox.__table__.update()
                .where(NotificationOutbox.id.in_(ids))
                .values(createdAt=datetime.now(timezone.utc) - timedelta(seconds=age_seconds))
            )
        await db.commit()
    return ids


async def _rows(ids: list[uuid.UUID]) -> dict[uuid.UUID, NotificationOutbox]:
    async with async_session() as db:
        res = await db.execute(select(NotificationOutbox).where(NotificationOutbox.id.in_(ids)))
        return {r.id: r for r in res.scalars().all()}


@db_test
async def test_drain_marks_sent_and_passes_delivery_id(monkeypatch):
    rec = _Recorder()
    monkeypatch.setattr(ns, "_send_webhook", rec)
    ids = await _enqueue(3)
    try:
        assert await drain_outbox() == 3
        rows = await _rows(ids)
        assert all(r.status == "sent" and r.attempts == 1 and r.lastError is None for r in rows.values())
        assert {d for d, _ in rec.calls} == {str(i) for i in ids}
        # already-sent rows are not picked up again
        assert await drain_outbox() == 0
        assert len(rec.calls) == 3
    finally:
        await _purge(ids)


@db_test
async def test_drain_failure_increments_attempts_then_fails_after_five(monkeypatch):
    rec = _Recorder(fail=True)
    monkeypatch.setattr(ns, "_send_webhook", rec)
    ids = await _enqueue(1)
    try:
        assert await drain_outbox() == 0
        row = (await _rows(ids))[ids[0]]
        assert row.status == "pending" and row.attempts == 1 and "upstream 503" in row.lastError

        # fresh row with 1 attempt is inside the 15s backoff → skipped without a delivery attempt
        assert await drain_outbox() == 0
        assert len(rec.calls) == 1

        # push to the edge: 4 attempts, old enough → 5th failure flips to "failed"
        async with async_session() as db:
            await db.execute(
                NotificationOutbox.__table__.update()
                .where(NotificationOutbox.id == ids[0])
                .values(attempts=4, createdAt=datetime.now(timezone.utc) - timedelta(minutes=10))
            )
            await db.commit()
        assert await drain_outbox() == 0
        row = (await _rows(ids))[ids[0]]
        assert row.status == "failed" and row.attempts == 5
        assert len(rec.calls) == 2
    finally:
        await _purge(ids)


@db_test
async def test_unknown_channel_is_recorded_as_error(monkeypatch):
    monkeypatch.setattr(ns, "_send_webhook", _Recorder())
    ids = await _enqueue(1, channel="pigeon")
    try:
        assert await drain_outbox() == 0
        row = (await _rows(ids))[ids[0]]
        assert row.attempts == 1 and "unknown channel pigeon" in row.lastError
    finally:
        await _purge(ids)


@db_test
async def test_rows_locked_by_another_worker_are_skipped(monkeypatch):
    rec = _Recorder()
    monkeypatch.setattr(ns, "_send_webhook", rec)
    ids = await _enqueue(2)
    try:
        async with engine.connect() as holder:
            await holder.execute(text("BEGIN"))
            locked = await holder.execute(
                select(NotificationOutbox.id)
                .where(NotificationOutbox.id.in_(ids))
                .with_for_update()
            )
            assert len(locked.all()) == 2
            # another worker draining now must not block and must not deliver the locked rows
            assert await asyncio.wait_for(drain_outbox(), timeout=5) == 0
            assert rec.calls == []
            await holder.execute(text("ROLLBACK"))
        assert await drain_outbox() == 2
        assert len(rec.calls) == 2
    finally:
        await _purge(ids)


@db_test
async def test_concurrent_drains_deliver_each_row_exactly_once(monkeypatch):
    rec = _Recorder(delay=0.05)
    monkeypatch.setattr(ns, "_send_webhook", rec)
    ids = await _enqueue(6)
    try:
        results = await asyncio.gather(drain_outbox(limit=4), drain_outbox(limit=4), drain_outbox(limit=4))
        assert sum(results) == 6
        delivered = [d for d, _ in rec.calls]
        assert sorted(delivered) == sorted(str(i) for i in ids)
        assert len(delivered) == len(set(delivered))
        rows = await _rows(ids)
        assert all(r.status == "sent" and r.attempts == 1 for r in rows.values())
    finally:
        await _purge(ids)


@db_test
async def test_drain_respects_limit_and_fifo_order(monkeypatch):
    rec = _Recorder()
    monkeypatch.setattr(ns, "_send_webhook", rec)
    older = await _enqueue(2, age_seconds=120)
    newer = await _enqueue(2)
    try:
        assert await drain_outbox(limit=2) == 2
        assert [d for d, _ in rec.calls] == [str(i) for i in older]
        assert await drain_outbox(limit=10) == 2
    finally:
        await _purge(older + newer)


# ---------------------------------------------------------------- enqueue rules
@db_test
async def test_emit_company_webhook_event_honours_settings():
    cid = uuid.uuid4()
    key = f"notify:{cid}"
    try:
        # no settings at all → nothing enqueued
        assert await emit_company_webhook_event(cid, "attendance.checked_in", {"x": 1}) is False

        async with async_session() as db:
            db.add(SystemSetting(key=key, value={"webhookUrl": "https://example.invalid/h", "events": ["attendance.checked_out"]}))
            await db.commit()
        assert await emit_company_webhook_event(cid, "attendance.checked_in", {"x": 1}) is False
        assert await emit_company_webhook_event(cid, "attendance.checked_out", {"x": 2}) is True

        async with async_session() as db:
            row = await db.get(SystemSetting, key)
            row.value = {"webhookUrl": "https://example.invalid/h", "events": ["*"], "webhookSecret": "s3"}
            await db.commit()
        assert await emit_company_webhook_event(cid, "anything.else", {"x": 3}) is True

        async with async_session() as db:
            res = await db.execute(
                select(NotificationOutbox).where(NotificationOutbox.companyId == cid).order_by(NotificationOutbox.createdAt)
            )
            rows = res.scalars().all()
        assert [r.event for r in rows] == ["attendance.checked_out", "anything.else"]
        assert all(r.channel == "webhook" and r.status == "pending" and r.attempts == 0 for r in rows)
        assert rows[1].payload["webhookSecret"] == "s3"
        assert rows[1].payload["data"] == {"x": 3}
    finally:
        async with async_session() as db:
            await db.execute(NotificationOutbox.__table__.delete().where(NotificationOutbox.companyId == cid))
            await db.execute(SystemSetting.__table__.delete().where(SystemSetting.key == key))
            await db.commit()
