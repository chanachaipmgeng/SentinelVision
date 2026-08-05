"""Excel template + bulk import for company employees."""
from __future__ import annotations

import io
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, UploadFile, status
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..models.company import Company
from ..models.company_employee import CompanyRoleType, EmpType
from ..models.department import Department
from ..models.position import Position
from ..schemas.company_employee_schema import (
    CompanyEmployeePost,
    DepartmentInput,
    MemberInput,
    PositionInput,
)
from .company_employee_controller import register_member

# Header keys used in row 1 of the Employees sheet (Thai labels for HR users).
HEADERS = [
    "อีเมล*",
    "ชื่อ*",
    "นามสกุล*",
    "แผนก*",
    "ตำแหน่ง*",
    "ประเภท*",
    "รหัสพนักงาน",
    "วันเริ่มงาน",
    "วันเกิด",
    "ที่อยู่",
    "ผู้ติดต่อฉุกเฉิน",
    "เบอร์ติดต่อฉุกเฉิน",
    "เบอร์โทร",
    "อีเมลหัวหน้างาน",
    "เงินเดือน",
    "สิทธิ์การใช้งาน",
]

HEADER_INDEX = {h: i for i, h in enumerate(HEADERS)}

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _norm(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.isoformat()
    return str(value).strip()


def _parse_date(value: Any) -> Optional[date]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = _norm(value)
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    raise ValueError(f"รูปแบบวันเกิดไม่ถูกต้อง: {text} (ใช้ YYYY-MM-DD)")


def _parse_datetime(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    text = _norm(value)
    if not text:
        return None
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
    ):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"รูปแบบวันเริ่มงานไม่ถูกต้อง: {text} (ใช้ YYYY-MM-DD)")


def _parse_emp_type(value: Any) -> EmpType:
    text = _norm(value).lower()
    if text in ("", "1", "รายเดือน", "permonth", "month", "monthly"):
        return EmpType.PERMONTH
    if text in ("0", "รายวัน", "perday", "day", "daily"):
        return EmpType.PERDAY
    raise ValueError("ประเภทต้องเป็น รายวัน หรือ รายเดือน")


def _parse_role(value: Any) -> CompanyRoleType:
    text = _norm(value).lower()
    if text in ("", "0", "พนักงาน", "emp", "employee"):
        return CompanyRoleType.EMP
    if text in ("1", "ผู้ดูแลบริษัท", "ผู้ดูแล", "admin", "admin_company"):
        return CompanyRoleType.ADMIN_COMPANY
    raise ValueError("สิทธิ์การใช้งานต้องเป็น พนักงาน หรือ ผู้ดูแลบริษัท")


def _parse_salary(value: Any) -> float:
    if value is None or _norm(value) == "":
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"เงินเดือนไม่ถูกต้อง: {value}")


def _lookup_by_name(items: List[Any], name: str) -> Optional[Any]:
    key = name.strip().lower()
    if not key:
        return None
    for item in items:
        th = (getattr(item, "thName", None) or "").strip().lower()
        eng = (getattr(item, "engName", None) or "").strip().lower()
        if key == th or key == eng:
            return item
    return None


async def _load_org_lookups(companyId: str, db: AsyncSession) -> Tuple[List[Department], List[Position]]:
    dept_result = await db.execute(select(Department).where(Department.companyId == companyId))
    pos_result = await db.execute(select(Position).where(Position.companyId == companyId))
    return list(dept_result.scalars().all()), list(pos_result.scalars().all())


