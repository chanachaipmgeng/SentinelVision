"""C3 punch state machine + C6 holiday CSV/iCal/Thai-preset import."""
from __future__ import annotations

import os
from datetime import date

import pytest
import pytest_asyncio

from src.controllers.employee_timestamp_controller import (
    _next_auto_punch_type,
    _parse_explicit_punch_type,
)
from src.models.employee_timestamp import TimestampType
from src.services.holiday_service import (
    SOURCE_CSV,
    SOURCE_ICAL,
    SOURCE_THAI_PRESET,
    parse_holiday_csv,
    parse_holiday_ical,
    thai_public_holidays,
)

# ---------------------------------------------------------------------------
# Pure unit tests (no DB)
# ---------------------------------------------------------------------------


def test_auto_state_machine_cycle():
    assert _next_auto_punch_type(None) == TimestampType.CHECK_IN
    assert _next_auto_punch_type(TimestampType.CHECK_IN) == TimestampType.BREAK_OUT
    assert _next_auto_punch_type(TimestampType.BREAK_OUT) == TimestampType.BREAK_IN
    assert _next_auto_punch_type(TimestampType.BREAK_IN) == TimestampType.CHECK_OUT
    assert _next_auto_punch_type(TimestampType.CHECK_OUT) == TimestampType.CHECK_OUT


def test_parse_explicit_punch_aliases():
    assert _parse_explicit_punch_type("AUTO") is None
    assert _parse_explicit_punch_type("in") == TimestampType.CHECK_IN
    assert _parse_explicit_punch_type("BREAK_OUT") == TimestampType.BREAK_OUT
    assert _parse_explicit_punch_type("break-in") == TimestampType.BREAK_IN
    assert _parse_explicit_punch_type("OUT") == TimestampType.CHECK_OUT
    assert _parse_explicit_punch_type("4") == TimestampType.BREAK_OUT
    assert _parse_explicit_punch_type("5") == TimestampType.BREAK_IN


def test_parse_holiday_csv_with_header_and_thai_columns():
    text = "วันที่,ชื่อ\n2026-01-01,วันขึ้นปีใหม่\n2026-04-13,สงกรานต์\n"
    rows = parse_holiday_csv(text)
    assert rows == [
        (date(2026, 1, 1), "วันขึ้นปีใหม่"),
        (date(2026, 4, 13), "สงกรานต์"),
    ]


def test_parse_holiday_csv_without_header():
    text = "2026-12-05,วันพ่อแห่งชาติ\n"
    assert parse_holiday_csv(text) == [(date(2026, 12, 5), "วันพ่อแห่งชาติ")]


def test_parse_holiday_ical_vevents():
    ics = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
