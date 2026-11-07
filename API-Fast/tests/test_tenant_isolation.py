"""A6 tenant-isolation authorization matrix (real PostgreSQL + pgvector).

Routes covered (same company → allowed, other company → 403, system admin → allowed):
- GET /departments, GET /positions                      (system admin only)
- GET/PUT/DELETE /departments/{id}, /positions/{id}      (bound to the row's company)
- DELETE /face/encodings/{faceEncodingId}               (bound via FaceEncoding.companyId)
- GET /face/enrolled-images/{faceEncodingId}?companyId= (encoding must belong to companyId)
- PUT /employees/company/{companyId}                     (Member.email guard)

Requires DATABASE_URL to point at a reachable PostgreSQL (see tests/conftest.py).
"""
from __future__ import annotations

import os
import sys
import uuid
from unittest.mock import MagicMock

import pytest
import pytest_asyncio

# Keep InsightFace / OpenCV / ONNX out of the import graph.
for _mod in ("insightface", "insightface.app", "cv2", "onnxruntime"):
    sys.modules.setdefault(_mod, MagicMock())

if not os.environ.get("DPU_TEST_DB_READY"):
    pytest.skip(
        "No test database: set TEST_DATABASE_URL or `pip install pgserver`",
        allow_module_level=True,
    )

import httpx  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from sqlalchemy import text  # noqa: E402

import src.models  # noqa: E402,F401  register every mapper before create_all
from src.config.database import Base, async_session, engine  # noqa: E402
from src.models.company import Company  # noqa: E402
from src.models.company_employee import CompanyEmployee, CompanyRoleType  # noqa: E402
from src.models.department import Department  # noqa: E402
from src.models.face_encoding import FACE_EMBEDDING_DIM, FaceEncoding  # noqa: E402
from src.models.member import Member, RoleType, StatusType  # noqa: E402
from src.models.position import Position  # noqa: E402
from src.routes import (  # noqa: E402
    department_routes,
    employee_routes,
    face_routes,
    position_routes,
)
from src.security.jwt import create_access_token  # noqa: E402
from src.security.middleware import AuthzMiddleware  # noqa: E402
from src.services import audit_service, notification_service  # noqa: E402,F401  audit_log / outbox tables

pytestmark = pytest.mark.asyncio(loop_scope="module")


def _app() -> FastAPI:
    app = FastAPI(redirect_slashes=False)
    app.add_middleware(AuthzMiddleware)
    app.include_router(department_routes.router, prefix="/departments")
    app.include_router(position_routes.router, prefix="/positions")
    app.include_router(employee_routes.router, prefix="/employees")
    app.include_router(face_routes.router, prefix="/face")
    return app


def _member(username: str, role: RoleType = RoleType.MEMBER) -> Member:
    m = Member(
        memberId=uuid.uuid4(),
        username=username,
        email=f"{username}@example.com",
        firstName=username,
        lastName="Test",
        role=role,
        status=StatusType.ENABLE,
    )
    m.hash_password("Passw0rd!xyz")
    return m


def _company(name: str) -> Company:
    return Company(
        companyId=uuid.uuid4(),
        companyName=name,
        companyCode=name.upper(),
        companyInfo=name,
        address="n/a",
    )


def _employee(member: Member, company: Company, dept: Department, pos: Position, role: CompanyRoleType):
    return CompanyEmployee(
        memberId=member.memberId,
        companyId=company.companyId,
        departmentId=dept.departmentId,
        positionId=pos.positionId,
        companyRoleType=role,
    )


def _encoding(member: Member, company: Company | None) -> FaceEncoding:
    return FaceEncoding(
        faceEncodingId=uuid.uuid4(),
        memberId=member.memberId,
        companyId=company.companyId if company else None,
        embedding=[0.0] * FACE_EMBEDDING_DIM,
    )


