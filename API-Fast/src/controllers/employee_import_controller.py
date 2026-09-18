"""Excel template + bulk import for company employees (optional face photos)."""
from __future__ import annotations

import io
import re
import shutil
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..models.company import Company
from ..models.company_employee import CompanyEmployee, CompanyRoleType, EmpType
from ..models.department import Department
from ..models.face_encoding import FaceEncoding
from ..models.member import Member
from ..models.position import Position
from ..schemas.company_employee_schema import (
    CompanyEmployeePost,
    DepartmentInput,
    MemberInput,
    PositionInput,
)
from ..utils.face_engine import generate_face_encoding
from ..utils.face_gpu_queue import run_on_face_gpu
from ..config.settings import settings
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
    "ไฟล์รูปใบหน้า",
]

PHOTO_HEADERS = ("ไฟล์รูปใบหน้า", "รูปใบหน้า", "รูปพนักงาน", "photo", "facePhoto", "face")

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".bmp")


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
        # Read loaded columns only — expired ORM attrs would lazy-IO and
        # raise greenlet_spawn in this sync helper.
        data = item.__dict__
        th = (data.get("thName") or "").strip().lower()
        eng = (data.get("engName") or "").strip().lower()
        if key == th or key == eng:
            return item
    return None


async def _load_org_lookups(companyId: str, db: AsyncSession) -> Tuple[List[Department], List[Position]]:
    dept_result = await db.execute(select(Department).where(Department.companyId == companyId))
    pos_result = await db.execute(select(Position).where(Position.companyId == companyId))
    return list(dept_result.scalars().all()), list(pos_result.scalars().all())


async def _get_or_create_department(
    companyId: str,
    name: str,
    departments: List[Department],
    db: AsyncSession,
) -> Department:
    found = _lookup_by_name(departments, name)
    if found:
        return found
    new_dept = Department(
        thName=name,
        engName=name,
        companyId=companyId,
    )
    db.add(new_dept)
    await db.commit()
    await db.refresh(new_dept)
    departments.append(new_dept)
    return new_dept


async def _get_or_create_position(
    companyId: str,
    name: str,
    positions: List[Position],
    db: AsyncSession,
) -> Position:
    found = _lookup_by_name(positions, name)
    if found:
        return found
    new_pos = Position(
        thName=name,
        engName=name,
        companyId=companyId,
    )
    db.add(new_pos)
    await db.commit()
    await db.refresh(new_pos)
    positions.append(new_pos)
    return new_pos


def _load_photos_zip(content: bytes) -> Dict[str, bytes]:
    """Map basename (lower) and stem (lower) → image bytes."""
    out: Dict[str, bytes] = {}
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                name = info.filename.replace("\\", "/")
                base = Path(name).name
                if base.startswith("."):
                    continue
                ext = Path(base).suffix.lower()
                if ext not in _IMAGE_EXTS:
                    continue
                data = zf.read(info)
                if not data:
                    continue
                out[base.lower()] = data
                out[Path(base).stem.lower()] = data
                # also key by full relative path basename already covered
    except zipfile.BadZipFile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ไฟล์รูปต้องเป็น ZIP ที่ถูกต้อง",
        )
    return out


def _extract_embedded_images(ws) -> Dict[int, bytes]:
    """Map Excel 1-based row → first image bytes anchored on that row."""
    by_row: Dict[int, bytes] = {}
    for img in getattr(ws, "_images", []) or []:
        try:
            anchor = img.anchor
            row0 = anchor._from.row  # 0-based
            row = int(row0) + 1
            data = img._data()
            if data and row not in by_row:
                by_row[row] = data
        except Exception:
            continue
    return by_row


