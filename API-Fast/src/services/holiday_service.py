"""Company holiday queries + CSV / iCal / Thai-preset import (Phase C C6).

C2 metrics should call ``is_company_holiday`` / ``holiday_dates_in_range`` rather than
querying ``CompanyHoliday`` ad hoc.
"""
from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime
from typing import Iterable, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.hr_schedule import CompanyHoliday

SOURCE_MANUAL = "MANUAL"
SOURCE_CSV = "CSV"
SOURCE_ICAL = "ICAL"
SOURCE_THAI_PRESET = "THAI_PRESET"

# Fixed Thai public holidays by (month, day). Buddhist/movable days are listed per Gregorian year below.
_THAI_FIXED: tuple[tuple[int, int, str], ...] = (
    (1, 1, "วันขึ้นปีใหม่"),
    (4, 6, "วันจักรี"),
    (4, 13, "วันสงกรานต์"),
    (4, 14, "วันสงกรานต์"),
    (4, 15, "วันสงกรานต์"),
    (5, 1, "วันแรงงานแห่งชาติ"),
    (5, 4, "วันฉัตรมงคล"),
    (6, 3, "วันเฉลิมพระชนมพรรษาสมเด็จพระราชินี"),
    (7, 28, "วันเฉลิมพระชนมพรรษาพระบาทสมเด็จพระเจ้าอยู่หัว"),
    (8, 12, "วันแม่แห่งชาติ"),
    (10, 13, "วันคล้ายวันสวรรคต ร.๙"),
    (10, 23, "วันปิยมหาราช"),
    (12, 5, "วันพ่อแห่งชาติ / วันชาติ"),
    (12, 10, "วันรัฐธรรมนูญ"),
    (12, 31, "วันสิ้นปี"),
)

# Movable / extra observed Thai holidays keyed by Gregorian year (official-ish presets).
_THAI_EXTRA_BY_YEAR: dict[int, tuple[tuple[int, int, int, str], ...]] = {
    2025: (
        (2, 12, 2025, "วันมาฆบูชา"),
        (5, 5, 2025, "วันฉัตรมงคล (ชดเชย)"),
        (5, 11, 2025, "วันวิสาขบูชา"),
        (6, 2, 2025, "วันเฉลิมพระชนมพรรษาสมเด็จพระราชินี (ชดเชย)"),
        (7, 10, 2025, "วันอาสาฬหบูชา"),
        (7, 11, 2025, "วันเข้าพรรษา"),
    ),
    2026: (
        (3, 3, 2026, "วันมาฆบูชา"),
        (5, 4, 2026, "วันฉัตรมงคล"),
        (5, 31, 2026, "วันวิสาขบูชา"),
        (6, 1, 2026, "วันวิสาขบูชา (ชดเชย)"),
        (7, 29, 2026, "วันอาสาฬหบูชา"),
        (7, 30, 2026, "วันเข้าพรรษา"),
    ),
    2027: (
        (2, 20, 2027, "วันมาฆบูชา"),
        (5, 4, 2027, "วันฉัตรมงคล"),
        (5, 20, 2027, "วันวิสาขบูชา"),
        (7, 18, 2027, "วันอาสาฬหบูชา"),
        (7, 19, 2027, "วันเข้าพรรษา"),
    ),
}


def thai_public_holidays(year: int) -> list[tuple[date, str]]:
    """Return (date, name) pairs for the Thai public-holiday preset for ``year``."""
    out: list[tuple[date, str]] = []
    for month, day, name in _THAI_FIXED:
        out.append((date(year, month, day), name))
    for month, day, y, name in _THAI_EXTRA_BY_YEAR.get(year, ()):
        if y == year:
            out.append((date(y, month, day), name))
    # Deduplicate by date (fixed may collide with extras); keep first name.
    seen: dict[date, str] = {}
    for d, name in out:
        seen.setdefault(d, name)
    return sorted(seen.items(), key=lambda x: x[0])


def parse_holiday_csv(text: str) -> list[tuple[date, str]]:
    """Parse CSV with columns date/holidayDate/วันที่ and name/ชื่อ (header optional)."""
    sample = text.lstrip("\ufeff")
    reader = csv.reader(io.StringIO(sample))
    rows = [r for r in reader if any(str(c).strip() for c in r)]
    if not rows:
        return []

    header = [str(c).strip().lower() for c in rows[0]]
    date_idx, name_idx = 0, 1
    looks_header = any(
        h in ("date", "holidaydate", "holiday_date", "วันที่", "วัน") for h in header
    ) or any(h in ("name", "title", "ชื่อ", "ชื่อวันหยุด") for h in header)
    if looks_header:
        for i, h in enumerate(header):
            if h in ("date", "holidaydate", "holiday_date", "วันที่", "วัน"):
                date_idx = i
            if h in ("name", "title", "ชื่อ", "ชื่อวันหยุด"):
                name_idx = i
        data_rows = rows[1:]
    else:
        data_rows = rows

    parsed: list[tuple[date, str]] = []
    for row in data_rows:
        if len(row) <= max(date_idx, name_idx):
            continue
        raw_date = str(row[date_idx]).strip()
        name = str(row[name_idx]).strip()
        if not raw_date or not name:
            continue
        d = _parse_date_flexible(raw_date)
        if d is None:
            continue
        parsed.append((d, name[:150]))
    return parsed