class Fixture:
    pass


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def fx():
    # Other modules (e.g. test_oidc's audit writes under TestClient) may have left pooled asyncpg
    # connections bound to a different event loop; drop them without awaiting their close.
    await engine.dispose(close=False)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"test database not reachable: {exc}")

    f = Fixture()
    f.company_a = _company(f"tenant-a-{uuid.uuid4().hex[:6]}")
    f.company_b = _company(f"tenant-b-{uuid.uuid4().hex[:6]}")
    f.dept_a = Department(departmentId=uuid.uuid4(), thName="A", engName="A", companyId=f.company_a.companyId)
    f.dept_b = Department(departmentId=uuid.uuid4(), thName="B", engName="B", companyId=f.company_b.companyId)
    f.pos_a = Position(positionId=uuid.uuid4(), thName="A", engName="A", companyId=f.company_a.companyId)
    f.pos_b = Position(positionId=uuid.uuid4(), thName="B", engName="B", companyId=f.company_b.companyId)

    tag = uuid.uuid4().hex[:6]
    f.sysadmin = _member(f"sysadmin-{tag}", RoleType.ADMIN_SYSTEM)
    f.admin_a = _member(f"admin-a-{tag}")
    f.admin_b = _member(f"admin-b-{tag}")
    f.emp_a = _member(f"emp-a-{tag}")
    f.emp_b = _member(f"emp-b-{tag}")
    f.multi = _member(f"multi-{tag}")  # employed by A and B

    f.enc_a = _encoding(f.emp_a, f.company_a)
    f.enc_a_legacy = _encoding(f.emp_a, None)  # pre-migration row, companyId unresolved
    f.enc_b = _encoding(f.emp_b, f.company_b)

    async with async_session() as db:
        db.add_all([f.company_a, f.company_b])
        await db.flush()
        db.add_all([f.dept_a, f.dept_b, f.pos_a, f.pos_b])
        db.add_all([f.sysadmin, f.admin_a, f.admin_b, f.emp_a, f.emp_b, f.multi])
        await db.flush()
        f.ce_admin_a = _employee(f.admin_a, f.company_a, f.dept_a, f.pos_a, CompanyRoleType.ADMIN_COMPANY)
        f.ce_admin_b = _employee(f.admin_b, f.company_b, f.dept_b, f.pos_b, CompanyRoleType.ADMIN_COMPANY)
        f.ce_emp_a = _employee(f.emp_a, f.company_a, f.dept_a, f.pos_a, CompanyRoleType.EMP)
        f.ce_emp_b = _employee(f.emp_b, f.company_b, f.dept_b, f.pos_b, CompanyRoleType.EMP)
        f.ce_multi_a = _employee(f.multi, f.company_a, f.dept_a, f.pos_a, CompanyRoleType.EMP)
        f.ce_multi_b = _employee(f.multi, f.company_b, f.dept_b, f.pos_b, CompanyRoleType.EMP)
        db.add_all([f.ce_admin_a, f.ce_admin_b, f.ce_emp_a, f.ce_emp_b, f.ce_multi_a, f.ce_multi_b])
        db.add_all([f.enc_a, f.enc_a_legacy, f.enc_b])
        await db.commit()

    f.tokens = {
        name: create_access_token(str(m.memberId), m.username)
        for name, m in {
            "sysadmin": f.sysadmin,
            "admin_a": f.admin_a,
            "admin_b": f.admin_b,
            "emp_a": f.emp_a,
        }.items()
    }
    f.app = _app()
    yield f

    async with async_session() as db:
        pat = f"%-{tag}"
        await db.execute(
            text('DELETE FROM face_encoding WHERE "memberId" IN (SELECT "memberId" FROM member WHERE username LIKE :pat)'),
            {"pat": pat},
        )
        cids = {"a": f.company_a.companyId, "b": f.company_b.companyId}
        for tbl in ("company_employee", "department", "position"):
            await db.execute(text(f'DELETE FROM {tbl} WHERE "companyId" IN (:a, :b)'), cids)
        await db.execute(text("DELETE FROM member WHERE username LIKE :pat"), {"pat": pat})
        await db.execute(text('DELETE FROM company WHERE "companyId" IN (:a, :b)'), cids)
        await db.commit()
    await engine.dispose()


def _client(fx) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=fx.app), base_url="http://test")


def _auth(fx, who: str) -> dict:
    return {"Authorization": f"Bearer {fx.tokens[who]}"}


# --------------------------------------------------------------------------- listings
@pytest.mark.parametrize("path", ["/departments", "/positions"])
async def test_cross_tenant_listing_requires_system_admin(fx, path):
    async with _client(fx) as c:
        assert (await c.get(path, headers=_auth(fx, "admin_a"))).status_code == 403
        assert (await c.get(path, headers=_auth(fx, "emp_a"))).status_code == 403
        r = await c.get(path, headers=_auth(fx, "sysadmin"))
        assert r.status_code == 200
        assert isinstance(r.json(), list)


async def test_listing_without_token_is_401(fx):
    async with _client(fx) as c:
        assert (await c.get("/departments")).status_code == 401


