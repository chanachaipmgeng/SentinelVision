"""B2: hybrid check-in/out punch logic, shift late/OT metrics and xlsx/csv export.

Pure-function tests cover ``_compute_shift_metrics`` (grace, late, OT, cross-midnight) and the two
export builders. The integration half drives ``POST /timestamp/company/{companyId}`` through the
real router + AuthzMiddleware against PostgreSQL, freezing the controller clock so the AUTO punch
resolution and late/OT numbers are deterministic.
"""
from __future__ import annotations

import csv
import io
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio
from openpyxl import load_workbook

if not os.environ.get("DPU_TEST_DB_READY"):
    pytest.skip(
        "No test database: set TEST_DATABASE_URL or `pip install pgserver`",
        allow_module_level=True,
    )

from src.controllers import employee_timestamp_controller as ctl  # noqa: E402
from src.controllers.employee_timestamp_controller import (  # noqa: E402
    EXPORT_HEADERS,
    _compute_shift_metrics,
    build_timestamps_csv,
    build_timestamps_xlsx,
)
from src.routes import employee_timestamp_routes  # noqa: E402
from tests.support import (  # noqa: E402
    FAR_AWAY_LAT,
    FAR_AWAY_LON,
    GEOFENCE_LAT,
    GEOFENCE_LON,
    build_app,
    client,
    seed_world,
    teardown_world,
)

BKK = ZoneInfo("Asia/Bangkok")
DAY_SHIFT = {"name": "Office", "startTime": "09:00", "endTime": "18:00", "graceMinutes": 15}
NIGHT_SHIFT = {"name": "Night", "startTime": "22:00", "endTime": "06:00", "graceMinutes": 10, "isCrossMidnight": True}


def _at(hhmm: str, *, day: int = 10) -> datetime:
    h, m = (int(x) for x in hhmm.split(":"))
    return datetime(2026, 3, day, h, m, tzinfo=BKK)


# ---------------------------------------------------------------- _compute_shift_metrics (pure)
@pytest.mark.parametrize(
    "when,expected",
    [
        ("08:45", (False, 0)),  # early
        ("09:00", (False, 0)),  # exactly on time
        ("09:15", (False, 0)),  # last minute of grace is still on time
        ("09:16", (True, 16)),  # late is measured from shift start, not from the grace cutoff
        ("10:30", (True, 90)),
    ],
)
def test_check_in_late_and_grace(when, expected):
    is_late, late_min, ot_min, name = _compute_shift_metrics(_at(when), DAY_SHIFT, is_checkout=False)
    assert (is_late, late_min) == expected
    assert ot_min == 0 and name == "Office"


@pytest.mark.parametrize(
    "when,expected_ot",
    [("17:30", 0), ("18:00", 0), ("18:01", 1), ("19:30", 90), ("23:59", 359)],
)
def test_check_out_overtime(when, expected_ot):
    is_late, late_min, ot_min, _ = _compute_shift_metrics(_at(when), DAY_SHIFT, is_checkout=True)
    assert (is_late, late_min) == (False, 0)
    assert ot_min == expected_ot


def test_grace_zero_and_missing_fields_fall_back_to_defaults():
    strict = {"graceMinutes": 0}  # 09:00-18:00 defaults, no grace
    assert _compute_shift_metrics(_at("09:01"), strict, is_checkout=False)[:2] == (True, 1)
    assert _compute_shift_metrics(_at("09:00"), strict, is_checkout=False)[:2] == (False, 0)
    assert _compute_shift_metrics(_at("09:01"), {}, is_checkout=False)[3] == ctl.DEFAULT_SHIFT["name"]


def test_cross_midnight_check_in_before_noon_uses_previous_day_start():
    # Night shift started 22:00 yesterday; clocking in at 00:30 is 150 minutes late.
    is_late, late_min, _, _ = _compute_shift_metrics(_at("00:30"), NIGHT_SHIFT, is_checkout=False)
    assert (is_late, late_min) == (True, 150)
    # Clocking in at 21:50 the same evening is early, not "late since this morning".
    assert _compute_shift_metrics(_at("21:50"), NIGHT_SHIFT, is_checkout=False)[:2] == (False, 0)
    assert _compute_shift_metrics(_at("22:10"), NIGHT_SHIFT, is_checkout=False)[:2] == (False, 0)
    assert _compute_shift_metrics(_at("22:11"), NIGHT_SHIFT, is_checkout=False)[:2] == (True, 11)


