"""Sprint 5 (BL-12 & BL-13): Offline Kiosk HMAC Sync & Fire Alarm Fail-Safe / Entry-Exit Muster Roll."""
from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime, timezone

import pytest
import pytest_asyncio

if not os.environ.get("DPU_TEST_DB_READY"):
    pytest.skip(
        "No test database: set TEST_DATABASE_URL or `pip install pgserver`",
        allow_module_level=True,
    )

from src.routes import employee_timestamp_routes, sentinel_routes  # noqa: E402
from tests.support import build_app, client, seed_world, teardown_world  # noqa: E402

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def world():
    w = await seed_world()
    w.app = build_app(
        (employee_timestamp_routes.router, "/timestamp"),
        (sentinel_routes.router, "/sentinel"),
    )
    yield w
    await teardown_world(w)


async def test_offline_hmac_sync_and_tamper_rejection(world):
    cid = str(world.a.company.companyId)
    emp_id = str(world.a.employee_employment.company_employeeId)

    async with client(world.app) as c:
        r_key = await c.get(
            f"/timestamp/company/{cid}/offline-sync-key",
            headers=world.auth("admin_a"),
        )
        assert r_key.status_code == 200, r_key.text
        hmac_key = r_key.json()["hmacKey"]
        assert len(hmac_key) == 64

        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000) - 60_000
        client_id = "punch_test_offline_001"
        canonical = f"{cid}|{client_id}|{now_ms}|CHECK_IN".encode("utf-8")
        sig = hmac.new(bytes.fromhex(hmac_key), canonical, hashlib.sha256).hexdigest()

        # 1. Valid signed offline punch -> SYNCED
        r_sync = await c.post(
            f"/timestamp/company/{cid}/offline-sync",
            json={
                "clientId": client_id,
                "capturedAtMs": now_ms,
                "hmacSignature": sig,
                "punchType": "CHECK_IN",
                "company_employeeId": emp_id,
                "latitude": 13.7563,
                "longitude": 100.5018,
            },
            headers=world.auth("admin_a"),
        )
        assert r_sync.status_code == 200, r_sync.text
        assert r_sync.json()["status"] == "SYNCED"
        assert r_sync.json()["isOfflineSync"] is True

        # 2. Idempotent duplicate replay -> DUPLICATE
        r_dup = await c.post(
            f"/timestamp/company/{cid}/offline-sync",
            json={
                "clientId": client_id,
                "capturedAtMs": now_ms,
                "hmacSignature": sig,
                "punchType": "CHECK_IN",
                "company_employeeId": emp_id,
            },
            headers=world.auth("admin_a"),
        )
        assert r_dup.status_code == 200, r_dup.text
        assert r_dup.json()["status"] == "DUPLICATE"

        # 3. Tampered signature -> 403
        r_bad = await c.post(
            f"/timestamp/company/{cid}/offline-sync",
            json={
                "clientId": "punch_tamper_002",
                "capturedAtMs": now_ms,
                "hmacSignature": "0" * 64,
                "punchType": "CHECK_IN",
                "company_employeeId": emp_id,
            },
            headers=world.auth("admin_a"),
        )
        assert r_bad.status_code == 403

        # 4. Future timestamp (>5m) with valid signature -> 400
        future_ms = int(datetime.now(timezone.utc).timestamp() * 1000) + 15 * 60 * 1000
        fut_sig = hmac.new(
            bytes.fromhex(hmac_key),
            f"{cid}|punch_future_003|{future_ms}|CHECK_IN".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        r_fut = await c.post(
            f"/timestamp/company/{cid}/offline-sync",
            json={
                "clientId": "punch_future_003",
                "capturedAtMs": future_ms,
                "hmacSignature": fut_sig,
                "punchType": "CHECK_IN",
                "company_employeeId": emp_id,
            },
            headers=world.auth("admin_a"),
        )
        assert r_fut.status_code == 400


async def test_fire_alarm_unlock_all_and_exit_deducts_muster(world):
    cid = str(world.a.company.companyId)
    emp_id = str(world.a.employee_employment.company_employeeId)

    async with client(world.app) as c:
        # Create ENTRY and EXIT zones
        r_in = await c.post(
            f"/sentinel/company/{cid}/zones",
            json={"name": "Main Entry", "code": "IN-01", "direction": "ENTRY"},
            headers=world.auth("admin_a"),
        )
        assert r_in.status_code == 200, r_in.text
        assert r_in.json()["direction"] == "ENTRY"

        r_out = await c.post(
            f"/sentinel/company/{cid}/zones",
            json={"name": "Main Exit", "code": "OUT-01", "direction": "EXIT"},
            headers=world.auth("admin_a"),
        )
        assert r_out.status_code == 200, r_out.text
        assert r_out.json()["direction"] == "EXIT"

        # Trigger Fire Alarm -> unlocks all active zones
        r_fire = await c.post(
            f"/sentinel/company/{cid}/fire-alarm",
            json={"reason": "Smoke detector Zone A"},
            headers=world.auth("admin_a"),
        )
        assert r_fire.status_code == 200, r_fire.text
        d_fire = r_fire.json()
        assert d_fire["status"] == "FIRE_ALARM_ACTIVE"
        assert d_fire["unlockedCount"] >= 2
        assert d_fire["incident"]["eventType"] == "FIRE_ALARM_TRIGGERED"
        assert d_fire["incident"]["severity"] == "CRITICAL"

        # Reset Fire Alarm
        r_rst = await c.post(
            f"/sentinel/company/{cid}/fire-alarm/reset",
            json={"reason": "Drill complete"},
            headers=world.auth("admin_a"),
        )
        assert r_rst.status_code == 200, r_rst.text
        assert r_rst.json()["status"] == "NORMAL"
        assert r_rst.json()["incident"]["eventType"] == "FIRE_ALARM_RESET"

        # Check-out employee -> muster roll must exclude them
        r_key = await c.get(
            f"/timestamp/company/{cid}/offline-sync-key",
            headers=world.auth("admin_a"),
        )
        hmac_key = r_key.json()["hmacKey"]
        out_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        out_sig = hmac.new(
            bytes.fromhex(hmac_key),
            f"{cid}|punch_checkout_004|{out_ms}|CHECK_OUT".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        r_out_ts = await c.post(
            f"/timestamp/company/{cid}/offline-sync",
            json={
                "clientId": "punch_checkout_004",
                "capturedAtMs": out_ms,
                "hmacSignature": out_sig,
                "punchType": "CHECK_OUT",
                "company_employeeId": emp_id,
            },
            headers=world.auth("admin_a"),
        )
        assert r_out_ts.status_code == 200, r_out_ts.text

        r_muster = await c.get(
            f"/sentinel/company/{cid}/muster",
            headers=world.auth("admin_a"),
        )
        assert r_muster.status_code == 200, r_muster.text
        subject_ids = {item["subjectId"] for item in r_muster.json()["items"]}
        assert emp_id not in subject_ids