# ------------------------------------------------------------- /departments/{id}, /positions/{id}
@pytest.mark.parametrize(
    "who,expected",
    [("admin_a", 200), ("sysadmin", 200), ("admin_b", 403), ("emp_a", 403)],
)
async def test_get_department_by_id_matrix(fx, who, expected):
    async with _client(fx) as c:
        r = await c.get(f"/departments/{fx.dept_a.departmentId}", headers=_auth(fx, who))
        assert r.status_code == expected, r.text
        if expected == 200:
            assert r.json()["companyId"] == str(fx.company_a.companyId)


@pytest.mark.parametrize(
    "who,expected",
    [("admin_a", 200), ("sysadmin", 200), ("admin_b", 403), ("emp_a", 403)],
)
async def test_get_position_by_id_matrix(fx, who, expected):
    async with _client(fx) as c:
        r = await c.get(f"/positions/{fx.pos_a.positionId}", headers=_auth(fx, who))
        assert r.status_code == expected, r.text


async def test_unknown_department_id_is_404_not_leak(fx):
    async with _client(fx) as c:
        r = await c.get(f"/departments/{uuid.uuid4()}", headers=_auth(fx, "admin_a"))
        assert r.status_code == 404


async def test_update_department_blocked_at_middleware_for_other_tenant(fx):
    body = {"thName": "hijack", "engName": "hijack", "companyId": str(fx.company_a.companyId)}
    async with _client(fx) as c:
        r = await c.put(f"/departments/{fx.dept_a.departmentId}", json=body, headers=_auth(fx, "admin_b"))
        assert r.status_code == 403
        r = await c.put(
            f"/departments/{fx.dept_a.departmentId}",
            json={"thName": "renamed", "engName": "renamed"},
            headers=_auth(fx, "admin_a"),
        )
        assert r.status_code == 200, r.text
        assert r.json()["thName"] == "renamed"
        r = await c.put(
            f"/departments/{fx.dept_b.departmentId}",
            json={"thName": "sys", "engName": "sys"},
            headers=_auth(fx, "sysadmin"),
        )
        assert r.status_code == 200, r.text


async def test_cannot_rehome_department_into_other_tenant(fx):
    body = {"companyId": str(fx.company_b.companyId)}
    async with _client(fx) as c:
        r = await c.put(f"/departments/{fx.dept_a.departmentId}", json=body, headers=_auth(fx, "admin_a"))
        assert r.status_code == 403
        r = await c.put(f"/positions/{fx.pos_a.positionId}", json=body, headers=_auth(fx, "admin_a"))
        assert r.status_code == 403
    async with async_session() as db:
        assert (await db.get(Department, fx.dept_a.departmentId)).companyId == fx.company_a.companyId
        assert (await db.get(Position, fx.pos_a.positionId)).companyId == fx.company_a.companyId


async def test_delete_position_matrix(fx):
    extra = Position(positionId=uuid.uuid4(), thName="tmp", engName="tmp", companyId=fx.company_a.companyId)
    async with async_session() as db:
        db.add(extra)
        await db.commit()
    async with _client(fx) as c:
        assert (await c.delete(f"/positions/{extra.positionId}", headers=_auth(fx, "admin_b"))).status_code == 403
        assert (await c.delete(f"/positions/{extra.positionId}", headers=_auth(fx, "emp_a"))).status_code == 403
        assert (await c.delete(f"/positions/{extra.positionId}", headers=_auth(fx, "admin_a"))).status_code == 200


# ------------------------------------------------------------------------- face encodings
async def test_delete_encoding_other_tenant_forbidden(fx):
    async with _client(fx) as c:
        r = await c.delete(f"/face/encodings/{fx.enc_a.faceEncodingId}", headers=_auth(fx, "admin_b"))
        assert r.status_code == 403
        # Claiming a companyId the caller does administer must not override the row's owner.
        r = await c.delete(
            f"/face/encodings/{fx.enc_a.faceEncodingId}",
            params={"companyId": str(fx.company_b.companyId)},
            headers=_auth(fx, "admin_b"),
        )
        assert r.status_code == 403
        r = await c.delete(f"/face/encodings/{fx.enc_a.faceEncodingId}", headers=_auth(fx, "emp_a"))
        assert r.status_code == 403
    async with async_session() as db:
        assert await db.get(FaceEncoding, fx.enc_a.faceEncodingId) is not None


