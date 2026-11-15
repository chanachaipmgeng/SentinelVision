"""Sprint 6 (BL-14..BL-17): Tailgating/Anti-Passback, Camera/Door Health, Vector Re-Index, Edge/SAML SSO."""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import os

import pytest
import pytest_asyncio
from sqlalchemy import select

if not os.environ.get("DPU_TEST_DB_READY"):
    pytest.skip(
        "No test database: set TEST_DATABASE_URL or `pip install pgserver`",
        allow_module_level=True,
    )

from src.config.database import async_session  # noqa: E402
from src.models.camera import Camera  # noqa: E402
from src.models.face_encoding import FaceEncoding  # noqa: E402
from src.models.sentinel import SentinelAccessZone, SentinelIdentity  # noqa: E402
from src.routes import auth_routes, sentinel_routes  # noqa: E402
from src.services.notification_service import NotificationOutbox  # noqa: E402
from tests.support import build_app, client, seed_world, teardown_world  # noqa: E402

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def world():
    w = await seed_world()
    w.app = build_app(
        (auth_routes.router, "/auth"),
        (sentinel_routes.router, "/sentinel"),
    )
    yield w
    await teardown_world(w)


async def test_tailgating_and_anti_passback(world):
    cid = str(world.a.company.companyId)
    emp_member_id = str(world.a.employee.memberId)

    async with client(world.app) as c:
        z_resp = await c.post(
            f"/sentinel/company/{cid}/zones",
            headers=world.auth("admin_a"),
            json={
                "name": "Server Vault",
                "code": "VAULT-01",
                "direction": "ENTRY",
                "antiPassbackEnabled": True,
                "antiPassbackMinutes": 10,
            },
        )
        assert z_resp.status_code == 200, z_resp.text
        zone = z_resp.json()
        assert zone["antiPassbackEnabled"] is True
        zone_id = zone["zoneId"]

        # 1) First valid ENTRY passes
        r1 = await c.post(
            f"/sentinel/company/{cid}/zones/{zone_id}/evaluate-access",
            headers=world.auth("admin_a"),
            json={
                "memberId": emp_member_id,
                "subjectName": "Alice",
                "direction": "ENTRY",
                "peopleCount": 1,
            },
        )
        assert r1.status_code == 200, r1.text
        assert r1.json()["allowed"] is True
        assert r1.json()["antiPassbackViolation"] is False

        # 2) Consecutive ENTRY within 10m triggers Anti-Passback + Tailgating when peopleCount=2
        r2 = await c.post(
            f"/sentinel/company/{cid}/zones/{zone_id}/evaluate-access",
            headers=world.auth("admin_a"),
            json={
                "memberId": emp_member_id,
                "subjectName": "Alice",
                "direction": "ENTRY",
                "peopleCount": 2,
            },
        )
        assert r2.status_code == 200, r2.text
        body2 = r2.json()
        assert body2["tailgatingDetected"] is True
        assert body2["antiPassbackViolation"] is True
        assert body2["allowed"] is False
        ev_types = {inc["eventType"] for inc in body2["incidents"]}
        assert "TAILGATING_DETECTED" in ev_types
        assert "ANTI_PASSBACK_VIOLATION" in ev_types


