"""C5 payroll export: stream summary (attendance_daily) + punch detail sheets without the 5000 cap."""
from __future__ import annotations

import csv
import io
from datetime import date, datetime, timezone
from typing import Any, AsyncIterator, Iterable, Optional
from uuid import UUID

from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..controllers.employee_timestamp_controller import (
    EXPORT_HEADERS,
    _format_export_rows,
    _timestamp_payload,
    get_bangkok_tz,
)
from ..models.attendance_daily import AttendanceDaily
from ..models.company_employee import CompanyEmployee
from ..models.employee_timestamp import EmployeeTimestamp

SUMMARY_HEADERS = [
    "วันที่",
    "รหัสพนักงาน",
    "ชื่อ-นามสกุล",
    "สถานะ",
    "เข้างานแรก",
    "ออกงานสุดท้าย",
    "นาทีทำงาน",
    "นาทีพัก",
    "นาทีสาย",
    "นาที OT",
]


def _as_bkk_date(dt: datetime) -> date:
    tz = get_bangkok_tz()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz).date()


def _fmt_dt(dt: Optional[datetime]) -> str:
    if not dt:
        return ""
    tz = get_bangkok_tz()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz).strftime("%Y-%m-%d %H:%M:%S")


async def _load_employees(
    db: AsyncSession,
    company_id: UUID,
    emp_ids: Iterable[UUID],
) -> dict[UUID, CompanyEmployee]:
    ids = list({i for i in emp_ids if i})
    if not ids:
        return {}
    rows = (
        await db.execute(
            select(CompanyEmployee)
            .where(CompanyEmployee.company_employeeId.in_(ids))
            .options(
                selectinload(CompanyEmployee.member),
                selectinload(CompanyEmployee.department),
                selectinload(CompanyEmployee.position),
            )
        )
    ).scalars().all()
    return {e.company_employeeId: e for e in rows}


def _emp_label(emp: Optional[CompanyEmployee]) -> tuple[str, str]:
    if not emp:
        return "", ""
    code = emp.employeeId or ""
    member = emp.member
    name = (
        f"{getattr(member, 'firstName', '') or ''} {getattr(member, 'lastName', '') or ''}".strip()
        if member
        else ""
    ) or (getattr(member, "username", "") if member else "")
    return code, name


async def fetch_daily_summary_rows(
    db: AsyncSession,
    company_id: UUID,
    start: Optional[date],
    end: Optional[date],
    company_employee_id: Optional[UUID] = None,
) -> list[list[str]]:
    """Prefer attendance_daily; fall back to synthesizing from punches when empty/unavailable."""
    try:
        q = select(AttendanceDaily).where(AttendanceDaily.companyId == company_id)
        if start:
            q = q.where(AttendanceDaily.workDate >= start)
        if end:
            q = q.where(AttendanceDaily.workDate <= end)
        if company_employee_id:
            q = q.where(AttendanceDaily.employeeId == company_employee_id)
        q = q.order_by(AttendanceDaily.workDate.asc(), AttendanceDaily.employeeId.asc())
        dailies = (await db.execute(q)).scalars().all()
    except Exception:
        dailies = []

    if dailies:
        emps = await _load_employees(db, company_id, (d.employeeId for d in dailies))
        rows: list[list[str]] = []
        for d in dailies:
            code, name = _emp_label(emps.get(d.employeeId))
            rows.append(
                [
                    d.workDate.isoformat() if d.workDate else "",
                    code,
                    name,
                    getattr(d.status, "value", str(d.status or "")),
                    _fmt_dt(d.firstIn),
                    _fmt_dt(d.lastOut),
                    str(int(d.workMinutes or 0)),
                    str(int(d.breakMinutes or 0)),
                    str(int(d.lateMinutes or 0)),
                    str(int(d.otMinutes or 0)),
                ]
            )
        return rows

    return await _synthesize_summary_from_punches(db, company_id, start, end, company_employee_id)