async def build_employee_import_template(companyId: str, db: AsyncSession) -> bytes:
    company = await db.get(Company, companyId)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    departments, positions = await _load_org_lookups(companyId, db)

    wb = Workbook()
    ws = wb.active
    ws.title = "Employees"

    header_fill = PatternFill("solid", fgColor="1F4E79")
    header_font = Font(color="FFFFFF", bold=True)
    required_fill = PatternFill("solid", fgColor="FFF2CC")

    for col, header in enumerate(HEADERS, start=1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", wrap_text=True)
        if header.endswith("*"):
            cell.fill = PatternFill("solid", fgColor="C65911")

    # Sample row (optional — clear before production upload)
    sample_dept = departments[0].thName if departments else "ชื่อแผนก"
    sample_pos = positions[0].thName if positions else "ชื่อตำแหน่ง"
    sample = [
        "name@company.com",
        "สมชาย",
        "ใจดี",
        sample_dept,
        sample_pos,
        "รายเดือน",
        "EMP001",
        datetime.utcnow().strftime("%Y-%m-%d"),
        "1990-01-15",
        "",
        "",
        "",
        "",
        "",
        "0",
        "พนักงาน",
    ]
    for col, value in enumerate(sample, start=1):
        cell = ws.cell(row=2, column=col, value=value)
        if HEADERS[col - 1].endswith("*"):
            cell.fill = required_fill

    for col in range(1, len(HEADERS) + 1):
        ws.column_dimensions[get_column_letter(col)].width = 18
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["J"].width = 30

    emp_type_dv = DataValidation(
        type="list",
        formula1='"รายวัน,รายเดือน"',
        allow_blank=True,
    )
    role_dv = DataValidation(
        type="list",
        formula1='"พนักงาน,ผู้ดูแลบริษัท"',
        allow_blank=True,
    )
    ws.add_data_validation(emp_type_dv)
    ws.add_data_validation(role_dv)
    emp_type_dv.add("F2:F5000")
    role_dv.add("P2:P5000")

    # Reference sheet
    ref = wb.create_sheet("Reference")
    ref["A1"] = "แผนกในบริษัท (ใช้ชื่อในคอลัมน์ แผนก*)"
    ref["A1"].font = Font(bold=True)
    ref["B1"] = "ตำแหน่งในบริษัท (ใช้ชื่อในคอลัมน์ ตำแหน่ง*)"
    ref["B1"].font = Font(bold=True)
    for i, d in enumerate(departments, start=2):
        ref.cell(row=i, column=1, value=d.thName)
    for i, p in enumerate(positions, start=2):
        ref.cell(row=i, column=2, value=p.thName)

    guide = wb.create_sheet("คู่มือ")
    lines = [
        "วิธีใช้เทมเพลตนำเข้าพนักงาน",
        "1) กรอกข้อมูลในชีต Employees ตั้งแต่แถวที่ 2 (ลบแถวตัวอย่างได้)",
        "2) คอลัมน์ที่มี * จำเป็นต้องกรอก",
        "3) แผนก* และ ตำแหน่ง* ต้องตรงกับชื่อในชีต Reference",
        "4) ประเภท*: รายวัน หรือ รายเดือน",
        "5) สิทธิ์การใช้งาน: พนักงาน หรือ ผู้ดูแลบริษัท (ว่าง = พนักงาน)",
        "6) วันเกิด / วันเริ่มงาน: รูปแบบ YYYY-MM-DD",
        "7) อีเมลหัวหน้างาน: ใส่อีเมลพนักงานที่มีอยู่แล้วในบริษัท (ถ้ามี)",
        "8) บัญชีใหม่จะได้รหัสผ่านเริ่มต้น 1234",
        "9) อีเมลที่ซ้ำในบริษัทเดียวกันจะข้ามและรายงานเป็น error",
        "10) บันทึกเป็น .xlsx แล้วอัปโหลดผ่านปุ่มนำเข้า Excel",
    ]
    for i, line in enumerate(lines, start=1):
        guide.cell(row=i, column=1, value=line)
    guide.column_dimensions["A"].width = 90

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


async def import_employees_from_excel(
    companyId: str,
    file: UploadFile,
    db: AsyncSession,
) -> Dict[str, Any]:
    company = await db.get(Company, companyId)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    filename = (file.filename or "").lower()
    if not filename.endswith((".xlsx", ".xlsm")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="กรุณาอัปโหลดไฟล์ Excel (.xlsx)",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ไฟล์ว่าง")

    try:
        wb = load_workbook(io.BytesIO(content), data_only=True)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="อ่านไฟล์ Excel ไม่ได้ กรุณาใช้เทมเพลตที่ดาวน์โหลดจากระบบ",
        )

    if "Employees" in wb.sheetnames:
        ws = wb["Employees"]
    else:
        ws = wb.active

    header_row = [_norm(c.value) for c in next(ws.iter_rows(min_row=1, max_row=1))]
    # Allow missing optional trailing columns; require core headers.
    required_headers = ["อีเมล*", "ชื่อ*", "นามสกุล*", "แผนก*", "ตำแหน่ง*", "ประเภท*"]
    missing = [h for h in required_headers if h not in header_row]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="หัวตารางไม่ตรงเทมเพลต ขาดคอลัมน์: " + ", ".join(missing),
        )

    col_map = {name: idx for idx, name in enumerate(header_row) if name}

    def cell(row_values: Tuple[Any, ...], header: str) -> Any:
        idx = col_map.get(header)
        if idx is None or idx >= len(row_values):
            return None
        return row_values[idx]

    departments, positions = await _load_org_lookups(companyId, db)

    # boss email → memberId (existing employees in company)
    from ..models.company_employee import CompanyEmployee
    from ..models.member import Member

    boss_result = await db.execute(
        select(Member.email, Member.memberId)
        .join(CompanyEmployee, CompanyEmployee.memberId == Member.memberId)
        .where(CompanyEmployee.companyId == companyId)
    )
    boss_by_email = {
        (email or "").strip().lower(): str(member_id)
        for email, member_id in boss_result.all()
        if email
    }

    created: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    total_data_rows = 0

    for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if row is None or all(v is None or _norm(v) == "" for v in row):
            continue
        total_data_rows += 1
        email = _norm(cell(row, "อีเมล*")).lower()
        try:
            if not email:
                raise ValueError("กรุณากรอกอีเมล")
            if not _EMAIL_RE.match(email):
                raise ValueError(f'รูปแบบอีเมลไม่ถูกต้อง: "{email}"')

            first_name = _norm(cell(row, "ชื่อ*"))
            last_name = _norm(cell(row, "นามสกุล*"))
            if not first_name:
                raise ValueError("กรุณากรอกชื่อ")
            if not last_name:
                raise ValueError("กรุณากรอกนามสกุล")

            dept_name = _norm(cell(row, "แผนก*"))
            pos_name = _norm(cell(row, "ตำแหน่ง*"))
            department = _lookup_by_name(departments, dept_name)
            position = _lookup_by_name(positions, pos_name)
            if not department:
                raise ValueError(f'ไม่พบแผนก "{dept_name}" ในบริษัทนี้')
            if not position:
                raise ValueError(f'ไม่พบตำแหน่ง "{pos_name}" ในบริษัทนี้')

            emp_type = _parse_emp_type(cell(row, "ประเภท*"))
            role = _parse_role(cell(row, "สิทธิ์การใช้งาน"))
            salary = _parse_salary(cell(row, "เงินเดือน"))
            birth_date = _parse_date(cell(row, "วันเกิด"))
            start_date = _parse_datetime(cell(row, "วันเริ่มงาน"))

            boss_email = _norm(cell(row, "อีเมลหัวหน้างาน")).lower()
            boss_id = None
            if boss_email:
                boss_id = boss_by_email.get(boss_email)
                if not boss_id:
                    raise ValueError(f'ไม่พบอีเมลหัวหน้างาน "{boss_email}" ในบริษัทนี้')

            payload = CompanyEmployeePost(
                member=MemberInput(
                    email=email,
                    firstName=first_name,
                    lastName=last_name,
                    phoneNumber=_norm(cell(row, "เบอร์โทร")) or None,
                    birthDate=birth_date,
                    address=_norm(cell(row, "ที่อยู่")) or None,
                    emergencyContactName=_norm(cell(row, "ผู้ติดต่อฉุกเฉิน")) or None,
                    emergencyContactPhone=_norm(cell(row, "เบอร์ติดต่อฉุกเฉิน")) or None,
                ),
                position=PositionInput(
                    positionId=position.positionId,
                    thName=position.thName,
                    engName=position.engName,
                ),
                department=DepartmentInput(
                    departmentId=department.departmentId,
                    thName=department.thName,
                    engName=department.engName,
                ),
                employeeId=_norm(cell(row, "รหัสพนักงาน")) or None,
                salary=salary,
                bossId=boss_id,
                companyRoleType=role,
                empType=emp_type,
                startDate=start_date,
            )

            result = await register_member(payload, companyId, db)
            created.append(
                {
                    "row": row_num,
                    "email": email,
                    "company_employeeId": str(result.get("company_employeeId")),
                    "employeeId": result.get("employeeId") or "",
                }
            )
            # Newly created member can become a boss for later rows
            boss_by_email[email] = str(result["member"]["memberId"])
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
            errors.append({"row": row_num, "email": email, "message": detail})
        except Exception as exc:
            errors.append({"row": row_num, "email": email, "message": str(exc)})

    return {
        "total": total_data_rows,
        "success": len(created),
        "failed": len(errors),
        "created": created,
        "errors": errors,
    }
