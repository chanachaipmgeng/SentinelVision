"""
Seed realistic demo data for 2 companies across every DPU table.

Usage:
  docker compose run --rm -v ./API-Fast:/app --entrypoint python api scripts/seed_demo_data.py --reset

Password for all users: Password123!
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

import numpy as np
from passlib.context import CryptContext
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.models.company import Company, PublicType
from src.models.company_employee import CompanyEmployee, CompanyRoleType, EmpType
from src.models.company_location import CompanyLocation, LocationType
from src.models.department import Department
from src.models.employee_timestamp import ApprovalStatus, EmployeeTimestamp, TimestampType
from src.models.face_encoding import FACE_EMBEDDING_DIM, FaceEncoding
from src.models.member import Member, RoleType, StatusType
from src.models.position import Position
from src.utils.schema_migrate import ensure_profile_and_approval_columns

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
DEFAULT_PASSWORD = "Password123!"
DEFAULT_PASSWORD_HASH = (
    "$2b$12$NN5ddv.cffdpVH2NYzTiEOnxmKKRLvVJt7uzh6dfJCLw8FZcaAPa2"
)

# Company A — tech / HQ Bangkok
CO_A = UUID("11111111-1111-1111-1111-111111111111")
# Company B — retail / Chiang Mai + Bangkok branch
CO_B = UUID("11111111-1111-1111-1111-111111111112")

IDS = {
    # Company A structure
    "a_dept_eng": UUID("22222222-2222-2222-2222-222222222201"),
    "a_dept_hr": UUID("22222222-2222-2222-2222-222222222202"),
    "a_dept_ops": UUID("22222222-2222-2222-2222-222222222203"),
    "a_pos_mgr": UUID("33333333-3333-3333-3333-333333333301"),
    "a_pos_dev": UUID("33333333-3333-3333-3333-333333333302"),
    "a_pos_hr": UUID("33333333-3333-3333-3333-333333333303"),
    "a_pos_ops": UUID("33333333-3333-3333-3333-333333333304"),
    "a_loc_hq": UUID("44444444-4444-4444-4444-444444444401"),
    "a_loc_site": UUID("44444444-4444-4444-4444-444444444402"),
    # Company B structure
    "b_dept_store": UUID("22222222-2222-2222-2222-222222222211"),
    "b_dept_wh": UUID("22222222-2222-2222-2222-222222222212"),
    "b_pos_sm": UUID("33333333-3333-3333-3333-333333333311"),
    "b_pos_staff": UUID("33333333-3333-3333-3333-333333333312"),
    "b_pos_wh": UUID("33333333-3333-3333-3333-333333333313"),
    "b_loc_cnx": UUID("44444444-4444-4444-4444-444444444411"),
    "b_loc_bkk": UUID("44444444-4444-4444-4444-444444444412"),
    # Members
    "m_sys": UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1"),
    "m_a_adm": UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2"),
    "m_a_mgr": UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3"),
    "m_a_dev": UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4"),
    "m_a_hr": UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa5"),
    "m_a_ops": UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa6"),
    "m_b_adm": UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaa12"),
    "m_b_mgr": UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaa13"),
    "m_b_st1": UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaa14"),
    "m_b_st2": UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaa15"),
    # Company employees
    "ce_a_adm": UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb2"),
    "ce_a_mgr": UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb3"),
    "ce_a_dev": UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb4"),
    "ce_a_hr": UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb5"),
    "ce_a_ops": UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb6"),
    "ce_b_adm": UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb12"),
    "ce_b_mgr": UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb13"),
    "ce_b_st1": UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb14"),
    "ce_b_st2": UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb15"),
    # Timestamps (A)
    "ts_a_in": UUID("cccccccc-cccc-cccc-cccc-ccccccccccc1"),
    "ts_a_pending": UUID("cccccccc-cccc-cccc-cccc-ccccccccccc2"),
    "ts_a_approved": UUID("cccccccc-cccc-cccc-cccc-ccccccccccc3"),
    "ts_a_rejected": UUID("cccccccc-cccc-cccc-cccc-ccccccccccc4"),
    "ts_a_out": UUID("cccccccc-cccc-cccc-cccc-ccccccccccc5"),
    "ts_a_pending2": UUID("cccccccc-cccc-cccc-cccc-ccccccccccc6"),
    # Timestamps (B)
    "ts_b_in": UUID("cccccccc-cccc-cccc-cccc-cccccccccc11"),
    "ts_b_pending": UUID("cccccccc-cccc-cccc-cccc-cccccccccc12"),
    "ts_b_out": UUID("cccccccc-cccc-cccc-cccc-cccccccccc13"),
    "ts_b_approved": UUID("cccccccc-cccc-cccc-cccc-cccccccccc14"),
}

# Geo
BKK_HQ = (13.7563, 100.5018)
BKK_OUT = (13.8200, 100.5600)
BKK_SITE = (13.7308, 100.5418)
CNX_STORE = (18.7883, 98.9853)
CNX_OUT = (18.8200, 99.0100)


def _hash(password: str) -> str:
    if password == DEFAULT_PASSWORD:
        return DEFAULT_PASSWORD_HASH
    return pwd_context.hash(password)


def _unit_embedding(seed: int) -> list[float]:
    rng = np.random.default_rng(seed)
    vec = rng.standard_normal(FACE_EMBEDDING_DIM).astype(np.float32)
    vec /= np.linalg.norm(vec) + 1e-12
    return vec.tolist()


def _dt(days: int = 0, hours: int = 0, minutes: int = 0) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days, hours=hours, minutes=minutes)


async def reset_all(session: AsyncSession) -> None:
    await session.execute(delete(EmployeeTimestamp))
    await session.execute(delete(FaceEncoding))
    await session.execute(delete(CompanyEmployee))
    await session.execute(delete(CompanyLocation))
    await session.execute(delete(Department))
    await session.execute(delete(Position))
    await session.execute(delete(Company))
    await session.execute(delete(Member))
    await session.commit()
    print("Reset: truncated all demo tables")


async def seed(session: AsyncSession) -> None:
    existing = (
        await session.execute(select(Company).where(Company.companyId == CO_A))
    ).scalar_one_or_none()
    if existing:
        print("Seed already present (company A). Use --reset to recreate.")
        return

    pw = _hash(DEFAULT_PASSWORD)
    now = datetime.now(timezone.utc)

    # ---- Members ----
    members = [
        Member(
            memberId=IDS["m_sys"],
            username="sysadmin",
            passwordHash=pw,
            firstName="กิตติ",
            lastName="ระบบ",
            email="sysadmin@example.com",
            phoneNumber="0801110001",
            role=RoleType.ADMIN_SYSTEM,
            status=StatusType.ENABLE,
            birthDate=date(1982, 4, 12),
            address="99 ถ.พระราม 4 แขวงคลองเตย เขตคลองเตย กรุงเทพฯ 10110",
            emergencyContactName="ศูนย์ IT",
            emergencyContactPhone="021111111",
        ),
        # Company A
        Member(
            memberId=IDS["m_a_adm"],
            username="admin",
            passwordHash=pw,
            firstName="อรุณี",
            lastName="ใจดี",
            email="admin@dpuattendance.example.com",
            phoneNumber="0812223344",
            role=RoleType.ADMIN_COMPANY,
            status=StatusType.ENABLE,
            birthDate=date(1988, 7, 21),
            address="88/12 ซอยสุขุมวิท 39 เขตวัฒนา กรุงเทพฯ 10110",
            emergencyContactName="สมชาย ใจดี",
            emergencyContactPhone="0891112233",
        ),
        Member(
            memberId=IDS["m_a_mgr"],
            username="boss",
            passwordHash=pw,
            firstName="สมชาย",
            lastName="มั่นคง",
            email="somchai.m@dpuattendance.example.com",
            phoneNumber="0813334455",
            role=RoleType.MEMBER,
            status=StatusType.ENABLE,
            birthDate=date(1985, 1, 30),
            address="15 ถ.สาทรใต้ เขตสาทร กรุงเทพฯ 10120",
            emergencyContactName="วิภา มั่นคง",
            emergencyContactPhone="0892223344",
        ),
        Member(
            memberId=IDS["m_a_dev"],
            username="emp1",
            passwordHash=pw,
            firstName="ณัฐพงศ์",
            lastName="โค้ดดี",
            email="nattapong.c@dpuattendance.example.com",
            phoneNumber="0814445566",
            role=RoleType.MEMBER,
            status=StatusType.ENABLE,
            birthDate=date(1995, 8, 8),
            address="42 ซอยลาดพร้าว 101 เขตวังทองหลาง กรุงเทพฯ 10310",
            emergencyContactName="แม่",
            emergencyContactPhone="0823334455",
            attachmentUrls="idcard-dev001.pdf,contract-dev001.pdf",
        ),
        Member(
            memberId=IDS["m_a_hr"],
            username="emp2",
            passwordHash=pw,
            firstName="ศิริวรรณ",
            lastName="บุญช่วย",
            email="siriwan.b@dpuattendance.example.com",
            phoneNumber="0815556677",
            role=RoleType.MEMBER,
            status=StatusType.ENABLE,
            birthDate=date(1993, 11, 2),
            address="7/5 ถ.เพชรบุรีตัดใหม่ เขตราชเทวี กรุงเทพฯ 10400",
            emergencyContactName="พี่ชาย",
            emergencyContactPhone="0834445566",
        ),
        Member(
            memberId=IDS["m_a_ops"],
            username="emp3",
            passwordHash=pw,
            firstName="วรพล",
            lastName="ปฏิบัติ",
            email="worapol.p@dpuattendance.example.com",
            phoneNumber="0816667788",
            role=RoleType.MEMBER,
            status=StatusType.ENABLE,
            birthDate=date(1991, 3, 15),
            address="120 ถ.รัชดาภิเษก เขตห้วยขวาง กรุงเทพฯ 10310",
            emergencyContactName="ภรรยา",
            emergencyContactPhone="0845556677",
        ),
        # Company B
        Member(
            memberId=IDS["m_b_adm"],
            username="admin_b",
            passwordHash=pw,
            firstName="มัลลิกา",
            lastName="รุ่งเรือง",
            email="admin@siamretail.example.com",
            phoneNumber="0821112233",
            role=RoleType.ADMIN_COMPANY,
            status=StatusType.ENABLE,
            birthDate=date(1987, 9, 9),
            address="55 ถ.ห้วยแก้ว อ.เมือง จ.เชียงใหม่ 50200",
            emergencyContactName="ฝ่ายบุคคล สยามรีเทล",
            emergencyContactPhone="053111222",
        ),
        Member(
            memberId=IDS["m_b_mgr"],
            username="boss_b",
            passwordHash=pw,
            firstName="ธนา",
            lastName="สาขา",
            email="thana.s@siamretail.example.com",
            phoneNumber="0822223344",
            role=RoleType.MEMBER,
            status=StatusType.ENABLE,
            birthDate=date(1984, 6, 18),
            address="12 ถ.นิมมานเหมินทร์ อ.เมือง จ.เชียงใหม่ 50200",
            emergencyContactName="ภรรยา",
            emergencyContactPhone="0896667788",
        ),
        Member(
            memberId=IDS["m_b_st1"],
            username="staff1",
            passwordHash=pw,
            firstName="พิมพ์ใจ",
            lastName="ขายดี",
            email="pimjai.k@siamretail.example.com",
            phoneNumber="0823334455",
            role=RoleType.MEMBER,
            status=StatusType.ENABLE,
            birthDate=date(1998, 2, 14),
            address="8 ซอยวัดเกต อ.เมือง จ.เชียงใหม่ 50000",
            emergencyContactName="แม่",
            emergencyContactPhone="0867778899",
        ),
        Member(
            memberId=IDS["m_b_st2"],
            username="staff2",
            passwordHash=pw,
            firstName="อนุชา",
            lastName="คลังสินค้า",
            email="anucha.w@siamretail.example.com",
            phoneNumber="0824445566",
            role=RoleType.MEMBER,
            status=StatusType.ENABLE,
            birthDate=date(1996, 12, 5),
            address="33 ถ.ช้างคลาน อ.เมือง จ.เชียงใหม่ 50100",
            emergencyContactName="พ่อ",
            emergencyContactPhone="0878889900",
        ),
    ]
    session.add_all(members)

    # ---- Companies ----
    session.add_all(
        [
            Company(
                companyId=CO_A,
                companyName="บริษัท ดีพียู แอทเทนแดนซ์ จำกัด",
                companyCode="DPUATT",
                companyInfo="ระบบลงเวลาและจดจำใบหน้าสำหรับองค์กร — สำนักงานใหญ่กรุงเทพฯ",
                picture="",
                address="99 อาคารเอ็มไพร์ ถ.สาทรใต้ เขตสาทร กรุงเทพฯ 10120",
                latitude=BKK_HQ[0],
                longitude=BKK_HQ[1],
                status=PublicType.PUBLIC,
                ownerName="คุณอรุณี ใจดี",
                contact="02-123-4567",
            ),
            Company(
                companyId=CO_B,
                companyName="บริษัท สยาม รีเทล กรุ๊ป จำกัด",
                companyCode="SIAMRG",
                companyInfo="เครือข่ายร้านค้าปลีกและคลังสินค้า ภาคเหนือและกรุงเทพฯ",
                picture="",
                address="55 ถ.ห้วยแก้ว อ.เมือง จ.เชียงใหม่ 50200",
                latitude=CNX_STORE[0],
                longitude=CNX_STORE[1],
                status=PublicType.PUBLIC,
                ownerName="คุณมัลลิกา รุ่งเรือง",
                contact="053-111-222",
            ),
        ]
    )

    # ---- Depts / Positions / Locations ----
    session.add_all(
        [
            Department(departmentId=IDS["a_dept_eng"], thName="วิศวกรรมซอฟต์แวร์", engName="Software Engineering", companyId=CO_A),
            Department(departmentId=IDS["a_dept_hr"], thName="ทรัพยากรบุคคล", engName="Human Resources", companyId=CO_A),
            Department(departmentId=IDS["a_dept_ops"], thName="ปฏิบัติการ", engName="Operations", companyId=CO_A),
            Position(positionId=IDS["a_pos_mgr"], thName="ผู้จัดการฝ่าย", engName="Department Manager", companyId=CO_A),
            Position(positionId=IDS["a_pos_dev"], thName="วิศวกรซอฟต์แวร์", engName="Software Engineer", companyId=CO_A),
            Position(positionId=IDS["a_pos_hr"], thName="เจ้าหน้าที่ HR", engName="HR Officer", companyId=CO_A),
            Position(positionId=IDS["a_pos_ops"], thName="เจ้าหน้าที่ปฏิบัติการ", engName="Operations Officer", companyId=CO_A),
            CompanyLocation(
                locationId=IDS["a_loc_hq"], companyId=CO_A,
                latitude=BKK_HQ[0], longitude=BKK_HQ[1],
                locationName="สำนักงานใหญ่ สาทร", radius=0.4,
                locationType=LocationType.PERMANENT,
                startDate=now - timedelta(days=900), endDate=now + timedelta(days=3650),
            ),
            CompanyLocation(
                locationId=IDS["a_loc_site"], companyId=CO_A,
                latitude=BKK_SITE[0], longitude=BKK_SITE[1],
                locationName="ไซต์ลูกค้า อโศก (ชั่วคราว)", radius=0.25,
                locationType=LocationType.TEMPORARY,
                startDate=now - timedelta(days=14), endDate=now + timedelta(days=45),
            ),
            Department(departmentId=IDS["b_dept_store"], thName="หน้าร้าน", engName="Store Front", companyId=CO_B),
            Department(departmentId=IDS["b_dept_wh"], thName="คลังสินค้า", engName="Warehouse", companyId=CO_B),
            Position(positionId=IDS["b_pos_sm"], thName="ผู้จัดการร้าน", engName="Store Manager", companyId=CO_B),
            Position(positionId=IDS["b_pos_staff"], thName="พนักงานขาย", engName="Sales Associate", companyId=CO_B),
            Position(positionId=IDS["b_pos_wh"], thName="พนักงานคลัง", engName="Warehouse Staff", companyId=CO_B),
            CompanyLocation(
                locationId=IDS["b_loc_cnx"], companyId=CO_B,
                latitude=CNX_STORE[0], longitude=CNX_STORE[1],
                locationName="สาขาเชียงใหม่ ห้วยแก้ว", radius=0.35,
                locationType=LocationType.PERMANENT,
                startDate=now - timedelta(days=600), endDate=now + timedelta(days=3650),
            ),
            CompanyLocation(
                locationId=IDS["b_loc_bkk"], companyId=CO_B,
                latitude=13.7460, longitude=100.5340,
                locationName="สาขากรุงเทพ สยาม", radius=0.3,
                locationType=LocationType.PERMANENT,
                startDate=now - timedelta(days=200), endDate=now + timedelta(days=3650),
            ),
        ]
    )

    # ---- Company employees ----
    session.add_all(
        [
            CompanyEmployee(
                company_employeeId=IDS["ce_a_adm"], memberId=IDS["m_a_adm"], companyId=CO_A,
                positionId=IDS["a_pos_hr"], departmentId=IDS["a_dept_hr"],
                employeeId="DPU-ADM-001", startDate=_dt(days=850),
                empType=EmpType.PERMONTH, companyRoleType=CompanyRoleType.ADMIN_COMPANY,
                salary=58000, bossId="",
            ),
            CompanyEmployee(
                company_employeeId=IDS["ce_a_mgr"], memberId=IDS["m_a_mgr"], companyId=CO_A,
                positionId=IDS["a_pos_mgr"], departmentId=IDS["a_dept_eng"],
                employeeId="DPU-MGR-001", startDate=_dt(days=700),
                empType=EmpType.PERMONTH, companyRoleType=CompanyRoleType.EMP,
                salary=72000, bossId=str(IDS["m_a_adm"]),
            ),
            CompanyEmployee(
                company_employeeId=IDS["ce_a_dev"], memberId=IDS["m_a_dev"], companyId=CO_A,
                positionId=IDS["a_pos_dev"], departmentId=IDS["a_dept_eng"],
                employeeId="DPU-DEV-001", startDate=_dt(days=220),
                empType=EmpType.PERMONTH, companyRoleType=CompanyRoleType.EMP,
                salary=45000, bossId=str(IDS["m_a_mgr"]),
            ),
            CompanyEmployee(
                company_employeeId=IDS["ce_a_hr"], memberId=IDS["m_a_hr"], companyId=CO_A,
                positionId=IDS["a_pos_hr"], departmentId=IDS["a_dept_hr"],
                employeeId="DPU-HR-001", startDate=_dt(days=180),
                empType=EmpType.PERMONTH, companyRoleType=CompanyRoleType.EMP,
                salary=32000, bossId=str(IDS["m_a_adm"]),
            ),
            CompanyEmployee(
                company_employeeId=IDS["ce_a_ops"], memberId=IDS["m_a_ops"], companyId=CO_A,
                positionId=IDS["a_pos_ops"], departmentId=IDS["a_dept_ops"],
                employeeId="DPU-OPS-001", startDate=_dt(days=90),
                empType=EmpType.PERDAY, companyRoleType=CompanyRoleType.EMP,
                salary=900, bossId=str(IDS["m_a_mgr"]),
            ),
            CompanyEmployee(
                company_employeeId=IDS["ce_b_adm"], memberId=IDS["m_b_adm"], companyId=CO_B,
                positionId=IDS["b_pos_sm"], departmentId=IDS["b_dept_store"],
                employeeId="SRG-ADM-001", startDate=_dt(days=500),
                empType=EmpType.PERMONTH, companyRoleType=CompanyRoleType.ADMIN_COMPANY,
                salary=48000, bossId="",
            ),
            CompanyEmployee(
                company_employeeId=IDS["ce_b_mgr"], memberId=IDS["m_b_mgr"], companyId=CO_B,
                positionId=IDS["b_pos_sm"], departmentId=IDS["b_dept_store"],
                employeeId="SRG-SM-001", startDate=_dt(days=400),
                empType=EmpType.PERMONTH, companyRoleType=CompanyRoleType.EMP,
                salary=38000, bossId=str(IDS["m_b_adm"]),
            ),
            CompanyEmployee(
                company_employeeId=IDS["ce_b_st1"], memberId=IDS["m_b_st1"], companyId=CO_B,
                positionId=IDS["b_pos_staff"], departmentId=IDS["b_dept_store"],
                employeeId="SRG-SA-001", startDate=_dt(days=120),
                empType=EmpType.PERDAY, companyRoleType=CompanyRoleType.EMP,
                salary=550, bossId=str(IDS["m_b_mgr"]),
            ),
            CompanyEmployee(
                company_employeeId=IDS["ce_b_st2"], memberId=IDS["m_b_st2"], companyId=CO_B,
                positionId=IDS["b_pos_wh"], departmentId=IDS["b_dept_wh"],
                employeeId="SRG-WH-001", startDate=_dt(days=95),
                empType=EmpType.PERDAY, companyRoleType=CompanyRoleType.EMP,
                salary=600, bossId=str(IDS["m_b_mgr"]),
            ),
        ]
    )

    # ---- Timestamps (realistic mix) ----
    session.add_all(
        [
            # A: normal check-in / check-out today
            EmployeeTimestamp(
                timestampId=IDS["ts_a_in"], company_employeeId=IDS["ce_a_dev"], companyId=CO_A,
                timestamp=_dt(hours=8, minutes=5), timestampType=TimestampType.CHECK_IN,
                locationName="สำนักงานใหญ่ สาทร", latitude=BKK_HQ[0], longitude=BKK_HQ[1],
                photoTimestamp="", note=None, approvalStatus=ApprovalStatus.NONE.value,
            ),
            EmployeeTimestamp(
                timestampId=IDS["ts_a_out"], company_employeeId=IDS["ce_a_dev"], companyId=CO_A,
                timestamp=_dt(hours=1, minutes=10), timestampType=TimestampType.CHECK_OUT,
                locationName="สำนักงานใหญ่ สาทร", latitude=BKK_HQ[0], longitude=BKK_HQ[1],
                photoTimestamp="", note=None, approvalStatus=ApprovalStatus.NONE.value,
            ),
            # A: pending outside area (primary smoke-test row)
            EmployeeTimestamp(
                timestampId=IDS["ts_a_pending"], company_employeeId=IDS["ce_a_hr"], companyId=CO_A,
                timestamp=_dt(hours=3, minutes=20), timestampType=TimestampType.WARNING,
                locationName="Outside Registered Area", latitude=BKK_OUT[0], longitude=BKK_OUT[1],
                photoTimestamp="", note="ไปสัมภาษณ์ผู้สมัครงานที่คาเฟ่ใกล้ BTS อโศก",
                approvalStatus=ApprovalStatus.PENDING.value,
            ),
            EmployeeTimestamp(
                timestampId=IDS["ts_a_pending2"], company_employeeId=IDS["ce_a_ops"], companyId=CO_A,
                timestamp=_dt(hours=2, minutes=40), timestampType=TimestampType.WARNING,
                locationName="Outside Registered Area", latitude=BKK_OUT[0], longitude=BKK_OUT[1],
                photoTimestamp="", note="ออกภาคสนามติดตั้งอุปกรณ์ลูกค้า ลาดพร้าว",
                approvalStatus=ApprovalStatus.PENDING.value,
            ),
            EmployeeTimestamp(
                timestampId=IDS["ts_a_approved"], company_employeeId=IDS["ce_a_dev"], companyId=CO_A,
                timestamp=_dt(days=1, hours=5), timestampType=TimestampType.CHECK_IN,
                locationName="Outside Registered Area", latitude=BKK_OUT[0], longitude=BKK_OUT[1],
                photoTimestamp="", note="WFH ตามที่หัวหน้าอนุมัติล่วงหน้า",
                approvalStatus=ApprovalStatus.APPROVED.value,
                approvedBy=IDS["m_a_adm"], approvedAt=_dt(days=1, hours=2),
            ),
            EmployeeTimestamp(
                timestampId=IDS["ts_a_rejected"], company_employeeId=IDS["ce_a_ops"], companyId=CO_A,
                timestamp=_dt(days=2, hours=4), timestampType=TimestampType.DISAPPROVE,
                locationName="Outside Registered Area", latitude=BKK_OUT[0], longitude=BKK_OUT[1],
                photoTimestamp="", note="ลงเวลาผิดพลาดจากบ้าน",
                approvalStatus=ApprovalStatus.REJECTED.value,
                approvedBy=IDS["m_a_adm"], approvedAt=_dt(days=2, hours=1),
                rejectReason="ไม่อยู่ในแผนงานที่อนุมัติ และไม่มีหลักฐานการทำงาน",
            ),
            # B
            EmployeeTimestamp(
                timestampId=IDS["ts_b_in"], company_employeeId=IDS["ce_b_st1"], companyId=CO_B,
                timestamp=_dt(hours=9, minutes=2), timestampType=TimestampType.CHECK_IN,
                locationName="สาขาเชียงใหม่ ห้วยแก้ว", latitude=CNX_STORE[0], longitude=CNX_STORE[1],
                photoTimestamp="", note=None, approvalStatus=ApprovalStatus.NONE.value,
            ),
            EmployeeTimestamp(
                timestampId=IDS["ts_b_out"], company_employeeId=IDS["ce_b_st1"], companyId=CO_B,
                timestamp=_dt(hours=0, minutes=45), timestampType=TimestampType.CHECK_OUT,
                locationName="สาขาเชียงใหม่ ห้วยแก้ว", latitude=CNX_STORE[0], longitude=CNX_STORE[1],
                photoTimestamp="", note=None, approvalStatus=ApprovalStatus.NONE.value,
            ),
            EmployeeTimestamp(
                timestampId=IDS["ts_b_pending"], company_employeeId=IDS["ce_b_st2"], companyId=CO_B,
                timestamp=_dt(hours=4, minutes=15), timestampType=TimestampType.WARNING,
                locationName="Outside Registered Area", latitude=CNX_OUT[0], longitude=CNX_OUT[1],
                photoTimestamp="", note="ไปรับสินค้าที่ซัพพลายเออร์นอกสาขา",
                approvalStatus=ApprovalStatus.PENDING.value,
            ),
            EmployeeTimestamp(
                timestampId=IDS["ts_b_approved"], company_employeeId=IDS["ce_b_mgr"], companyId=CO_B,
                timestamp=_dt(days=1, hours=6), timestampType=TimestampType.CHECK_IN,
                locationName="Outside Registered Area", latitude=CNX_OUT[0], longitude=CNX_OUT[1],
                photoTimestamp="", note="ประชุมซัพพลายเออร์ที่สำนักงานใหญ่เชียงใหม่",
                approvalStatus=ApprovalStatus.APPROVED.value,
                approvedBy=IDS["m_b_adm"], approvedAt=_dt(days=1, hours=3),
            ),
        ]
    )

    session.add_all(
        [
            FaceEncoding(faceEncodingId=UUID("dddddddd-dddd-dddd-dddd-ddddddddddd1"), memberId=IDS["m_a_dev"], embedding=_unit_embedding(101)),
            FaceEncoding(faceEncodingId=UUID("dddddddd-dddd-dddd-dddd-ddddddddddd2"), memberId=IDS["m_a_hr"], embedding=_unit_embedding(202)),
            FaceEncoding(faceEncodingId=UUID("dddddddd-dddd-dddd-dddd-dddddddddd11"), memberId=IDS["m_b_st1"], embedding=_unit_embedding(303)),
            FaceEncoding(faceEncodingId=UUID("dddddddd-dddd-dddd-dddd-dddddddddd12"), memberId=IDS["m_b_st2"], embedding=_unit_embedding(404)),
        ]
    )

    await session.commit()
    print("Seed OK — 2 companies populated")
    _print_summary()


def _print_summary() -> None:
    print(
        f"""