async def _synthesize_summary_from_punches(
    db: AsyncSession,
    company_id: UUID,
    start: Optional[date],
    end: Optional[date],
    company_employee_id: Optional[UUID],
) -> list[list[str]]:
    punches = await iter_punch_payloads(db, company_id, start, end, company_employee_id)
    buckets: dict[tuple[str, str], dict[str, Any]] = {}
    for item in punches:
        emp = item.get("employee") or {}
        emp_key = str(emp.get("company_employeeId") or "")
        ts = item.get("timestamp")
        if not isinstance(ts, datetime):
            continue
        day = _as_bkk_date(ts).isoformat()
        key = (day, emp_key)
        bucket = buckets.setdefault(
            key,
            {
                "code": emp.get("employeeId") or "",
                "name": "",
                "first": ts,
                "last": ts,
                "late": 0,
                "ot": 0,
            },
        )
        member = emp.get("member") or {}
        bucket["name"] = (
            f"{member.get('firstName') or ''} {member.get('lastName') or ''}".strip()
            or member.get("username")
            or bucket["name"]
        )
        if ts < bucket["first"]:
            bucket["first"] = ts
        if ts > bucket["last"]:
            bucket["last"] = ts
        bucket["late"] = max(int(bucket["late"]), int(item.get("lateMinutes") or 0))
        bucket["ot"] = max(int(bucket["ot"]), int(item.get("overtimeMinutes") or 0))

    rows: list[list[str]] = []
    for (day, _), b in sorted(buckets.items()):
        work = 0
        if b["first"] and b["last"] and b["last"] > b["first"]:
            work = int((b["last"] - b["first"]).total_seconds() // 60)
        rows.append(
            [
                day,
                str(b["code"]),
                str(b["name"]),
                "PRESENT",
                _fmt_dt(b["first"]),
                _fmt_dt(b["last"]),
                str(work),
                "0",
                str(b["late"]),
                str(b["ot"]),
            ]
        )
    return rows


async def iter_punch_payloads(
    db: AsyncSession,
    company_id: UUID,
    start: Optional[date],
    end: Optional[date],
    company_employee_id: Optional[UUID] = None,
    *,
    chunk_size: int = 1000,
) -> list[dict]:
    """Load all matching punches in chunks — no hard 5000 ceiling (payroll path)."""
    items: list[dict] = []
    offset = 0
    start_dt = datetime.combine(start, datetime.min.time(), tzinfo=get_bangkok_tz()) if start else None
    end_dt = datetime.combine(end, datetime.max.time().replace(microsecond=0), tzinfo=get_bangkok_tz()) if end else None
    while True:
        q = select(EmployeeTimestamp).where(EmployeeTimestamp.companyId == company_id)
        if start_dt:
            q = q.where(EmployeeTimestamp.timestamp >= start_dt)
        if end_dt:
            q = q.where(EmployeeTimestamp.timestamp <= end_dt)
        if company_employee_id:
            q = q.where(EmployeeTimestamp.company_employeeId == company_employee_id)
        q = (
            q.order_by(EmployeeTimestamp.timestamp.asc())
            .offset(offset)
            .limit(chunk_size)
            .options(
                selectinload(EmployeeTimestamp.company_employee).joinedload(CompanyEmployee.member),
                selectinload(EmployeeTimestamp.company_employee).joinedload(CompanyEmployee.position),
                selectinload(EmployeeTimestamp.company_employee).joinedload(CompanyEmployee.department),
            )
        )
        batch = (await db.execute(q)).scalars().all()
        if not batch:
            break
        items.extend(_timestamp_payload(t) for t in batch)
        if len(batch) < chunk_size:
            break
        offset += chunk_size
    return items


async def build_payroll_csv_bytes(
    db: AsyncSession,
    company_id: UUID,
    start: Optional[date],
    end: Optional[date],
    company_employee_id: Optional[UUID] = None,
) -> bytes:
    summary = await fetch_daily_summary_rows(db, company_id, start, end, company_employee_id)
    punches = await iter_punch_payloads(db, company_id, start, end, company_employee_id)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["# Summary"])
    writer.writerow(SUMMARY_HEADERS)
    for row in summary:
        writer.writerow(row)
    writer.writerow([])
    writer.writerow(["# Punch Detail"])
    writer.writerow(EXPORT_HEADERS)
    for row in _format_export_rows(punches):
        writer.writerow(row)
    return ("\ufeff" + buf.getvalue()).encode("utf-8")


async def iter_payroll_csv_chunks(
    db: AsyncSession,
    company_id: UUID,
    start: Optional[date],
    end: Optional[date],
    company_employee_id: Optional[UUID] = None,
) -> AsyncIterator[bytes]:
    """True streaming CSV: header + summary first, then punch rows in chunks."""
    yield "\ufeff".encode("utf-8")
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["# Summary"])
    writer.writerow(SUMMARY_HEADERS)
    summary = await fetch_daily_summary_rows(db, company_id, start, end, company_employee_id)
    for row in summary:
        writer.writerow(row)
    writer.writerow([])
    writer.writerow(["# Punch Detail"])
    writer.writerow(EXPORT_HEADERS)
    yield buf.getvalue().encode("utf-8")
    buf.seek(0)
    buf.truncate(0)

    punches = await iter_punch_payloads(db, company_id, start, end, company_employee_id)
    batch: list[list[str]] = []
    for row in _format_export_rows(punches):
        batch.append(row)
        if len(batch) >= 200:
            for r in batch:
                writer.writerow(r)
            yield buf.getvalue().encode("utf-8")
            buf.seek(0)
            buf.truncate(0)
            batch.clear()
    if batch:
        for r in batch:
            writer.writerow(r)
        yield buf.getvalue().encode("utf-8")


async def build_payroll_xlsx_bytes(
    db: AsyncSession,
    company_id: UUID,
    start: Optional[date],
    end: Optional[date],
    company_employee_id: Optional[UUID] = None,
) -> bytes:
    summary = await fetch_daily_summary_rows(db, company_id, start, end, company_employee_id)
    punches = await iter_punch_payloads(db, company_id, start, end, company_employee_id)

    wb = Workbook(write_only=True)
    ws_sum = wb.create_sheet("Daily Summary")
    ws_sum.append(SUMMARY_HEADERS)
    for row in summary:
        ws_sum.append(row)

    ws_det = wb.create_sheet("Punch Detail")
    ws_det.append(EXPORT_HEADERS)
    for row in _format_export_rows(punches):
        ws_det.append(row)

    # remove default sheet if present
    if "Sheet" in wb.sheetnames:
        del wb["Sheet"]

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
