"""Sprint 3 (BL-08 & BL-09): Leave Policy, Thai Labor OT Rate Engine, and 5-Angle Quality Gate."""
from __future__ import annotations

import os
from datetime import date

import numpy as np
import pytest
import pytest_asyncio

if not os.environ.get("DPU_TEST_DB_READY"):
    pytest.skip(
        "No test database: set TEST_DATABASE_URL or `pip install pgserver`",
        allow_module_level=True,
    )

from src.config.database import async_session  # noqa: E402
from src.models.attendance_daily import AttendanceDaily  # noqa: E402
from src.models.company_employee import CompanyEmployee  # noqa: E402
from src.routes import hr_routes  # noqa: E402
from src.utils.enrollment_quality import check_enrollment_quality_bgr  # noqa: E402
from tests.support import build_app, client, seed_world, teardown_world  # noqa: E402

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def world():
    w = await seed_world()
    async with async_session() as db:
        emp = await db.get(CompanyEmployee, w.a.employee_employment.company_employeeId)
        emp.bossId = str(w.a.admin.memberId)
        db.add(
            AttendanceDaily(
                companyId=w.a.company.companyId,
                employeeId=w.a.employee_employment.company_employeeId,
                workDate=date(2026, 11, 10),  # Tuesday (workday)
                status="PRESENT",
                workMinutes=540,
                lateMinutes=0,
                otMinutes=60,
            )
        )
        db.add(
            AttendanceDaily(
                companyId=w.a.company.companyId,
                employeeId=w.a.employee_employment.company_employeeId,
                workDate=date(2026, 11, 14),  # Saturday (weekend)
                status="PRESENT",
                workMinutes=540,
                lateMinutes=0,
                otMinutes=60,
            )
        )
        await db.commit()
    w.app = build_app((hr_routes.router, "/hr"))
    yield w
    await teardown_world(w)


async def test_leave_policy_hourly_and_ot_payroll_summary(world):
    cid = str(world.a.company.companyId)
    emp_id = str(world.a.employee_employment.company_employeeId)

    async with client(world.app) as c:
        r_pol = await c.put(
            f"/hr/company/{cid}/leave-policies/SICK",
            json={
                "displayName": "Sick Leave",
                "annualQuotaDays": 30,
                "allowCarryOver": False,
                "allowHalfDay": True,
                "allowHourly": True,
                "requireMedicalCert": True,
                "medicalCertMinDays": 2,
            },
            headers=world.auth("admin_a"),
        )
        assert r_pol.status_code == 200
        assert r_pol.json()["requireMedicalCert"] is True

        # 2-day sick leave without medical cert should be rejected
        r_missing_cert = await c.post(
            f"/hr/company/{cid}/leaves",
            json={
                "company_employeeId": emp_id,
                "startDate": "2026-11-18",
                "endDate": "2026-11-19",
                "leaveType": "SICK",
                "leaveUnit": "FULL_DAY",
                "reason": "Fever",
            },
            headers=world.auth("admin_a"),
        )
        assert r_missing_cert.status_code == 400

        # Hourly sick leave (2h) should succeed and accumulate in payroll summary
        r_hourly = await c.post(
            f"/hr/company/{cid}/leaves",
            json={
                "company_employeeId": emp_id,
                "startDate": "2026-11-12",
                "endDate": "2026-11-12",
                "leaveType": "SICK",
                "leaveUnit": "HOURLY",
                "leaveHours": 2.0,
                "reason": "Clinic",
                "autoApprove": True,
            },
            headers=world.auth("admin_a"),
        )
        assert r_hourly.status_code == 200
        assert r_hourly.json()["leaveUnit"] == "HOURLY"
        assert r_hourly.json()["leaveHours"] == 2.0

        r_ot = await c.put(
            f"/hr/company/{cid}/ot-policy",
            json={
                "normalOtRate": 1.0,
                "workdayOtRate": 1.5,
                "holidayWorkRate": 2.0,
                "holidayOtRate": 3.0,
                "dailyWorkMinutes": 480,
                "roundingMinutes": 15,
            },
            headers=world.auth("admin_a"),
        )
        assert r_ot.status_code == 200

        r_sum = await c.get(
            f"/hr/company/{cid}/payroll-summary",
            params={"startDate": "2026-11-01", "endDate": "2026-11-30"},
            headers=world.auth("admin_a"),
        )
        assert r_sum.status_code == 200
        row = next(i for i in r_sum.json()["items"] if i["company_employeeId"] == emp_id)
        assert row["ot15Minutes"] == 60
        assert row["ot20Minutes"] == 480
        assert row["ot30Minutes"] == 60
        assert row["leaveHours"] == 2.0
        assert row["weightedOtHours"] > 0


async def test_enrollment_quality_gate_pose_angles():
    # High-contrast textured synthetic image so brightness & sharpness pass
    rng = np.random.default_rng(42)
    img = rng.integers(60, 200, size=(300, 300, 3), dtype=np.uint8)
    bbox = [50, 50, 250, 250]
    # Extreme yaw landmarks (nose shifted far right)
    angled_kps = np.array(
        [[110, 120], [170, 120], [210, 150], [120, 190], [165, 190]],
        dtype=np.float32,
    )
    ok_front, msg_front, scores_front = check_enrollment_quality_bgr(img, bbox, angled_kps, angle="FRONT")
    assert ok_front is False
    assert "yaw" in msg_front.lower()
    assert "pitchDeg" in scores_front

    ok_right, _, scores_right = check_enrollment_quality_bgr(img, bbox, angled_kps, angle="RIGHT")
    assert ok_right is True
    assert "yawDeg" in scores_right