def test_cross_midnight_check_out_overtime():
    # 06:00 end; leaving 06:45 the next morning is 45 minutes OT.
    assert _compute_shift_metrics(_at("06:45"), NIGHT_SHIFT, is_checkout=True)[2] == 45
    assert _compute_shift_metrics(_at("05:30"), NIGHT_SHIFT, is_checkout=True)[2] == 0
    # Leaving at 23:00 (before midnight) must compare against tomorrow's 06:00, not today's → no OT.
    assert _compute_shift_metrics(_at("23:00"), NIGHT_SHIFT, is_checkout=True)[2] == 0


def test_end_before_start_is_implicitly_cross_midnight():
    implicit = {"startTime": "20:00", "endTime": "04:00", "graceMinutes": 0}
    assert _compute_shift_metrics(_at("01:00"), implicit, is_checkout=False)[:2] == (True, 300)


# ---------------------------------------------------------------- export builders (pure)
def _export_item(**over) -> dict:
    base = {
        "timestamp": datetime(2026, 3, 10, 2, 5, tzinfo=timezone.utc),  # 09:05 Bangkok
        "employee": {
            "employeeId": "EMP-1",
            "member": {"firstName": "สมชาย", "lastName": "ใจดี"},
            "department": {"thName": "บัญชี"},
            "position": {"thName": "พนักงาน"},
        },
        "timestampType": ctl.TimestampType.CHECK_IN,
        "shiftName": "Office",
        "isLate": True,
        "lateMinutes": 5,
        "overtimeMinutes": 0,
        "locationName": "HQ",
        "latitude": 13.75,
        "longitude": 100.5,
        "approvalStatus": "NONE",
        "note": "x, \"quoted\"",
    }
    base.update(over)
    return base


def test_csv_export_has_bom_headers_and_rows():
    raw = build_timestamps_csv([_export_item(), _export_item(note=None, isLate=False, lateMinutes=0)])
    assert raw.startswith("\ufeff".encode("utf-8"))
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"))))
    assert rows[0] == EXPORT_HEADERS
    assert len(rows) == 3
    assert rows[1][2] == "EMP-1"
    assert "สมชาย" in rows[1][3]
    assert rows[1][-1] == 'x, "quoted"'  # csv quoting survives round-trip


def test_xlsx_export_matches_csv_content():
    items = [_export_item(), _export_item(employee={"employeeId": "EMP-2", "member": {"firstName": "B", "lastName": "C"}})]
    wb = load_workbook(io.BytesIO(build_timestamps_xlsx(items)))
    ws = wb.active
    assert ws.title == "Attendance Report"
    header = [c.value for c in ws[1]]
    assert header == EXPORT_HEADERS
    assert ws.max_row == 3
    csv_rows = list(csv.reader(io.StringIO(build_timestamps_csv(items).decode("utf-8-sig"))))
    for r in (2, 3):
        xlsx_row = ["" if c.value is None else str(c.value) for c in ws[r]]
        assert xlsx_row == csv_rows[r - 1]


def test_export_builders_handle_empty():
    assert list(csv.reader(io.StringIO(build_timestamps_csv([]).decode("utf-8-sig")))) == [EXPORT_HEADERS]
    assert load_workbook(io.BytesIO(build_timestamps_xlsx([]))).active.max_row == 1


# ---------------------------------------------------------------- integration: POST /timestamp
pytestmark_db = pytest.mark.asyncio(loop_scope="module")


class _FrozenClock:
    """Swap the controller's ``datetime`` for one whose ``now()`` is pinned (today, Bangkok)."""

    def __init__(self, monkeypatch):
        self._mp = monkeypatch
        self.today = datetime.now(BKK).date()

    def set(self, hhmm: str) -> datetime:
        h, m = (int(x) for x in hhmm.split(":"))
        fixed = datetime(self.today.year, self.today.month, self.today.day, h, m, 0, tzinfo=BKK)

        class _DT(datetime):
            @classmethod
            def now(cls, tz=None):  # type: ignore[override]
                return fixed.astimezone(tz) if tz else fixed.replace(tzinfo=None)

        self._mp.setattr(ctl, "datetime", _DT)
        return fixed


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def world():
    w = await seed_world()
    w.app = build_app((employee_timestamp_routes.router, "/timestamp"))
    yield w
    await teardown_world(w)