async def test_delete_unknown_encoding_has_no_any_company_fallback(fx):
    async with _client(fx) as c:
        r = await c.delete(f"/face/encodings/{uuid.uuid4()}", headers=_auth(fx, "admin_a"))
        assert r.status_code == 404
        r = await c.delete(f"/face/encodings/{uuid.uuid4()}", headers=_auth(fx, "sysadmin"))
        assert r.status_code == 404  # reaches the controller, which 404s


async def test_delete_legacy_encoding_falls_back_to_member_company(fx):
    async with _client(fx) as c:
        r = await c.delete(f"/face/encodings/{fx.enc_a_legacy.faceEncodingId}", headers=_auth(fx, "admin_b"))
        assert r.status_code == 403
        r = await c.delete(f"/face/encodings/{fx.enc_a_legacy.faceEncodingId}", headers=_auth(fx, "admin_a"))
        assert r.status_code == 200, r.text


async def test_delete_encoding_same_tenant_and_sysadmin_allowed(fx):
    async with _client(fx) as c:
        r = await c.delete(f"/face/encodings/{fx.enc_a.faceEncodingId}", headers=_auth(fx, "admin_a"))
        assert r.status_code == 200, r.text
        r = await c.delete(f"/face/encodings/{fx.enc_b.faceEncodingId}", headers=_auth(fx, "sysadmin"))
        assert r.status_code == 200, r.text


async def test_enrolled_image_requires_encoding_in_claimed_company(fx):
    enc_b2 = _encoding(fx.emp_b, fx.company_b)
    async with async_session() as db:
        db.add(enc_b2)
        await db.commit()
    async with _client(fx) as c:
        # Admin of A claims A but asks for B's encoding → 403 before any file is read.
        r = await c.get(
            f"/face/enrolled-images/{enc_b2.faceEncodingId}",
            params={"companyId": str(fx.company_a.companyId)},
            headers=_auth(fx, "admin_a"),
        )
        assert r.status_code == 403
        # Same-tenant admin passes authz (404 only because no JPEG exists on disk in tests).
        r = await c.get(
            f"/face/enrolled-images/{enc_b2.faceEncodingId}",
            params={"companyId": str(fx.company_b.companyId)},
            headers=_auth(fx, "admin_b"),
        )
        assert r.status_code == 404, r.text


class _KioskRequest:
    """Minimal stand-in for starlette.Request as seen after AuthzMiddleware (kiosk token)."""

    def __init__(self, kiosk_company_id, company_id_param=None):
        self.state = type("S", (), {})()
        self.state.kiosk_company_id = kiosk_company_id
        self.state.member = None
        self.query_params = {"companyId": str(company_id_param)} if company_id_param else {}


async def test_kiosk_token_bound_to_encoding_company(fx):
    from fastapi import HTTPException

    from src.security.deps import assert_encoding_company_access

    enc_a2 = _encoding(fx.emp_a, fx.company_a)
    enc_a2_legacy = _encoding(fx.emp_a, None)
    async with async_session() as db:
        db.add_all([enc_a2, enc_a2_legacy])
        await db.commit()
    kiosk_b = fx.company_b.companyId
    async with async_session() as db:
        # Kiosk of B must not reach A's encoding, even when claiming B.
        with pytest.raises(HTTPException) as ei:
            await assert_encoding_company_access(_KioskRequest(kiosk_b, kiosk_b), db, enc_a2.faceEncodingId)
        assert ei.value.status_code == 403
        # Legacy row (NULL companyId): falls back to "member employed by kiosk company" → A-only member → 403.
        with pytest.raises(HTTPException) as ei:
            await assert_encoding_company_access(_KioskRequest(kiosk_b), db, enc_a2_legacy.faceEncodingId)
        assert ei.value.status_code == 403
        # Kiosk of B reading B's own encoding is fine.
        enc_b3 = _encoding(fx.emp_b, fx.company_b)
        db.add(enc_b3)
        await db.commit()
        await assert_encoding_company_access(_KioskRequest(kiosk_b, kiosk_b), db, enc_b3.faceEncodingId)
        # Unknown encoding (Face Core BFF mode) without a companyId claim → 403.
        with pytest.raises(HTTPException) as ei:
            await assert_encoding_company_access(_KioskRequest(kiosk_b), db, uuid.uuid4())
        assert ei.value.status_code == 403