def _resolve_photo_bytes(
    *,
    row_num: int,
    photo_ref: str,
    email: str,
    employee_id: str,
    zip_photos: Dict[str, bytes],
    embedded: Dict[int, bytes],
) -> Optional[bytes]:
    if row_num in embedded:
        return embedded[row_num]
    if not zip_photos:
        if photo_ref:
            raise ValueError(
                f'ระบุไฟล์รูป "{photo_ref}" แต่ไม่ได้แนบ ZIP รูป (photos.zip)'
            )
        return None

    candidates: List[str] = []
    if photo_ref:
        ref = photo_ref.replace("\\", "/").strip()
        candidates.append(Path(ref).name.lower())
        candidates.append(Path(ref).stem.lower())
        candidates.append(ref.lower())
    if email:
        stem = email.lower()
        candidates.append(stem)
        for ext in _IMAGE_EXTS:
            candidates.append(stem + ext)
    if employee_id:
        stem = employee_id.lower()
        candidates.append(stem)
        for ext in _IMAGE_EXTS:
            candidates.append(stem + ext)

    for key in candidates:
        if key in zip_photos:
            return zip_photos[key]
    if photo_ref:
        raise ValueError(f'ไม่พบรูป "{photo_ref}" ในไฟล์ ZIP')
    return None


async def _recover_import_session(db: AsyncSession) -> None:
    """Clear a failed/expired async session so the next Excel row can continue."""
    try:
        await db.rollback()
    except Exception:
        pass