@pytest.fixture
def clock(monkeypatch):
    return _FrozenClock(monkeypatch)


def _punch_body(world, *, inside=True, punch=None, note=None, emp=None):
    body = {
        "company_employeeId": str((emp or world.a.employee_employment).company_employeeId),
        "latitude": GEOFENCE_LAT if inside else FAR_AWAY_LAT,
        "longitude": GEOFENCE_LON if inside else FAR_AWAY_LON,
    }
    if punch is not None:
        body["punchType"] = punch
    if note is not None:
        body["note"] = note
    return body


@pytestmark_db
async def test_hybrid_auto_punch_in_then_out_with_late_and_ot(world, clock):
    cid = world.a.company_id
    url = f"/timestamp/company/{cid}"
    async with client(world.app) as c:
        clock.set("09:40")  # default company shift 09:00-18:00 grace 15
        first = await c.post(url, json=_punch_body(world), headers=world.auth("admin_a"))
        assert first.status_code == 200, first.text
        body = first.json()
        assert body["timestampType"] == ctl.TimestampType.CHECK_IN.value
        assert body["approvalStatus"] == "NONE"
        assert body["locationName"] == world.a.location.locationName
        assert body["isLate"] is True and body["lateMinutes"] == 40 and body["overtimeMinutes"] == 0

        clock.set("19:30")
        second = await c.post(url, json=_punch_body(world), headers=world.auth("admin_a"))
        assert second.status_code == 200, second.text
        body = second.json()
        assert body["timestampType"] == ctl.TimestampType.CHECK_OUT.value
        assert body["isLate"] is False and body["lateMinutes"] == 0 and body["overtimeMinutes"] == 90

        # AUTO after any punch today keeps resolving to CHECK_OUT (walk-by kiosks re-punch).
        third = await c.post(url, json=_punch_body(world), headers=world.auth("admin_a"))
        assert third.json()["timestampType"] == ctl.TimestampType.CHECK_OUT.value


@pytestmark_db
async def test_explicit_punch_type_overrides_auto(world, clock):
    cid = world.a.company_id
    url = f"/timestamp/company/{cid}"
    emp = world.a.admin_employment  # separate employee so the AUTO history of the other test is irrelevant
    async with client(world.app) as c:
        clock.set("08:00")
        out_first = await c.post(url, json=_punch_body(world, punch="CHECK_OUT", emp=emp), headers=world.auth("admin_a"))
        assert out_first.status_code == 200, out_first.text
        assert out_first.json()["timestampType"] == ctl.TimestampType.CHECK_OUT.value

        clock.set("12:00")
        in_again = await c.post(url, json=_punch_body(world, punch="in", emp=emp), headers=world.auth("admin_a"))
        assert in_again.json()["timestampType"] == ctl.TimestampType.CHECK_IN.value
        assert in_again.json()["lateMinutes"] == 180


@pytestmark_db
async def test_outside_geofence_requires_note_and_becomes_pending_warning(world, clock):
    cid = world.b.company_id
    url = f"/timestamp/company/{cid}"
    emp = world.b.employee_employment
    clock.set("09:05")
    async with client(world.app) as c:
        no_note = await c.post(url, json=_punch_body(world, inside=False, emp=emp), headers=world.auth("admin_b"))
        assert no_note.status_code == 400
        assert "Note is required" in no_note.json()["detail"]

        with_note = await c.post(
            url, json=_punch_body(world, inside=False, note="ออกพบลูกค้า", emp=emp), headers=world.auth("admin_b")
        )
        assert with_note.status_code == 200, with_note.text
        body = with_note.json()
        assert body["timestampType"] == ctl.TimestampType.WARNING.value
        assert body["approvalStatus"] == "PENDING"
        assert body["locationName"] == "Outside Registered Area"
        assert body["note"] == "ออกพบลูกค้า"