async def test_health_check_camera_offline_and_door_held_open(world):
    cid = str(world.a.company.companyId)

    async with async_session() as db:
        cam = Camera(
            companyId=world.a.company.companyId,
            name="Lobby RTSP Cam",
            streamUrl="rtsp://127.0.0.1:554/stream1",
            status="offline",
            lastPingAt=datetime.now(timezone.utc) - timedelta(minutes=10),
        )
        zone = SentinelAccessZone(
            companyId=world.a.company.companyId,
            name="Fire Exit Door",
            code="EXIT-99",
            doorHeldMaxSeconds=15,
            doorOpenSince=datetime.now(timezone.utc) - timedelta(seconds=90),
            isActive=True,
        )
        db.add_all([cam, zone])
        await db.commit()

    async with client(world.app) as c:
        r = await c.post(
            f"/sentinel/company/{cid}/health-check",
            headers=world.auth("admin_a"),
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert len(data["offlineCameras"]) >= 1
        assert len(data["doorHeldOpen"]) >= 1

    async with async_session() as db:
        outbox_rows = (
            await db.execute(
                select(NotificationOutbox).where(
                    NotificationOutbox.companyId == world.a.company.companyId,
                    NotificationOutbox.event == "DOOR_HELD_OPEN",
                )
            )
        ).scalars().all()
        assert len(outbox_rows) >= 1


async def test_batch_vector_reindex(world):
    cid = str(world.a.company.companyId)
    raw_vec = [2.0] + [0.0] * 511

    async with async_session() as db:
        enc = FaceEncoding(
            memberId=world.a.employee.memberId,
            embedding=raw_vec,
            modelVersion="buffalo_l-v1",
        )
        ident = SentinelIdentity(
            companyId=world.a.company.companyId,
            identityType="VIP",
            fullName="VIP Vector",
            embedding=raw_vec,
            status="ACTIVE",
        )
        db.add_all([enc, ident])
        await db.commit()

    async with client(world.app) as c:
        r = await c.post(
            f"/sentinel/company/{cid}/reindex-vectors",
            headers=world.auth("admin_a"),
            json={"targetModel": "buffalo_l-512d-norm-v2"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "COMPLETED"
        assert body["employeeVectors"] >= 1
        assert body["sentinelVectors"] >= 1
        assert body["targetModel"] == "buffalo_l-512d-norm-v2"

        r_status = await c.get(
            f"/sentinel/company/{cid}/reindex-status",
            headers=world.auth("admin_a"),
        )
        assert r_status.status_code == 200, r_status.text
        assert r_status.json()["status"] == "COMPLETED"

    async with async_session() as db:
        await db.execute(
            FaceEncoding.__table__.delete().where(FaceEncoding.memberId == world.a.employee.memberId)
        )
        await db.commit()


async def test_edge_unlock_osdp_and_saml_acs_sso(world):
    cid = str(world.a.company.companyId)

    async with client(world.app) as c:
        z_resp = await c.post(
            f"/sentinel/company/{cid}/zones",
            headers=world.auth("admin_a"),
            json={
                "name": "OSDP Turnstile",
                "code": "OSDP-01",
                "edgeProtocol": "OSDP",
                "osdpAddress": 3,
            },
        )
        assert z_resp.status_code == 200, z_resp.text
        zone_id = z_resp.json()["zoneId"]

        unlock_resp = await c.post(
            f"/sentinel/company/{cid}/zones/{zone_id}/edge-unlock",
            headers=world.auth("admin_a"),
            json={"durationMs": 2000},
        )
        assert unlock_resp.status_code == 200, unlock_resp.text
        u_data = unlock_resp.json()
        assert u_data["protocol"] == "OSDP"
        assert u_data["osdpAddress"] == 3
        assert u_data["frame"]["osdpCommand"] == "osdp_OUT"

        # Enable SSO policy for company A
        pol_resp = await c.put(
            f"/auth/sso/policy/{cid}",
            headers=world.auth("admin_a"),
            json={
                "jitProvisioning": True,
                "allowedEmailDomains": [],
                "defaultDepartmentId": str(world.a.employee_employment.departmentId),
                "defaultPositionId": str(world.a.employee_employment.positionId),
            },
        )
        assert pol_resp.status_code == 200, pol_resp.text

        saml_xml = "<Response><Assertion><Subject><NameID>saml.jit@example.com</NameID></Subject></Assertion></Response>"
        saml_b64 = base64.b64encode(saml_xml.encode("utf-8")).decode("ascii")
        acs_resp = await c.post(
            "/auth/sso/saml/acs",
            json={"companyId": cid, "SAMLResponse": saml_b64, "name": "SAML JIT User"},
        )
        assert acs_resp.status_code == 200, acs_resp.text
        assert acs_resp.json().get("accessToken")

    async with async_session() as db:
        from src.models.company_employee import CompanyEmployee
        from src.models.member import Member

        jit_member = (
            await db.execute(select(Member).where(Member.email == "saml.jit@example.com"))
        ).scalar_one_or_none()
        if jit_member is not None:
            await db.execute(
                CompanyEmployee.__table__.delete().where(CompanyEmployee.memberId == jit_member.memberId)
            )
            await db.execute(Member.__table__.delete().where(Member.memberId == jit_member.memberId))
            await db.commit()