async def _enroll_face_bytes(member_id: str, image_bytes: bytes, db: AsyncSession) -> str:
    """Save profile picture + InsightFace encoding. Returns faceEncodingId."""
    member = await db.get(Member, UUID(str(member_id)))
    if not member:
        raise ValueError("ไม่พบสมาชิกสำหรับบันทึกใบหน้า")

    temp_dir = Path("temp_images")
    temp_dir.mkdir(exist_ok=True)
    uploaded_dir = Path("uploaded_images")
    uploaded_dir.mkdir(exist_ok=True)
    enrolled_dir = Path("enrolled_images")
    enrolled_dir.mkdir(exist_ok=True)

    temp_path = temp_dir / f"{uuid4()}.jpg"
    profile_name = f"{uuid4()}.jpg"
    profile_path = uploaded_dir / profile_name
    file_moved = False
    encoding_started = False

    try:
        temp_path.write_bytes(image_bytes)
        shutil.copyfile(temp_path, profile_path)

        path = str(temp_path)
        blur_limit = float(settings.IMAGE_BLUR_THRESHOLD_IMPORT)
        encoding_started = True
        encoding = await run_on_face_gpu(
            lambda p=path, b=blur_limit: generate_face_encoding(p, blur_threshold=b)
        )
        if encoding is None:
            raise ValueError("ไม่พบใบหน้าในรูป หรือคุณภาพรูปไม่ผ่านเกณฑ์")

        new_face = FaceEncoding(memberId=member.memberId, embedding=encoding)
        db.add(new_face)
        member.picture = profile_name
        await db.commit()
        await db.refresh(new_face)

        permanent_path = enrolled_dir / f"{new_face.faceEncodingId}.jpg"
        shutil.move(str(temp_path), permanent_path)
        file_moved = True
        return str(new_face.faceEncodingId)
    except ValueError:
        # Do not rollback here: employee row is already committed. Rollback
        # expires cached Department/Position objects and the next Excel rows
        # then fail with greenlet_spawn / await_only().
        if profile_path.exists():
            profile_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        if encoding_started:
            await _recover_import_session(db)
        if profile_path.exists():
            profile_path.unlink(missing_ok=True)
        raise ValueError(f"บันทึกใบหน้าไม่สำเร็จ: {exc}") from exc
    finally:
        if not file_moved and temp_path.exists():
            temp_path.unlink(missing_ok=True)


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
        "EMP001.jpg",
    ]
    for col, value in enumerate(sample, start=1):
        cell = ws.cell(row=2, column=col, value=value)
        if HEADERS[col - 1].endswith("*"):
            cell.fill = required_fill

    for col in range(1, len(HEADERS) + 1):
        ws.column_dimensions[get_column_letter(col)].width = 18
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["J"].width = 30
    ws.column_dimensions["Q"].width = 22

    emp_type_dv = DataValidation(type="list", formula1='"รายวัน,รายเดือน"', allow_blank=True)
    role_dv = DataValidation(type="list", formula1='"พนักงาน,ผู้ดูแลบริษัท"', allow_blank=True)
    ws.add_data_validation(emp_type_dv)
    ws.add_data_validation(role_dv)
    emp_type_dv.add("F2:F5000")
    role_dv.add("P2:P5000")

    ref = wb.create_sheet("Reference")
    ref["A1"] = "แผนกในบริษัท (อ้างอิงได้ หรือใส่ชื่อใหม่ในคอลัมน์ แผนก* ระบบจะสร้างให้)"
    ref["A1"].font = Font(bold=True)
    ref["B1"] = "ตำแหน่งในบริษัท (อ้างอิงได้ หรือใส่ชื่อใหม่ในคอลัมน์ ตำแหน่ง* ระบบจะสร้างให้)"
    ref["B1"].font = Font(bold=True)
    for i, d in enumerate(departments, start=2):
        ref.cell(row=i, column=1, value=d.thName)
    for i, p in enumerate(positions, start=2):
        ref.cell(row=i, column=2, value=p.thName)

    guide = wb.create_sheet("คู่มือ")
    lines = [
        "วิธีใช้เทมเพลตนำเข้าพนักงาน + รูปใบหน้า",
        "1) กรอกข้อมูลในชีต Employees ตั้งแต่แถวที่ 2 (ลบแถวตัวอย่างได้)",
        "2) คอลัมน์ที่มี * จำเป็นต้องกรอก",
        "3) แผนก* และ ตำแหน่ง*: ใช้ชื่อในชีต Reference ได้ หรือใส่ชื่อใหม่ระบบจะสร้างให้อัตโนมัติ",
        "4) ประเภท*: รายวัน หรือ รายเดือน",
        "5) สิทธิ์การใช้งาน: พนักงาน หรือ ผู้ดูแลบริษัท (ว่าง = พนักงาน)",
        "6) วันเกิด / วันเริ่มงาน: รูปแบบ YYYY-MM-DD",
        "7) อีเมลหัวหน้างาน: ใส่อีเมลพนักงานที่มีอยู่แล้วในบริษัท (ถ้ามี)",
        "8) บัญชีใหม่จะได้รหัสผ่านเริ่มต้น 1234",
        "9) อีเมลที่ซ้ำในบริษัทเดียวกันจะข้ามและรายงานเป็น error",
        "10) คอลัมน์ ไฟล์รูปใบหน้า: ใส่ชื่อไฟล์ เช่น EMP001.jpg หรือ name@company.com.jpg",
        "11) อัปโหลด Excel พร้อมไฟล์ ZIP รูป (photos.zip) — ชื่อไฟล์ใน ZIP ต้องตรงคอลัมน์หรือใช้อีเมล/รหัสพนักงาน",
        "12) หรือแทรกรูปฝังในแถวของ Excel (Insert Picture) ระบบจะจับคู่ตามแถว",
        "13) รูปต้องเห็นใบหน้าชัด ระบบจะบันทึกเป็น face encoding สำหรับลงเวลา",
    ]
    for i, line in enumerate(lines, start=1):
        guide.cell(row=i, column=1, value=line)
    guide.column_dimensions["A"].width = 100

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