_ICAL_DATE = re.compile(r"(\d{4})(\d{2})(\d{2})")


def parse_holiday_ical(text: str) -> list[tuple[date, str]]:
    """Minimal VEVENT parser: DTSTART (DATE or DATETIME) + SUMMARY."""
    events: list[tuple[date, str]] = []
    blocks = re.split(r"BEGIN:VEVENT", text, flags=re.IGNORECASE)
    for block in blocks[1:]:
        end = re.search(r"END:VEVENT", block, flags=re.IGNORECASE)
        body = block[: end.start()] if end else block
        dt_m = re.search(
            r"^DTSTART(?:;VALUE=DATE)?(?:;[^:]*)?:([0-9TZz+\-]+)",
            body,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        sum_m = re.search(
            r"^SUMMARY(?:;[^:]*)?:(.+)$",
            body,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        if not dt_m or not sum_m:
            continue
        raw = dt_m.group(1).strip()
        m = _ICAL_DATE.match(raw[:8])
        if not m:
            continue
        d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        name = sum_m.group(1).strip().replace("\\,", ",").replace("\\n", " ")[:150]
        if name:
            events.append((d, name))
    return events


def _parse_date_flexible(raw: str) -> Optional[date]:
    s = raw.strip()[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s if len(s) >= 8 else raw.strip()[:10], fmt).date()
        except ValueError:
            continue
    # bare YYYYMMDD
    if re.fullmatch(r"\d{8}", raw.strip()):
        try:
            return datetime.strptime(raw.strip(), "%Y%m%d").date()
        except ValueError:
            return None
    return None


async def list_active_holidays(
    db: AsyncSession,
    company_id: UUID,
    *,
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> list[CompanyHoliday]:
    """Active (non-deleted) holidays, optionally filtered to an inclusive date range."""
    q = select(CompanyHoliday).where(
        CompanyHoliday.companyId == company_id,
        CompanyHoliday.deletedAt.is_(None),
    )
    if start is not None:
        q = q.where(CompanyHoliday.holidayDate >= start)
    if end is not None:
        q = q.where(CompanyHoliday.holidayDate <= end)
    q = q.order_by(CompanyHoliday.holidayDate.asc())
    return list((await db.execute(q)).scalars().all())


async def holiday_dates_in_range(
    db: AsyncSession,
    company_id: UUID,
    start: date,
    end: date,
) -> set[date]:
    """Set of holiday dates in ``[start, end]`` — intended for C2 metrics."""
    rows = await list_active_holidays(db, company_id, start=start, end=end)
    return {r.holidayDate for r in rows if r.holidayDate is not None}


async def is_company_holiday(db: AsyncSession, company_id: UUID, on: date) -> bool:
    rows = await list_active_holidays(db, company_id, start=on, end=on)
    return len(rows) > 0


async def upsert_holidays(
    db: AsyncSession,
    company_id: UUID,
    items: Iterable[tuple[date, str]],
    *,
    source: str,
) -> dict:
    """Insert or revive holidays by (companyId, holidayDate). Returns created/updated/skipped counts."""
    created = updated = skipped = 0
    for holiday_date, name in items:
        name = (name or "").strip()[:150]
        if not name:
            skipped += 1
            continue
        existing = (
            await db.execute(
                select(CompanyHoliday).where(
                    CompanyHoliday.companyId == company_id,
                    CompanyHoliday.holidayDate == holiday_date,
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            db.add(
                CompanyHoliday(
                    companyId=company_id,
                    holidayDate=holiday_date,
                    name=name,
                    source=source,
                )
            )
            created += 1
            continue
        if existing.deletedAt is not None:
            existing.deletedAt = None
            existing.name = name
            existing.source = source
            updated += 1
            continue
        if existing.name != name or (existing.source or "") != source:
            existing.name = name
            existing.source = source
            updated += 1
        else:
            skipped += 1
    await db.commit()
    return {"created": created, "updated": updated, "skipped": skipped, "source": source}


def serialize_holiday(row: CompanyHoliday) -> dict:
    return {
        "holidayId": str(row.holidayId),
        "companyId": str(row.companyId),
        "holidayDate": row.holidayDate.isoformat() if row.holidayDate else None,
        "name": row.name,
        "source": getattr(row, "source", None) or SOURCE_MANUAL,
        "createdAt": row.createdAt,
    }