DTSTART;VALUE=DATE:20260101
SUMMARY:New Year
END:VEVENT
BEGIN:VEVENT
DTSTART:20260413T000000
SUMMARY:Songkran
END:VEVENT
END:VCALENDAR
"""
    rows = parse_holiday_ical(ics)
    assert (date(2026, 1, 1), "New Year") in rows
    assert (date(2026, 4, 13), "Songkran") in rows


def test_thai_public_holiday_preset_includes_fixed_days():
    rows = dict(thai_public_holidays(2026))
    assert rows[date(2026, 1, 1)] == "วันขึ้นปีใหม่"
    assert rows[date(2026, 4, 13)] == "วันสงกรานต์"
    assert date(2026, 12, 5) in rows


# ---------------------------------------------------------------------------
# DB integration
# ---------------------------------------------------------------------------

if not os.environ.get("DPU_TEST_DB_READY"):
    pytest.skip(
        "No test database: set TEST_DATABASE_URL or `pip install pgserver`",
        allow_module_level=True,
    )

from src.controllers import employee_timestamp_controller as ctl  # noqa: E402
from src.routes import employee_timestamp_routes, hr_routes  # noqa: E402
from tests.support import (  # noqa: E402
    GEOFENCE_LAT,
    GEOFENCE_LON,
    build_app,
    client,
    seed_world,
    teardown_world,
)

pytestmark_db = pytest.mark.asyncio(loop_scope="module")


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def world():
    w = await seed_world()
    w.app = build_app(
        (employee_timestamp_routes.router, "/timestamp"),
        (hr_routes.router, "/hr"),
    )
    yield w
    await teardown_world(w)


@pytest.fixture
def clock(monkeypatch):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    BKK = ZoneInfo("Asia/Bangkok")

    class _FrozenClock:
        def __init__(self, mp):
            self._mp = mp
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

    return _FrozenClock(monkeypatch)


def _punch_body(world, *, punch=None, emp=None):
    body = {
        "company_employeeId": str((emp or world.a.employee_employment).company_employeeId),
        "latitude": GEOFENCE_LAT,
        "longitude": GEOFENCE_LON,
    }
    if punch is not None:
        body["punchType"] = punch
    return body


@pytestmark_db
async def test_auto_punch_advances_in_break_out_break_in_out(world, clock):
    """AUTO: IN → BREAK_OUT → BREAK_IN → OUT, then stays OUT."""
    cid = world.a.company_id
    url = f"/timestamp/company/{cid}"
    emp = world.a.admin_employment
    async with client(world.app) as c:
        clock.set("09:00")
        r1 = await c.post(url, json=_punch_body(world, emp=emp), headers=world.auth("admin_a"))
        assert r1.status_code == 200, r1.text
        assert r1.json()["timestampType"] == TimestampType.CHECK_IN.value

        clock.set("12:00")
        r2 = await c.post(url, json=_punch_body(world, emp=emp), headers=world.auth("admin_a"))
        assert r2.status_code == 200, r2.text
        assert r2.json()["timestampType"] == TimestampType.BREAK_OUT.value
        assert r2.json()["lateMinutes"] == 0 and r2.json()["overtimeMinutes"] == 0

        clock.set("13:00")
        r3 = await c.post(url, json=_punch_body(world, emp=emp), headers=world.auth("admin_a"))
        assert r3.status_code == 200, r3.text
        assert r3.json()["timestampType"] == TimestampType.BREAK_IN.value

        clock.set("18:30")
        r4 = await c.post(url, json=_punch_body(world, emp=emp), headers=world.auth("admin_a"))
        assert r4.status_code == 200, r4.text
        assert r4.json()["timestampType"] == TimestampType.CHECK_OUT.value
        assert r4.json()["overtimeMinutes"] == 30

        clock.set("18:45")
        r5 = await c.post(url, json=_punch_body(world, emp=emp), headers=world.auth("admin_a"))
        assert r5.json()["timestampType"] == TimestampType.CHECK_OUT.value


@pytestmark_db
async def test_explicit_break_punch_types(world, clock):
    cid = world.b.company_id
    url = f"/timestamp/company/{cid}"
    emp = world.b.employee_employment
    async with client(world.app) as c:
        clock.set("10:00")
        out = await c.post(
            url, json=_punch_body(world, punch="BREAK_OUT", emp=emp), headers=world.auth("admin_b")
        )
        assert out.status_code == 200, out.text
        assert out.json()["timestampType"] == TimestampType.BREAK_OUT.value

        clock.set("10:30")
        back = await c.post(
            url, json=_punch_body(world, punch="BREAK_IN", emp=emp), headers=world.auth("admin_b")
        )
        assert back.json()["timestampType"] == TimestampType.BREAK_IN.value


@pytestmark_db
async def test_holiday_csv_import_and_list_filter(world):
    cid = world.a.company_id
    async with client(world.app) as c:
        csv_body = "holidayDate,name\n2026-01-01,New Year\n2026-04-13,Songkran\n"
        imp = await c.post(
            f"/hr/company/{cid}/holidays/import",
            json={"format": "csv", "content": csv_body},
            headers=world.auth("admin_a"),
        )
        assert imp.status_code == 200, imp.text
        body = imp.json()
        assert body["source"] == SOURCE_CSV
        assert body["created"] >= 2

        listed = await c.get(
            f"/hr/company/{cid}/holidays",
            params={"start": "2026-01-01", "end": "2026-01-31"},
            headers=world.auth("admin_a"),
        )
        assert listed.status_code == 200
        dates = {row["holidayDate"] for row in listed.json()}
        assert "2026-01-01" in dates
        assert "2026-04-13" not in dates


@pytestmark_db
async def test_holiday_ical_import(world):
    cid = world.a.company_id
    ics = """BEGIN:VCALENDAR
BEGIN:VEVENT
DTSTART;VALUE=DATE:20261023
SUMMARY:Chulalongkorn Day
END:VEVENT
END:VCALENDAR
"""
    async with client(world.app) as c:
        imp = await c.post(
            f"/hr/company/{cid}/holidays/import",
            json={"format": "ical", "content": ics},
            headers=world.auth("admin_a"),
        )
        assert imp.status_code == 200, imp.text
        assert imp.json()["source"] == SOURCE_ICAL
        assert imp.json()["created"] + imp.json()["updated"] >= 1


@pytestmark_db
async def test_thai_holiday_preset(world):
    cid = world.b.company_id
    async with client(world.app) as c:
        res = await c.post(
            f"/hr/company/{cid}/holidays/thai-preset",
            json={"year": 2026},
            headers=world.auth("admin_b"),
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["year"] == 2026
        assert body["source"] == SOURCE_THAI_PRESET
        assert body["imported"] >= 10

        listed = await c.get(f"/hr/company/{cid}/holidays", headers=world.auth("admin_b"))
        assert any(r["holidayDate"] == "2026-01-01" for r in listed.json())
        assert any(r.get("source") == SOURCE_THAI_PRESET for r in listed.json())