async def test_resolve_enroll_company_id_rules(fx):
    from fastapi import HTTPException

    from src.controllers.face_controller import resolve_enroll_company_id

    async with async_session() as db:
        # single-company member → that company
        assert await resolve_enroll_company_id(db, fx.emp_a.memberId, None, fx.admin_a) == fx.company_a.companyId
        # multi-company member, admin of A acting → A
        assert await resolve_enroll_company_id(db, fx.multi.memberId, None, fx.admin_a) == fx.company_a.companyId
        # multi-company member, admin of B acting → B
        assert await resolve_enroll_company_id(db, fx.multi.memberId, None, fx.admin_b) == fx.company_b.companyId
        # explicit company where the member is not employed → 403
        with pytest.raises(HTTPException) as ei:
            await resolve_enroll_company_id(db, fx.emp_a.memberId, fx.company_b.companyId, fx.sysadmin)
        assert ei.value.status_code == 403


# ------------------------------------------------------------------- Member.email guard
def _update_payload(fx, ce: CompanyEmployee, member: Member, email: str) -> dict:
    return {
        "company_employeeId": str(ce.company_employeeId),
        "member": {"email": email, "firstName": member.firstName, "lastName": member.lastName},
        "position": {"positionId": str(ce.positionId), "thName": "A", "engName": "A"},
        "department": {"departmentId": str(ce.departmentId), "thName": "A", "engName": "A"},
        "companyRoleType": ce.companyRoleType.value,
        "empType": ce.empType.value if ce.empType is not None else 1,
    }


async def test_company_admin_cannot_change_email_of_multi_company_member(fx):
    payload = _update_payload(fx, fx.ce_multi_a, fx.multi, "takeover@example.com")
    async with _client(fx) as c:
        r = await c.put(f"/employees/company/{fx.company_a.companyId}", json=payload, headers=_auth(fx, "admin_a"))
        assert r.status_code == 403, r.text
    async with async_session() as db:
        m = await db.get(Member, fx.multi.memberId)
        assert m.email == fx.multi.email


async def test_company_admin_unchanged_email_still_updates_profile(fx):
    payload = _update_payload(fx, fx.ce_multi_a, fx.multi, fx.multi.email)
    payload["member"]["firstName"] = "Renamed"
    async with _client(fx) as c:
        r = await c.put(f"/employees/company/{fx.company_a.companyId}", json=payload, headers=_auth(fx, "admin_a"))
        assert r.status_code == 200, r.text
        assert r.json()["member"]["firstName"] == "Renamed"


async def test_company_admin_can_change_email_of_single_company_member(fx):
    new_email = f"emp-a-new-{uuid.uuid4().hex[:6]}@example.com"
    payload = _update_payload(fx, fx.ce_emp_a, fx.emp_a, new_email)
    async with _client(fx) as c:
        r = await c.put(f"/employees/company/{fx.company_a.companyId}", json=payload, headers=_auth(fx, "admin_a"))
        assert r.status_code == 200, r.text
        assert r.json()["member"]["email"] == new_email


async def test_system_admin_can_change_email_of_multi_company_member(fx):
    new_email = f"multi-new-{uuid.uuid4().hex[:6]}@example.com"
    payload = _update_payload(fx, fx.ce_multi_a, fx.multi, new_email)
    async with _client(fx) as c:
        r = await c.put(f"/employees/company/{fx.company_a.companyId}", json=payload, headers=_auth(fx, "sysadmin"))
        assert r.status_code == 200, r.text
        assert r.json()["member"]["email"] == new_email


async def test_other_tenant_admin_cannot_update_employee_at_all(fx):
    payload = _update_payload(fx, fx.ce_emp_a, fx.emp_a, fx.emp_a.email)
    async with _client(fx) as c:
        r = await c.put(f"/employees/company/{fx.company_a.companyId}", json=payload, headers=_auth(fx, "admin_b"))
        assert r.status_code == 403


# ------------------------------------------------------------------ schema / backfill
async def test_schema_migrate_backfills_face_encoding_company(fx):
    from src.utils.schema_migrate import ensure_profile_and_approval_columns

    orphan = _encoding(fx.emp_b, None)
    async with async_session() as db:
        db.add(orphan)
        await db.commit()
    async with engine.begin() as conn:
        await ensure_profile_and_approval_columns(conn)
    async with async_session() as db:
        row = await db.get(FaceEncoding, orphan.faceEncodingId)
        assert row.companyId == fx.company_b.companyId
        idx = await db.execute(
            text("SELECT 1 FROM pg_indexes WHERE indexname = 'face_encoding_company_member_idx'")
        )
        assert idx.first() is not None
