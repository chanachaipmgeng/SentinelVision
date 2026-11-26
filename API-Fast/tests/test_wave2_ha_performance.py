"""Wave 2 (v7.1.0) HA Scaling, Multi-Replica Realtime, Outbox & Hot-Path Performance tests."""
from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.controllers import sentinel_controller as sc  # noqa: E402
from src.models.camera import Camera  # noqa: E402
from src.routes import sentinel_routes  # noqa: E402
from src.models.member import Member, StatusType  # noqa: E402
from src.models.sentinel import SentinelEvent, SentinelIncidentLog  # noqa: E402
from src.security.deps import verify_kiosk_token_db  # noqa: E402
from src.security.jwt import create_access_token, create_kiosk_token, hash_kiosk_token  # noqa: E402
from src.services import api_key_service  # noqa: E402
from src.services import cctv_analysis_service as cctv_svc  # noqa: E402
from src.services import incident_ws_hub as ws_hub_mod  # noqa: E402
from src.services import notification_service as ns  # noqa: E402
from src.services import people_count_service as people_svc  # noqa: E402
from src.services import sentinel_incident_service as inc_svc  # noqa: E402
from src.utils import face_gpu_queue as gpuq  # noqa: E402


# ---------------------------------------------------------------------------
# 1. Incident WebSocket Auth (memberId claim + revocation)
# ---------------------------------------------------------------------------
def test_incident_ws_authenticates_member_id_and_rejects_revoked(monkeypatch):
    cid = uuid4()
    mid = uuid4()
    token = create_access_token(member_id=str(mid), username="ws_admin")
    member = Member(
        memberId=mid,
        username="ws_admin",
        passwordHash="x",
        status=StatusType.ENABLE,
        deletedAt=None,
    )

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=member)
    mock_session_cm = MagicMock()
    mock_session_cm.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session_cm.__aexit__ = AsyncMock(return_value=False)

    import src.config.database as db_mod
    import src.security.deps as deps_mod
    import src.services.token_revocation_service as rev_mod

    monkeypatch.setattr(db_mod, "async_session", lambda: mock_session_cm)
    monkeypatch.setattr(deps_mod, "assert_company_access", AsyncMock(return_value=None))
    monkeypatch.setattr(rev_mod, "is_token_revoked", AsyncMock(return_value=False))

    ws_app = FastAPI()
    ws_app.include_router(sentinel_routes.router, prefix="/sentinel")

    with TestClient(ws_app) as client:
        with client.websocket_connect(f"/sentinel/ws/incidents/{cid}?token={token}") as ws:
            assert ws is not None

    # Revoked token closes immediately with 4401
    monkeypatch.setattr(rev_mod, "is_token_revoked", AsyncMock(return_value=True))
    with TestClient(ws_app) as client:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(f"/sentinel/ws/incidents/{cid}?token={token}"):
                pass
        assert exc_info.value.code == 4401


# ---------------------------------------------------------------------------
# 2. Multi-Replica Redis Pub/Sub Hub Fanout & originNode Deduplication
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_incident_ws_hub_redis_fanout_and_origin_dedupe():
    cid = uuid4()
    ws = AsyncMock()
    ws.send_text = AsyncMock()
    await ws_hub_mod.incident_ws_hub.subscribe(cid, ws)
    try:
        # Message originating from the SAME node must be skipped
        same_node_msg = {
            "channel": f"sv:incidents:{cid}",
            "data": json.dumps(
                {
                    "type": "incident",
                    "originNode": ws_hub_mod._NODE_ID,
                    "data": {"incidentId": "same"},
                }
            ),
        }
        assert await ws_hub_mod.handle_redis_incident_message(same_node_msg) == 0
        ws.send_text.assert_not_awaited()

        # Message originating from a REMOTE replica must fan out locally without originNode leak
        remote_msg = {
            "channel": f"sv:incidents:{cid}".encode("utf-8"),
            "data": json.dumps(
                {
                    "type": "incident",
                    "originNode": "remote-replica-2",
                    "data": {"incidentId": "remote-1", "severity": "CRITICAL"},
                }
            ).encode("utf-8"),
        }
        delivered = await ws_hub_mod.handle_redis_incident_message(remote_msg)
        assert delivered == 1
        sent_payload = json.loads(ws.send_text.call_args.args[0])
        assert sent_payload["type"] == "incident"
        assert sent_payload["data"]["incidentId"] == "remote-1"
        assert "originNode" not in sent_payload
    finally:
        await ws_hub_mod.incident_ws_hub.unsubscribe(cid, ws)


