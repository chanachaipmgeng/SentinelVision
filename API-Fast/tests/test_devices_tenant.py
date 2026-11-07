"""D2 device CRUD/heartbeat/rotate + D5 tenant lifecycle/quota gates."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytestmark = pytest.mark.skipif(
    not os.environ.get("DPU_TEST_DB_READY"),
    reason="No test database: set TEST_DATABASE_URL or `pip install pgserver`",
)


@pytest.mark.asyncio
async def test_device_crud_heartbeat_rotate_and_revoke():
    from src.routes import device_routes
    from tests.support import build_app, client, seed_world, teardown_world

    world = await seed_world()
    app = build_app((device_routes.router, "/devices"))
    cid = world.a.company_id
    try:
        async with client(app) as http:
            # Create
            created = await http.post(
                f"/devices/company/{cid}/devices",
                headers=world.auth("admin_a"),
                json={
                    "name": "Lobby Gate",
                    "locationLabel": "Floor 1",
                    "stationMode": "ACCESS_CONTROL",
                    "appVersion": "2.1.0",
                },
            )
            assert created.status_code == 200, created.text
            body = created.json()
            assert body["name"] == "Lobby Gate"
            assert body["stationMode"] == "ACCESS_CONTROL"
            assert body["locationLabel"] == "Floor 1"
            assert body["pairingCode"]
            device_id = body["deviceId"]

            # Foreign tenant blocked
            denied = await http.get(
                f"/devices/company/{cid}/devices",
                headers=world.auth("admin_b"),
            )
            assert denied.status_code == 403

            # List
            listed = await http.get(
                f"/devices/company/{cid}/devices",
                headers=world.auth("admin_a"),
            )
            assert listed.status_code == 200
            assert any(r["deviceId"] == device_id for r in listed.json())

            # Patch binding
            patched = await http.patch(
                f"/devices/company/{cid}/devices/{device_id}",
                headers=world.auth("admin_a"),
                json={"stationMode": "ATTENDANCE", "zoneId": None},
            )
            assert patched.status_code == 200, patched.text
            assert patched.json()["stationMode"] == "ATTENDANCE"

            # Heartbeat via admin (device not yet paired — still allowed for admin)
            beat = await http.post(
                f"/devices/company/{cid}/devices/{device_id}/heartbeat",
                headers=world.auth("admin_a"),
                json={"fingerprint": "fp-abc", "appVersion": "2.1.1"},
            )
            assert beat.status_code == 200, beat.text
            assert beat.json()["fingerprint"] == "fp-abc"
            assert beat.json()["appVersion"] == "2.1.1"
            assert beat.json()["heartbeatAt"]

            # Rotate (re-pair)
            rotated = await http.post(
                f"/devices/company/{cid}/devices/{device_id}/rotate",
                headers=world.auth("admin_a"),
            )
            assert rotated.status_code == 200, rotated.text
            assert rotated.json()["pairingCode"]
            assert rotated.json()["pairingCode"] != body["pairingCode"]

            # Revoke
            revoked = await http.delete(
                f"/devices/company/{cid}/devices/{device_id}",
                headers=world.auth("admin_a"),
            )
            assert revoked.status_code == 200
            assert revoked.json()["isActive"] is False

            # Cannot rotate revoked
            again = await http.post(
                f"/devices/company/{cid}/devices/{device_id}/rotate",
                headers=world.auth("admin_a"),
            )
            assert again.status_code == 409
    finally:
        await teardown_world(world)


@pytest.mark.asyncio
async def test_device_quota_gate():
    from src.config.database import async_session
    from src.models.company import Company
    from src.routes import device_routes
    from tests.support import build_app, client, seed_world, teardown_world

    world = await seed_world()
    app = build_app((device_routes.router, "/devices"))
    cid = world.a.company_id
    try:
        async with async_session() as db:
            company = await db.get(Company, cid)
            # One device already seeded → cap at 1 blocks the next create.
            company.maxDevices = 1
            await db.commit()

        async with client(app) as http:
            blocked = await http.post(
                f"/devices/company/{cid}/devices",
                headers=world.auth("admin_a"),
                json={"name": "Overflow"},
            )
            assert blocked.status_code == 409, blocked.text
            assert "quota" in blocked.json()["detail"].lower()
    finally:
        await teardown_world(world)


@pytest.mark.asyncio
async def test_employee_quota_gate():
    from fastapi import HTTPException

    from src.config.database import async_session
    from src.models.company import Company
    from src.services.tenant_quota_service import assert_employee_quota
    from tests.support import seed_world, teardown_world

    world = await seed_world()
    cid = world.a.company_id
    try:
        async with async_session() as db:
            company = await db.get(Company, cid)
            # Two employees already (admin + emp) → cap at 2 blocks next hire.
            company.maxEmployees = 2
            await db.commit()
            await db.refresh(company)

            with pytest.raises(HTTPException) as exc:
                await assert_employee_quota(db, company)
            assert exc.value.status_code == 409
            assert "quota" in str(exc.value.detail).lower()
    finally:
        await teardown_world(world)


@pytest.mark.asyncio
async def test_tenant_suspend_blocks_and_resume():
    from src.routes import company_routes, device_routes, hr_routes
    from tests.support import build_app, client, seed_world, teardown_world

    world = await seed_world()
    app = build_app(
        (company_routes.router, "/companys"),
        (device_routes.router, "/devices"),
        (hr_routes.router, "/hr"),
    )
    cid = world.a.company_id
    try:
        async with client(app) as http:
            # Suspend as sysadmin
            suspended = await http.post(
                f"/companys/{cid}/suspend",
                headers=world.auth("sysadmin"),
            )
            assert suspended.status_code == 200, suspended.text
            assert suspended.json()["lifecycleStatus"] == "SUSPENDED"

            # Company admin blocked from devices
            blocked = await http.get(
                f"/devices/company/{cid}/devices",
                headers=world.auth("admin_a"),
            )
            assert blocked.status_code == 403
            assert "suspended" in blocked.json()["detail"].lower()

            # Sysadmin can still manage quotas
            quotas = await http.put(
                f"/companys/{cid}/quotas",
                headers=world.auth("sysadmin"),
                json={"packageCode": "STARTER", "gpuPriority": 1},
            )
            assert quotas.status_code == 200, quotas.text
            assert quotas.json()["packageCode"] == "STARTER"
            assert quotas.json()["quotas"]["maxDevices"] == 2

            # Resume
            resumed = await http.post(
                f"/companys/{cid}/resume",
                headers=world.auth("sysadmin"),
            )
            assert resumed.status_code == 200
            assert resumed.json()["lifecycleStatus"] == "ACTIVE"

            ok = await http.get(
                f"/devices/company/{cid}/devices",
                headers=world.auth("admin_a"),
            )
            assert ok.status_code == 200
    finally:
        await teardown_world(world)


@pytest.mark.asyncio
async def test_tenant_offboard_revokes_devices():
    from src.config.database import async_session
    from src.models.hr_schedule import KioskDevice
    from src.routes import company_routes
    from tests.support import build_app, client, seed_world, teardown_world

    world = await seed_world()
    app = build_app((company_routes.router, "/companys"))
    cid = world.a.company_id
    device_id = world.a.kiosk.deviceId
    try:
        async with client(app) as http:
            off = await http.post(
                f"/companys/{cid}/offboard",
                headers=world.auth("sysadmin"),
                json={"purgeDevices": True},
            )
            assert off.status_code == 200, off.text
            assert off.json()["lifecycleStatus"] == "OFFBOARDED"

        async with async_session() as db:
            device = await db.get(KioskDevice, device_id)
            assert device is not None
            assert device.revokedAt is not None
            assert device.tokenHash is None
    finally:
        await teardown_world(world)


def test_package_module_quotas_normalize():
    from fastapi import HTTPException
    from src.services.company_module_service import normalize_module_config, merge_module_config

    clean = normalize_module_config(
        {
            "enabledModules": ["ATTENDANCE", "EVENTS", "WATCHLIST"],
            "packageCode": "STARTER",
            "quotas": {"maxDevices": 2, "gpuPriority": 0},
        }
    )
    # STARTER allows only ATTENDANCE
    assert clean["enabledModules"] == ["ATTENDANCE"]
    assert clean["packageCode"] == "STARTER"
    assert clean["quotas"]["maxDevices"] == 2

    with pytest.raises(HTTPException):
        normalize_module_config({"packageCode": "NOPE"})

    merged = merge_module_config({"packageCode": "PRO", "quotas": {"gpuPriority": 5}})
    assert merged["packageCode"] == "PRO"
    assert merged["quotas"]["gpuPriority"] == 5
