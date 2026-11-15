"""Tests for Multi-Region DR Active-Active replication & topology."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest

from src.services.dr_replication_service import (
    apply_incoming_replication_event,
    build_replication_envelope,
    get_region_topology,
    sign_replication_payload,
    verify_replication_signature,
)


def test_dr_envelope_and_hmac_signature() -> None:
    cid = uuid.uuid4()
    env = build_replication_envelope(
        entity_type="MODULE_CONFIG",
        company_id=cid,
        action="UPDATE",
        payload={"modules": ["ATTENDANCE", "WATCHLIST"]},
    )
    raw = json.dumps(env, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sig = sign_replication_payload(raw)

    assert verify_replication_signature(raw, sig) is True
    assert verify_replication_signature(raw + b"x", sig) is False
    assert verify_replication_signature(raw, None) is False


@pytest.mark.asyncio
async def test_apply_incoming_replication_event_idempotency_and_cache_invalidation() -> None:
    cid = uuid.uuid4()
    env = {
        "eventId": "evt-dr-001",
        "originRegion": "ap-southeast-3",
        "entityType": "ALL",
        "companyId": str(cid),
        "action": "UPDATE",
        "payload": {},
    }

    with (
        patch(
            "src.services.dr_replication_service.kiosk_scan_debounce_check",
            new_callable=AsyncMock,
            side_effect=[True, False],
        ),
        patch(
            "src.services.dr_replication_service.cache_delete",
            new_callable=AsyncMock,
        ) as del_mock,
    ):
        first = await apply_incoming_replication_event(env)
        assert first["applied"] is True
        assert first["duplicate"] is False
        assert f"sv:modcfg:{cid}" in first["invalidatedCaches"]
        assert f"sv:zones:{cid}" in first["invalidatedCaches"]
        assert del_mock.await_count == 2

        second = await apply_incoming_replication_event(env)
        assert second["applied"] is False
        assert second["duplicate"] is True
        assert del_mock.await_count == 2


@pytest.mark.asyncio
async def test_get_region_topology_and_fallback() -> None:
    res_rec = MagicMock()
    res_rec.scalar.return_value = False
    res_lsn = MagicMock()
    res_lsn.scalar.return_value = "0/1A2B3C4"
    res_cnt = MagicMock()
    res_cnt.scalar.return_value = 2

    db = MagicMock()
    db.execute = AsyncMock(side_effect=[res_rec, res_lsn, res_cnt])

    topo = await get_region_topology(db)
    assert topo["dbMode"] == "PRIMARY_RW"
    assert topo["inRecovery"] is False
    assert topo["walLsn"] == "0/1A2B3C4"
    assert topo["connectedReplicas"] == 2

    db_err = MagicMock()
    db_err.execute = AsyncMock(side_effect=RuntimeError("sqlite has no pg_is_in_recovery"))
    topo_fallback = await get_region_topology(db_err)
    assert topo_fallback["dbMode"] == "UNKNOWN"