# ---------------------------------------------------------------------------
# 3. Lock-free 3-Phase Outbox Backoff (nextAttemptAt even with old createdAt)
# ---------------------------------------------------------------------------
def test_outbox_backoff_respects_next_attempt_at_over_old_created_at():
    now_utc = datetime.now(timezone.utc)
    row = ns.NotificationOutbox(
        event="sentinel.alert",
        channel="webhook",
        payload={},
        status="pending",
        attempts=1,
    )
    row.createdAt = now_utc - timedelta(hours=2)
    row.nextAttemptAt = now_utc + timedelta(seconds=10)
    assert ns._backoff_ready(row, now_utc) is False

    row.nextAttemptAt = now_utc - timedelta(seconds=1)
    assert ns._backoff_ready(row, now_utc) is True


# ---------------------------------------------------------------------------
# 4. Bounded GPU Queue Enqueue Timeout & Graceful Stop
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_face_gpu_queue_saturation_raises_queue_full():
    await gpuq.stop_face_gpu_workers_for_tests()
    await gpuq.start_face_gpu_workers(workers=1, queue_size=8, devices=["cpu"])
    try:
        # Force pending_total == maxsize without filling real futures
        gpuq._pending_total = gpuq._maxsize
        with pytest.raises(asyncio.QueueFull):
            await gpuq.run_on_face_gpu(lambda: 1, kind="identify", timeout=0.05)
    finally:
        gpuq._pending_total = 0
        await gpuq.stop_face_gpu_workers()
        assert gpuq.face_gpu_queue_stats()["started"] is False


# ---------------------------------------------------------------------------
# 5. list_events Batched GROUP BY & Bulk Incident Location Enrichment
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_list_events_batches_counts_with_group_by():
    cid = uuid4()
    ev1 = SentinelEvent(
        eventId=uuid4(),
        companyId=cid,
        name="Summit A",
        startAt=datetime.now(timezone.utc),
        endAt=datetime.now(timezone.utc) + timedelta(hours=4),
        capacity=100,
        autoExpireDays=7,
        status="LIVE",
    )
    ev2 = SentinelEvent(
        eventId=uuid4(),
        companyId=cid,
        name="Summit B",
        startAt=datetime.now(timezone.utc),
        endAt=datetime.now(timezone.utc) + timedelta(hours=4),
        capacity=50,
        autoExpireDays=7,
        status="LIVE",
    )

    db = AsyncMock()
    res_events = MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[ev1, ev2]))))
    res_att = MagicMock(all=MagicMock(return_value=[(ev1.eventId, 12), (ev2.eventId, 5)]))
    res_chk = MagicMock(all=MagicMock(return_value=[(ev1.eventId, 9)]))
    db.execute = AsyncMock(side_effect=[res_events, res_att, res_chk])

    out = await sc.list_events(db, cid)
    assert db.execute.await_count == 3  # 1 events + 2 GROUP BY queries (never 2N+1)
    assert out[0]["attendeeCount"] == 12
    assert out[0]["checkedInCount"] == 9
    assert out[1]["attendeeCount"] == 5
    assert out[1]["checkedInCount"] == 0


