"""Sprint 4 (BL-10 & BL-11): Roster Calendar, Shift Swap & Mobile Field Check-In Anti-Mock GPS."""
from __future__ import annotations

import os

import pytest
import pytest_asyncio

if not os.environ.get("DPU_TEST_DB_READY"):
    pytest.skip(
        "No test database: set TEST_DATABASE_URL or `pip install pgserver`",
        allow_module_level=True,
    )

from src.config.database import async_session  # noqa: E402
from src.models.company_employee import CompanyEmployee  # noqa: E402
from src.models.hr_schedule import WorkShift  # noqa: E402
from src.models.member import Member, RoleType, StatusType  # noqa: E402
from src.routes import employee_timestamp_routes, hr_routes  # noqa: E402
from tests.support import build_app, client, seed_world, teardown_world  # noqa: E402

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def world():
    w = await seed_world()
    async with async_session() as db:
        m2 = Member(
            username="colleague-s4",
            email="colleague-s4@test.local",
            passwordHash="hashed-password-placeholder",
            firstName="Colleague",
            lastName="Two",
            role=RoleType.MEMBER,
            status=StatusType.ENABLE,
        )
        db.add(m2)
        await db.flush()
        ce2 = CompanyEmployee(
            companyId=w.a.company.companyId,
            memberId=m2.memberId,
            positionId=w.a.employee_employment.positionId,
            departmentId=w.a.employee_employment.departmentId,
            employeeId="EMP-S4-02",
        )
        db.add(ce2)
        s_day = WorkShift(
            companyId=w.a.company.companyId,
            name="Day Shift",
            startTime="08:30",
            endTime="17:30",
            isDefault=True,
        )
        s_night = WorkShift(
            companyId=w.a.company.companyId,
            name="Night Shift",
            startTime="22:00",
            endTime="06:00",
            isCrossMidnight=True,
        )
        db.add_all([s_day, s_night])
        await db.commit()
        await db.refresh(ce2)
        await db.refresh(s_day)
        await db.refresh(s_night)
        w.colleague_id = ce2.company_employeeId
        w.shift_day_id = s_day.shiftId
        w.shift_night_id = s_night.shiftId

    w.app = build_app(
        (hr_routes.router, "/hr"),
        (employee_timestamp_routes.router, "/timestamp"),
    )
    yield w
    await teardown_world(w)


async def test_roster_generate_and_shift_swap_approval(world):
    cid = str(world.a.company.companyId)
    emp1 = str(world.a.employee_employment.company_employeeId)
    emp2 = str(world.colleague_id)
    s_day = str(world.shift_day_id)
    s_night = str(world.shift_night_id)

    async with client(world.app) as c:
        # Upsert explicit roster entries for 2026-12-01
        r_put = await c.put(
            f"/hr/company/{cid}/roster",
            json={
                "entries": [
                    {"company_employeeId": emp1, "workDate": "2026-12-01", "shiftId": s_day},
                    {"company_employeeId": emp2, "workDate": "2026-12-01", "shiftId": s_night},
                ],
                "generate": {
                    "employeeIds": [emp1],
                    "startDate": "2026-12-02",
                    "endDate": "2026-12-05",
                    "patternShiftIds": [s_day, s_night],
                    "workDays": 2,
                    "offDays": 1,
                    "isFlexible": True,
                },
            },
            headers=world.auth("admin_a"),
        )
        assert r_put.status_code == 200, r_put.text
        assert r_put.json()["updated"] == 6

        r_get = await c.get(
            f"/hr/company/{cid}/roster",
            params={"startDate": "2026-12-01", "endDate": "2026-12-05"},
            headers=world.auth("admin_a"),
        )
        assert r_get.status_code == 200
        assert len(r_get.json()) >= 6

        # Create shift swap request on 2026-12-01
        r_swap = await c.post(
            f"/hr/company/{cid}/shift-swaps",
            json={
                "requesterEmployeeId": emp1,
                "targetEmployeeId": emp2,
                "workDate": "2026-12-01",
                "reason": "Family appointment",
            },
            headers=world.auth("admin_a"),
        )
        assert r_swap.status_code == 201, r_swap.text
        swap_id = r_swap.json()["swapId"]
        assert r_swap.json()["status"] == "PENDING"

        # Approve swap -> roster entries should exchange shiftIds
        r_dec = await c.post(
            f"/hr/company/{cid}/shift-swaps/{swap_id}/approval",
            json={"status": "APPROVED"},
            headers=world.auth("admin_a"),
        )
        assert r_dec.status_code == 200, r_dec.text
        assert r_dec.json()["status"] == "APPROVED"

        r_after = await c.get(
            f"/hr/company/{cid}/roster",
            params={"startDate": "2026-12-01", "endDate": "2026-12-01"},
            headers=world.auth("admin_a"),
        )
        by_emp = {row["company_employeeId"]: row["shiftId"] for row in r_after.json()}
        assert by_emp[emp1] == s_night
        assert by_emp[emp2] == s_day


async def test_mobile_checkin_anti_mock_and_impossible_travel(world):
    cid = str(world.a.company.companyId)
    emp1 = str(world.a.employee_employment.company_employeeId)

    async with client(world.app) as c:
        # 1. Valid mobile field check-in in Bangkok
        r_ok = await c.post(
            f"/timestamp/company/{cid}/mobile-checkin",
            json={
                "company_employeeId": emp1,
                "timestampType": 1,
                "latitude": 13.7563,
                "longitude": 100.5018,
                "gpsAccuracy": 18,
                "wifiSsid": "Sentinel-Site-WiFi",
                "wifiBssid": "AA:BB:CC:DD:EE:FF",
                "locationName": "Bangkok Client Site",
            },
            headers=world.auth("admin_a"),
        )
        assert r_ok.status_code == 200, r_ok.text
        d_ok = r_ok.json()
        assert d_ok["status"] == "OK"
        assert d_ok["isMockGps"] is False
        assert d_ok["gpsIntegrityFlag"] is None
        assert d_ok["wifiSsid"] == "Sentinel-Site-WiFi"

        # 2. Mock GPS + Low accuracy
        r_mock = await c.post(
            f"/timestamp/company/{cid}/mobile-checkin",
            json={
                "company_employeeId": emp1,
                "timestampType": 1,
                "latitude": 13.7564,
                "longitude": 100.5019,
                "gpsAccuracy": 1200,
                "isMockLocation": True,
            },
            headers=world.auth("admin_a"),
        )
        assert r_mock.status_code == 200, r_mock.text
        d_mock = r_mock.json()
        assert d_mock["status"] == "WARNING"
        assert d_mock["isMockGps"] is True
        assert "MOCK_LOCATION" in d_mock["gpsIntegrityFlag"]
        assert "LOW_ACCURACY" in d_mock["gpsIntegrityFlag"]

        # 3. Impossible travel: Bangkok -> Chiang Mai (~580 km) immediately
        r_jump = await c.post(
            f"/timestamp/company/{cid}/mobile-checkin",
            json={
                "company_employeeId": emp1,
                "timestampType": 2,
                "latitude": 18.7883,
                "longitude": 98.9853,
                "gpsAccuracy": 15,
            },
            headers=world.auth("admin_a"),
        )
        assert r_jump.status_code == 200, r_jump.text
        d_jump = r_jump.json()
        assert d_jump["status"] == "WARNING"
        assert d_jump["isMockGps"] is True
        assert "IMPOSSIBLE_TRAVEL" in d_jump["gpsIntegrityFlag"]