@pytestmark_db
async def test_punch_rejects_missing_or_null_island_gps(world):
    cid = world.a.company_id
    url = f"/timestamp/company/{cid}"
    emp_id = str(world.a.employee_employment.company_employeeId)
    async with client(world.app) as c:
        missing = await c.post(url, json={"company_employeeId": emp_id}, headers=world.auth("admin_a"))
        assert missing.status_code == 400 and "required" in missing.json()["detail"]
        zero = await c.post(
            url, json={"company_employeeId": emp_id, "latitude": 0, "longitude": 0}, headers=world.auth("admin_a")
        )
        assert zero.status_code == 400 and "(0,0)" in zero.json()["detail"]


@pytestmark_db
async def test_punch_for_employee_of_other_company_is_404(world, clock):
    """Tenant A admin posting B's employee id under A's path must not create a row."""
    clock.set("09:00")
    async with client(world.app) as c:
        r = await c.post(
            f"/timestamp/company/{world.a.company_id}",
            json=_punch_body(world, emp=world.b.employee_employment),
            headers=world.auth("admin_a"),
        )
    assert r.status_code == 404


@pytestmark_db
async def test_employee_specific_work_shift_drives_late_calculation(world, clock):
    from src.config.database import async_session
    from src.models.company_employee import CompanyEmployee
    from src.models.hr_schedule import WorkShift

    emp = world.b.admin_employment
    async with async_session() as db:
        ws = WorkShift(companyId=world.b.company_id, name="Early Bird", startTime="07:00", endTime="16:00", graceMinutes=5)
        db.add(ws)
        await db.flush()
        row = await db.get(CompanyEmployee, emp.company_employeeId)
        row.shiftId = ws.shiftId
        await db.commit()
    clock.set("07:20")
    async with client(world.app) as c:
        r = await c.post(
            f"/timestamp/company/{world.b.company_id}",
            json=_punch_body(world, punch="CHECK_IN", emp=emp),
            headers=world.auth("admin_b"),
        )
    assert r.status_code == 200, r.text
    assert r.json()["shiftName"] == "Early Bird"
    assert r.json()["isLate"] is True and r.json()["lateMinutes"] == 20


# ---------------------------------------------------------------- integration: export endpoint
@pytestmark_db
async def test_export_endpoint_csv_and_xlsx_reflect_company_rows_only(world):
    """Runs after the punch tests above: A has 5 rows, B has 2 rows (1 WARNING + 1 CHECK_IN)."""
    async with client(world.app) as c:
        csv_a = await c.get(f"/timestamp/export/company/{world.a.company_id}?format=csv", headers=world.auth("admin_a"))
        xlsx_b = await c.get(f"/timestamp/export/company/{world.b.company_id}", headers=world.auth("admin_b"))
        warn_b = await c.get(
            f"/timestamp/export/company/{world.b.company_id}?format=csv&timestampType=0",
            headers=world.auth("sysadmin"),
        )
    assert csv_a.status_code == 200
    assert csv_a.headers["content-type"].startswith("text/csv")
    assert 'filename="attendance-report.csv"' in csv_a.headers["content-disposition"]
    rows_a = list(csv.reader(io.StringIO(csv_a.content.decode("utf-8-sig"))))
    assert rows_a[0] == EXPORT_HEADERS
    assert len(rows_a) - 1 == 5
    assert {r[2] for r in rows_a[1:]} == {f"EMP-{world.tag}", f"ADM-{world.tag}"}

    assert xlsx_b.status_code == 200
    assert xlsx_b.headers["content-type"].startswith("application/vnd.openxmlformats")
    ws = load_workbook(io.BytesIO(xlsx_b.content)).active
    assert ws.max_row - 1 == 2
    codes = {ws.cell(row=r, column=3).value for r in range(2, ws.max_row + 1)}
    assert codes == {f"EMP-{world.tag}", f"ADM-{world.tag}"}

    rows_warn = list(csv.reader(io.StringIO(warn_b.content.decode("utf-8-sig"))))
    assert len(rows_warn) - 1 == 1
    assert rows_warn[1][-1] == "ออกพบลูกค้า"


@pytestmark_db
async def test_export_bad_filters_are_422(world):
    async with client(world.app) as c:
        bad_type = await c.get(
            f"/timestamp/export/company/{world.a.company_id}?timestampType=abc", headers=world.auth("admin_a")
        )
        bad_date = await c.get(
            f"/timestamp/export/company/{world.a.company_id}?startDate=yesterday", headers=world.auth("admin_a")
        )
    assert bad_type.status_code == 422
    assert bad_date.status_code == 422