@pytest.mark.asyncio
async def test_bulk_incident_actions_call_location_enrichment(monkeypatch):
    cid = uuid4()
    actor = uuid4()
    inc1 = SentinelIncidentLog(
        incidentId=uuid4(),
        companyId=cid,
        eventType="DOOR_FORCED",
        severity="HIGH",
        status=inc_svc.STATUS_OPEN,
        occurredAt=datetime.now(timezone.utc),
    )
    missing_id = uuid4()
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[inc1]))))
    )
    db.commit = AsyncMock()
    enrich_mock = AsyncMock(side_effect=lambda _d, _c, items: [{**it, "cameraName": "Gate 1"} for it in items])
    monkeypatch.setattr(inc_svc, "enrich_incidents_location_metadata", enrich_mock)
    monkeypatch.setattr(inc_svc, "queue_siem_incident_export", AsyncMock(return_value=False))

    res = await inc_svc.acknowledge_incidents_bulk(db, cid, [str(inc1.incidentId), str(missing_id)], actor)
    assert res["acknowledgedCount"] == 1
    assert res["skippedCount"] == 1
    assert res["acknowledged"][0]["cameraName"] == "Gate 1"
    assert enrich_mock.await_count == 1


# ---------------------------------------------------------------------------
# 6. Write-Amplification Throttling on lastSeenAt / lastUsedAt (60s window)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_kiosk_and_api_key_last_seen_throttled():
    cid = uuid4()
    did = uuid4()
    tok = create_kiosk_token(device_id=str(did), company_id=str(cid))
    fresh_now = datetime.now(timezone.utc) - timedelta(seconds=10)
    device = SimpleNamespace(
        deviceId=did,
        companyId=cid,
        revokedAt=None,
        tokenHash=hash_kiosk_token(tok),
        lastSeenAt=fresh_now,
    )
    company = SimpleNamespace(companyId=cid, lifecycleStatus="ACTIVE")

    db = AsyncMock()
    db.get = AsyncMock(side_effect=[device, company])
    db.commit = AsyncMock()

    await verify_kiosk_token_db(tok, db)
    db.commit.assert_not_awaited()
    assert device.lastSeenAt == fresh_now

    # Old lastSeenAt (>=60s) DOES trigger update + commit
    stale_now = datetime.now(timezone.utc) - timedelta(seconds=120)
    device.lastSeenAt = stale_now
    db.get = AsyncMock(side_effect=[device, company])
    await verify_kiosk_token_db(tok, db)
    db.commit.assert_awaited_once()
    assert device.lastSeenAt > stale_now

    # Same 60s throttle for CompanyApiKey.lastUsedAt
    raw_key = "sv_test_key_123456"
    api_row = SimpleNamespace(
        companyId=cid,
        revokedAt=None,
        lastUsedAt=datetime.now(timezone.utc) - timedelta(seconds=15),
    )
    db2 = AsyncMock()
    db2.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=api_row)))
    db2.get = AsyncMock(return_value=company)
    db2.commit = AsyncMock()
    assert await api_key_service.verify_bearer_api_key(db2, raw_key) is api_row
    db2.commit.assert_not_awaited()


# ---------------------------------------------------------------------------
# 7. Camera Worker Lease Claiming (CCTV & People Count)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_camera_lease_claiming_sets_lease_until(monkeypatch):
    cid = uuid4()
    cam = Camera(
        cameraId=uuid4(),
        companyId=cid,
        name="Lobby Cam",
        streamUrl="rtsp://example.invalid/live",
        analysisEnabled=True,
        isActive=True,
        aiConfig={"peopleEnabled": True, "roi_polygon": [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9]]},
    )

    monkeypatch.setattr(
        "src.services.company_ai_settings_service.resolve_cctv_camera_interval",
        AsyncMock(return_value=30),
    )
    db_cctv = AsyncMock()
    db_cctv.execute = AsyncMock(
        return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[cam]))))
    )
    db_cctv.commit = AsyncMock()
    claimed_cctv = await cctv_svc.claim_due_cameras(db_cctv, lease_seconds=90)
    assert len(claimed_cctv) == 1
    assert claimed_cctv[0].analysisLeaseUntil is not None
    db_cctv.commit.assert_awaited_once()

    db_people = AsyncMock()
    db_people.execute = AsyncMock(
        return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[cam]))))
    )
    db_people.commit = AsyncMock()
    claimed_people = await people_svc.claim_due_people_cameras(db_people, lease_seconds=90)
    assert len(claimed_people) == 1
    assert claimed_people[0].peopleLeaseUntil is not None
    db_people.commit.assert_awaited_once()
