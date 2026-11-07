"""Shared helpers for the DB-backed integration tests (real PostgreSQL migrated by conftest).

Not a test module. Builds two isolated tenants with the usual cast (system admin, company admin,
plain employee, kiosk device) and tears them down again so the suite can run repeatedly against
the same database.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI
from sqlalchemy import text

from src.config.database import async_session, engine
from src.models.company import Company
from src.models.company_employee import CompanyEmployee, CompanyRoleType
from src.models.company_location import CompanyLocation
from src.models.department import Department
from src.models.hr_schedule import KioskDevice
from src.models.member import Member, RoleType, StatusType
from src.models.position import Position
from src.security.jwt import create_access_token, create_kiosk_token, hash_kiosk_token
from src.security.middleware import AuthzMiddleware

# Somewhere in Bangkok; the geofence radius is generous so float rounding never matters.
GEOFENCE_LAT = 13.7563
GEOFENCE_LON = 100.5018
GEOFENCE_RADIUS_KM = 0.5
FAR_AWAY_LAT = 18.7883  # Chiang Mai
FAR_AWAY_LON = 98.9853


def build_app(*routers: tuple[object, str]) -> FastAPI:
    """FastAPI app with the real AuthzMiddleware and the given (router, prefix) pairs."""
    app = FastAPI(redirect_slashes=False)
    app.add_middleware(AuthzMiddleware)
    for router, prefix in routers:
        app.include_router(router, prefix=prefix)
    return app


def client(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def make_member(username: str, role: RoleType = RoleType.MEMBER, password: str = "Passw0rd!xyz") -> Member:
    m = Member(
        memberId=uuid.uuid4(),
        username=username,
        email=f"{username}@example.com",
        firstName=username,
        lastName="Test",
        role=role,
        status=StatusType.ENABLE,
    )
    m.hash_password(password)
    return m


@dataclass
class Tenant:
    tag: str
    company: Company
    department: Department
    position: Position
    admin: Member
    employee: Member
    admin_employment: CompanyEmployee
    employee_employment: CompanyEmployee
    location: CompanyLocation
    kiosk: KioskDevice
    kiosk_token: str
    tokens: dict[str, str] = field(default_factory=dict)

    @property
    def company_id(self) -> uuid.UUID:
        return self.company.companyId


def _tenant_objects(tag: str, name: str) -> Tenant:
    company = Company(
        companyId=uuid.uuid4(),
        companyName=f"{name}-{tag}",
        companyCode=f"{name.upper()}{tag}",
        companyInfo=name,
        address="n/a",
        latitude=GEOFENCE_LAT,
        longitude=GEOFENCE_LON,
        picture="",
        ownerName="owner",
        contact="000",
    )
    dept = Department(departmentId=uuid.uuid4(), thName=f"แผนก {name}", engName=f"Dept {name}", companyId=company.companyId)
    pos = Position(positionId=uuid.uuid4(), thName=f"ตำแหน่ง {name}", engName=f"Pos {name}", companyId=company.companyId)
    admin = make_member(f"admin-{name}-{tag}")
    employee = make_member(f"emp-{name}-{tag}")
    admin_emp = CompanyEmployee(
        memberId=admin.memberId,
        companyId=company.companyId,
        departmentId=dept.departmentId,
        positionId=pos.positionId,
        companyRoleType=CompanyRoleType.ADMIN_COMPANY,
        employeeId=f"ADM-{tag}",
    )
    emp_emp = CompanyEmployee(
        memberId=employee.memberId,
        companyId=company.companyId,
        departmentId=dept.departmentId,
        positionId=pos.positionId,
        companyRoleType=CompanyRoleType.EMP,
        employeeId=f"EMP-{tag}",
    )
    location = CompanyLocation(
        locationId=uuid.uuid4(),
        companyId=company.companyId,
        latitude=GEOFENCE_LAT,
        longitude=GEOFENCE_LON,
        locationName=f"HQ {name}",
        radius=GEOFENCE_RADIUS_KM,
    )
    kiosk = KioskDevice(deviceId=uuid.uuid4(), companyId=company.companyId, name=f"Gate {name}")
    kiosk_token = create_kiosk_token(str(kiosk.deviceId), str(company.companyId), location_id=str(location.locationId))
    kiosk.tokenHash = hash_kiosk_token(kiosk_token)
    kiosk.pairedAt = datetime.now(timezone.utc)
    return Tenant(
        tag=tag,
        company=company,
        department=dept,
        position=pos,
        admin=admin,
        employee=employee,
        admin_employment=admin_emp,
        employee_employment=emp_emp,
        location=location,
        kiosk=kiosk,
        kiosk_token=kiosk_token,
    )


@dataclass
class World:
    tag: str
    sysadmin: Member
    a: Tenant
    b: Tenant
    tokens: dict[str, str]

    def auth(self, who: str) -> dict[str, str]:
        return bearer(self.tokens[who])


async def seed_world() -> World:
    """Two tenants + a system admin. Tokens: sysadmin, admin_a, admin_b, emp_a, emp_b, kiosk_a, kiosk_b."""
    await engine.dispose(close=False)
    tag = uuid.uuid4().hex[:6]
    sysadmin = make_member(f"sysadmin-{tag}", RoleType.ADMIN_SYSTEM)
    a = _tenant_objects(tag, "alpha")
    b = _tenant_objects(tag, "beta")
    async with async_session() as db:
        db.add_all([a.company, b.company, sysadmin])
        await db.flush()
        db.add_all([a.department, a.position, b.department, b.position, a.admin, a.employee, b.admin, b.employee])
        await db.flush()
        db.add_all([a.admin_employment, a.employee_employment, b.admin_employment, b.employee_employment])
        db.add_all([a.location, b.location, a.kiosk, b.kiosk])
        await db.commit()
    tokens = {
        "sysadmin": create_access_token(str(sysadmin.memberId), sysadmin.username),
        "admin_a": create_access_token(str(a.admin.memberId), a.admin.username),
        "admin_b": create_access_token(str(b.admin.memberId), b.admin.username),
        "emp_a": create_access_token(str(a.employee.memberId), a.employee.username),
        "emp_b": create_access_token(str(b.employee.memberId), b.employee.username),
        "kiosk_a": a.kiosk_token,
        "kiosk_b": b.kiosk_token,
    }
    return World(tag=tag, sysadmin=sysadmin, a=a, b=b, tokens=tokens)


async def teardown_world(world: World) -> None:
    cids = {"a": world.a.company_id, "b": world.b.company_id}
    async with async_session() as db:
        await db.execute(text('DELETE FROM notification_outbox WHERE "companyId" IN (:a, :b)'), cids)
        await db.execute(text('DELETE FROM audit_log WHERE "companyId" IN (:a, :b)'), cids)
        await db.execute(text("DELETE FROM system_setting WHERE key LIKE :a OR key LIKE :b"), {
            "a": f"%{cids['a']}",
            "b": f"%{cids['b']}",
        })
        for tbl in (
            "attendance_daily",
            "employee_timestamp",
            "face_encoding",
            "leave_request",
            "company_employee",
            "work_shift",
            "company_holiday",
            "kiosk_device",
            "company_location",
            "department",
            "position",
        ):
            await db.execute(text(f'DELETE FROM {tbl} WHERE "companyId" IN (:a, :b)'), cids)
        await db.execute(text("DELETE FROM member WHERE username LIKE :pat"), {"pat": f"%-{world.tag}"})
        await db.execute(text('DELETE FROM company WHERE "companyId" IN (:a, :b)'), cids)
        await db.commit()
    await engine.dispose()