async def import_employees_from_excel(
    companyId: str,
    file: UploadFile,
    db: AsyncSession,
    photos: Optional[UploadFile] = None,
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

    zip_photos: Dict[str, bytes] = {}
    if photos is not None and photos.filename:
        photo_name = (photos.filename or "").lower()
        photo_bytes = await photos.read()
        if photo_bytes:
            if not photo_name.endswith(".zip"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="ไฟล์รูปต้องเป็น ZIP (.zip) รวมรูป jpg/png",
                )
            zip_photos = _load_photos_zip(photo_bytes)

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

    # Reload without data_only to keep embedded images
    try:
        wb_img = load_workbook(io.BytesIO(content), data_only=False)
        ws_img = wb_img["Employees"] if "Employees" in wb_img.sheetnames else wb_img.active
        embedded = _extract_embedded_images(ws_img)
    except Exception:
        embedded = {}

    header_row = [_norm(c.value) for c in next(ws.iter_rows(min_row=1, max_row=1))]
    required_headers = ["อีเมล*", "ชื่อ*", "นามสกุล*", "แผนก*", "ตำแหน่ง*", "ประเภท*"]
    missing = [h for h in required_headers if h not in header_row]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="หัวตารางไม่ตรงเทมเพลต ขาดคอลัมน์: " + ", ".join(missing),
        )

    col_map = {name: idx for idx, name in enumerate(header_row) if name}
    photo_header = next((h for h in PHOTO_HEADERS if h in col_map), None)

    def cell(row_values: Tuple[Any, ...], header: str) -> Any:
        idx = col_map.get(header)
        if idx is None or idx >= len(row_values):
            return None
        return row_values[idx]

    departments, positions = await _load_org_lookups(companyId, db)

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
    faces_ok = 0

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
            if not dept_name:
                raise ValueError("กรุณากรอกแผนก")
            if not pos_name:
                raise ValueError("กรุณากรอกตำแหน่ง")
            department = await _get_or_create_department(
                companyId, dept_name, departments, db
            )
            position = await _get_or_create_position(
                companyId, pos_name, positions, db
            )

            emp_type = _parse_emp_type(cell(row, "ประเภท*"))
            role = _parse_role(cell(row, "สิทธิ์การใช้งาน"))
            salary = _parse_salary(cell(row, "เงินเดือน"))
            birth_date = _parse_date(cell(row, "วันเกิด"))
            start_date = _parse_datetime(cell(row, "วันเริ่มงาน"))
            employee_code = _norm(cell(row, "รหัสพนักงาน"))

            boss_email = _norm(cell(row, "อีเมลหัวหน้างาน")).lower()
            boss_id = None
            if boss_email:
                boss_id = boss_by_email.get(boss_email)
                if not boss_id:
                    raise ValueError(f'ไม่พบอีเมลหัวหน้างาน "{boss_email}" ในบริษัทนี้')

            photo_ref = _norm(cell(row, photo_header)) if photo_header else ""

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
                employeeId=employee_code or None,
                salary=salary,
                bossId=boss_id,
                companyRoleType=role,
                empType=emp_type,
                startDate=start_date,
            )

            result = await register_member(payload, companyId, db)
            member_id = str(result["member"]["memberId"])
            face_enrolled = False
            face_warning = None
            try:
                photo_bytes = _resolve_photo_bytes(
                    row_num=row_num,
                    photo_ref=photo_ref,
                    email=email,
                    employee_id=employee_code,
                    zip_photos=zip_photos,
                    embedded=embedded,
                )
                if photo_bytes:
                    await _enroll_face_bytes(member_id, photo_bytes, db)
                    face_enrolled = True
                    faces_ok += 1
            except Exception as face_exc:
                face_warning = str(face_exc)
                await _recover_import_session(db)
                departments, positions = await _load_org_lookups(companyId, db)

            created.append(
                {
                    "row": row_num,
                    "email": email,
                    "company_employeeId": str(result.get("company_employeeId")),
                    "employeeId": result.get("employeeId") or "",
                    "faceEnrolled": face_enrolled,
                    "faceWarning": face_warning,
                }
            )
            boss_by_email[email] = member_id
        except HTTPException as exc:
            await _recover_import_session(db)
            departments, positions = await _load_org_lookups(companyId, db)
            detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
            errors.append({"row": row_num, "email": email, "message": detail})
        except Exception as exc:
            await _recover_import_session(db)
            departments, positions = await _load_org_lookups(companyId, db)
            errors.append({"row": row_num, "email": email, "message": str(exc)})

    return {
        "total": total_data_rows,
        "success": len(created),
        "failed": len(errors),
        "facesEnrolled": faces_ok,
        "created": created,
        "errors": errors,
    }
