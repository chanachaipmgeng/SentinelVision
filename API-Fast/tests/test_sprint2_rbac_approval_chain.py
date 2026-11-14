"""Sprint 2 (BL-06 & BL-07): Granular RBAC scoping, multi-level approval chain, and delegation."""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone

import pytest
import pytest_asyncio

if not os.environ.get("DPU_TEST_DB_READY"):
    pytest.skip(
        "No test database: set TEST_DATABASE_URL or `pip install pgserver`",
        allow_module_level=True,
    )

from src.config.database import async_session  # noqa: E402
from src.models.company_employee import CompanyEmployee  # noqa: E402
from src.models.company_location import CompanyLocation, LocationType  # noqa: E402
from src.routes import hr_routes, rbac_routes  # noqa: E402
from tests.support import build_app, client, seed_world, teardown_world  # noqa: E402

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def world():
    w = await seed_world()
    async with async_session() as db:
        emp = await db.get(CompanyEmployee, w.a.employee_employment.company_employeeId)
        emp.bossId = str(w.a.admin.memberId)
        loc = CompanyLocation(
            companyId=w.a.company.companyId,
            latitude=13.75,
            longitude=100.5,
            locationName="HQ Branch",
            radius=0.5,
            locationType=LocationType.PERMANENT,
        )
        db.add(loc)
        await db.commit()
        await db.refresh(loc)
        w.hq_location_id = loc.locationId
    w.app = build_app(
        (rbac_routes.router, "/rbac"),
        (hr_routes.router, "/hr"),
    )
    yield w
    await teardown_world(w)


async def test_rbac_roles_and_scoped_assignments(world):
    cid = str(world.a.company.companyId)
    async with client(world.app) as c:
        r_roles = await c.get("/rbac/roles", headers=world.auth("admin_a"))
        assert r_roles.status_code == 200
        codes = {r["code"] for r in r_roles.json()["roles"]}
        assert {"SYSTEM_ADMIN", "HR_ADMIN", "MANAGER", "SECURITY_GUARD", "EMPLOYEE"}.issubset(codes)

        r_create = await c.post(
            f"/rbac/company/{cid}/assignments",
            json={
                "memberId": str(world.a.employee.memberId),
                "roleCode": "SECURITY_GUARD",
                "departmentId": str(world.a.department.departmentId),
                "locationId": str(world.hq_location_id),
            },
            headers=world.auth("admin_a"),
        )
        assert r_create.status_code == 200
        created = r_create.json()
        assert created["roleCode"] == "SECURITY_GUARD"
        assert created["locationId"] == str(world.hq_location_id)

        r_list = await c.get(f"/rbac/company/{cid}/assignments", headers=world.auth("admin_a"))
        assert r_list.status_code == 200
        assert any(i["assignmentId"] == created["assignmentId"] for i in r_list.json()["items"])

        r_del = await c.delete(
            f"/rbac/company/{cid}/assignments/{created['assignmentId']}",
            headers=world.auth("admin_a"),
        )
        assert r_del.status_code == 200


async def test_multi_level_approval_chain_and_delegation(world):
    cid = str(world.a.company.companyId)
    emp_id = str(world.a.employee_employment.company_employeeId)
    today = date.today()

    async with client(world.app) as c:
        # Configure 2-level approval policy
        r_pol = await c.put(
            f"/hr/company/{cid}/approval-policy",
            json={
                "requestType": "ALL",
                "levels": [
                    {"level": 1, "role": "MANAGER", "label": "Line Manager"},
                    {"level": 2, "role": "HR_ADMIN", "label": "HR Final"},
                ],
            },
            headers=world.auth("admin_a"),
        )
        assert r_pol.status_code == 200
        assert len(r_pol.json()["levels"]) == 2

        # Create a regularization request -> starts at Level 1 of 2
        r_reg = await c.post(
            f"/hr/company/{cid}/regularizations",
            json={
                "company_employeeId": emp_id,
                "workDate": today.isoformat(),
                "requestedTimestamp": datetime.now(timezone.utc).isoformat(),
                "requestedType": 1,
                "reason": "Forgot badge",
            },
            headers=world.auth("emp_a"),
        )
        assert r_reg.status_code == 200
        reg_id = r_reg.json()["requestId"]
        assert r_reg.json()["approvalLevel"] == 1
        assert r_reg.json()["maxApprovalLevel"] == 2

        # Level 1 approval -> stays PENDING and advances to level 2
        r_step1 = await c.post(
            f"/hr/company/{cid}/regularizations/{reg_id}/approval",
            json={"approve": True},
            headers=world.auth("admin_a"),
        )
        assert r_step1.status_code == 200
        assert r_step1.json()["status"] == "PENDING"
        assert r_step1.json()["approvalLevel"] == 2
        assert len(r_step1.json()["approvalHistory"]) == 1

        # Level 2 approval -> final APPROVED
        r_step2 = await c.post(
            f"/hr/company/{cid}/regularizations/{reg_id}/approval",
            json={"approve": True},
            headers=world.auth("admin_a"),
        )
        assert r_step2.status_code == 200
        assert r_step2.json()["status"] == "APPROVED"
        assert len(r_step2.json()["approvalHistory"]) == 2

        # Create delegation from admin -> employee for today
        r_delg = await c.post(
            f"/hr/company/{cid}/approval-delegations",
            json={
                "delegateMemberId": str(world.a.employee.memberId),
                "startDate": (today - timedelta(days=1)).isoformat(),
                "endDate": (today + timedelta(days=1)).isoformat(),
                "reason": "Annual leave",
            },
            headers=world.auth("admin_a"),
        )
        assert r_delg.status_code == 200
        delegation_id = r_delg.json()["delegationId"]

        # Clean up delegation & reset policy to 1-level
        assert (
            await c.delete(
                f"/hr/company/{cid}/approval-delegations/{delegation_id}",
                headers=world.auth("admin_a"),
            )
        ).status_code == 200
        assert (
            await c.put(
                f"/hr/company/{cid}/approval-policy",
                json={"requestType": "ALL", "levels": [{"level": 1, "role": "MANAGER", "label": "Line Manager"}]},
                headers=world.auth("admin_a"),
            )
        ).status_code == 200