Password for all accounts: {DEFAULT_PASSWORD}

System
  sysadmin

Company A  ({CO_A})  — ดีพียู แอทเทนแดนซ์ / DPUATT
  admin     HR admin
  boss      Eng manager
  emp1      Developer   (DPU-DEV-001)
  emp2      HR officer  (DPU-HR-001)
  emp3      Operations  (DPU-OPS-001)
  PENDING timestamps: {IDS['ts_a_pending']}, {IDS['ts_a_pending2']}

Company B  ({CO_B})  — สยาม รีเทล / SIAMRG
  admin_b   Company admin
  boss_b    Store manager
  staff1    Sales
  staff2    Warehouse
  PENDING timestamp: {IDS['ts_b_pending']}

Note: face_encoding vectors are synthetic — enroll real faces for check-in demos.
"""
    )


async def count_rows(session: AsyncSession) -> None:
    tables = [
        "member", "company", "department", "position",
        "company_location", "company_employee", "employee_timestamp", "face_encoding",
    ]
    print("Row counts:")
    for t in tables:
        n = (await session.execute(text(f'SELECT count(*) FROM "{t}"'))).scalar()
        print(f"  {t:20} {n}")


async def main(reset: bool) -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is not set")

    engine = create_async_engine(database_url, echo=False)
    Session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await ensure_profile_and_approval_columns(conn)

    async with Session() as session:
        if reset:
            await reset_all(session)
        await seed(session)
        await count_rows(session)

    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed DPU demo data (2 companies)")
    parser.add_argument("--reset", action="store_true", help="Wipe app tables then seed")
    args = parser.parse_args()
    asyncio.run(main(reset=args.reset))
