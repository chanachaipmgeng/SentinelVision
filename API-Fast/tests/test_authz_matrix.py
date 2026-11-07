"""B2: authorization matrix — AuthzMiddleware + tenancy deps across the real routers.

Actors: anonymous, garbage / expired / wrong-type tokens, system admin, company admin of A,
company admin of B, plain employee of A, kiosk device of A and B. Routes: every company-scoped
collection the middleware binds via ``_COMPANY_RES`` plus the system-admin-only listings and the
kiosk allow-list. Expected codes come from the security baseline in ``.cursor/rules``.
"""
from __future__ import annotations

import os
import uuid
from datetime import timedelta

import pytest
import pytest_asyncio

if not os.environ.get("DPU_TEST_DB_READY"):
    pytest.skip(
        "No test database: set TEST_DATABASE_URL or `pip install pgserver`",
        allow_module_level=True,
    )

from src.routes import (  # noqa: E402
    company_location_routes,
    company_routes,
    dashboard_routes,
    department_routes,
    employee_routes,
    employee_timestamp_routes,
    hr_routes,
    member_routes,
    notification_routes,
    position_routes,
    system_routes,
)
from src.security.jwt import TYP_ACCESS, TYP_REFRESH, create_token, create_token_pair  # noqa: E402
from tests.support import bearer, build_app, client, seed_world, teardown_world  # noqa: E402

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def world():
    w = await seed_world()
    w.app = build_app(
        (company_routes.router, "/companys"),
        (member_routes.router, "/members"),
        (department_routes.router, "/departments"),
        (position_routes.router, "/positions"),
        (employee_routes.router, "/employees"),
        (employee_timestamp_routes.router, "/timestamp"),
        (company_location_routes.router, "/company-locations"),
        (dashboard_routes.router, "/dashboard"),
        (notification_routes.router, "/notifications"),
        (hr_routes.router, "/hr"),
        (system_routes.router, "/system"),
    )
    yield w
    await teardown_world(w)


# Company-scoped GET collections: (path template, kiosk may read?)
COMPANY_ROUTES = [
    ("/employees/company/{cid}", False),
    ("/departments/company/{cid}", False),
    ("/positions/company/{cid}", False),
    ("/timestamp/company/{cid}", False),
    ("/timestamp/search/company/{cid}", False),
    ("/timestamp/export/company/{cid}?format=csv", False),
    ("/timestamp/company/{cid}/shift-settings", False),
    ("/company-locations/company/{cid}", True),
    ("/dashboard/stats/{cid}", False),
    ("/companys/{cid}", False),
    ("/companys/{cid}/audit-logs", False),
    ("/notifications/company/{cid}/settings", False),
    ("/notifications/company/{cid}/outbox", False),
    ("/hr/company/{cid}/shifts", False),
    ("/hr/company/{cid}/holidays", False),
    ("/hr/company/{cid}/leaves", False),
    ("/hr/company/{cid}/kiosk-devices", False),
]

# actor → expected status on a company-A route
ACTOR_EXPECTATIONS = [
    ("sysadmin", 200),
    ("admin_a", 200),
    ("admin_b", 403),  # other tenant's admin
    ("emp_a", 403),  # plain employee of the same tenant: "Company admin required"
    ("emp_b", 403),
]


@pytest.mark.parametrize("route,kiosk_ok", COMPANY_ROUTES, ids=[r for r, _ in COMPANY_ROUTES])
@pytest.mark.parametrize("who,expected", ACTOR_EXPECTATIONS)
async def test_company_route_matrix(world, route, kiosk_ok, who, expected):
    path = route.format(cid=world.a.company_id)
    async with client(world.app) as c:
        r = await c.get(path, headers=world.auth(who))
    assert r.status_code == expected, f"{who} GET {path} → {r.status_code} {r.text[:200]}"


@pytest.mark.parametrize("route,kiosk_ok", COMPANY_ROUTES, ids=[r for r, _ in COMPANY_ROUTES])
async def test_company_route_requires_token(world, route, kiosk_ok):
    path = route.format(cid=world.a.company_id)
    async with client(world.app) as c:
        anonymous = await c.get(path)
        garbage = await c.get(path, headers=bearer("not.a.jwt"))
    assert anonymous.status_code == 401 and anonymous.json()["detail"] == "Authorization required"
    assert garbage.status_code == 401 and garbage.json()["detail"] == "Invalid token"


@pytest.mark.parametrize("route,kiosk_ok", COMPANY_ROUTES, ids=[r for r, _ in COMPANY_ROUTES])
async def test_kiosk_token_matrix(world, route, kiosk_ok):
    """Kiosk device tokens only reach the kiosk allow-list, and only for their own company."""
    path_a = route.format(cid=world.a.company_id)
    path_b = route.format(cid=world.b.company_id)
    async with client(world.app) as c:
        own = await c.get(path_a, headers=world.auth("kiosk_a"))
        other = await c.get(path_b, headers=world.auth("kiosk_a"))
    if kiosk_ok:
        assert own.status_code == 200, own.text
        assert other.status_code == 403
        assert "company" in other.json()["detail"].lower()
    else:
        assert own.status_code == 403, own.text
        assert "kiosk" in own.json()["detail"].lower()
        assert other.status_code == 403


async def test_kiosk_token_rejected_for_writes_on_allowed_prefix(world):
    body = {"latitude": 1, "longitude": 1, "locationName": "x", "radius": 0.1}
    async with client(world.app) as c:
        r = await c.post(
            f"/company-locations/company/{world.a.company_id}", json=body, headers=world.auth("kiosk_a")
        )
    assert r.status_code == 403


# ------------------------------------------------------------------ system-admin-only surfaces
@pytest.mark.parametrize("path", ["/companys", "/departments", "/positions", "/members"])
async def test_global_listings_are_system_admin_only(world, path):
    async with client(world.app) as c:
        for who in ("admin_a", "emp_a"):
            r = await c.get(path, headers=world.auth(who))
            assert r.status_code == 403, f"{who} {path} → {r.status_code}"
        ok = await c.get(path, headers=world.auth("sysadmin"))
    assert ok.status_code == 200, ok.text
    assert isinstance(ok.json(), list)


async def test_company_admin_cannot_create_company(world):
    body = {
        "companyName": f"evil-{uuid.uuid4().hex[:6]}",
        "companyCode": f"EV{uuid.uuid4().hex[:6]}",
        "companyInfo": "x",
        "address": "x",
    }
    async with client(world.app) as c:
        r = await c.post("/companys", json=body, headers=world.auth("admin_a"))
        assert r.status_code == 403
        r = await c.post("/companys", json=body, headers=world.auth("emp_a"))
        assert r.status_code == 403


async def test_member_self_scope(world):
    """/employees/member/{memberId}/companies is self-only for non system admins."""
    mine = f"/employees/member/{world.a.employee.memberId}/companies"
    theirs = f"/employees/member/{world.b.employee.memberId}/companies"
    async with client(world.app) as c:
        assert (await c.get(mine, headers=world.auth("emp_a"))).status_code == 200
        r = await c.get(theirs, headers=world.auth("emp_a"))
        assert r.status_code == 403
        assert (await c.get(theirs, headers=world.auth("sysadmin"))).status_code == 200


# ------------------------------------------------------------------ token lifecycle regressions
async def test_expired_access_token_is_401(world):
    expired = create_token(
        str(world.a.admin.memberId), world.a.admin.username, typ=TYP_ACCESS, expires=timedelta(seconds=-5)
    )
    async with client(world.app) as c:
        r = await c.get(f"/employees/company/{world.a.company_id}", headers=bearer(expired))
    assert r.status_code == 401
    assert r.json()["detail"] == "Token has expired"


async def test_refresh_token_cannot_be_used_as_access_token(world):
    _access, refresh = create_token_pair(str(world.a.admin.memberId), world.a.admin.username)
    async with client(world.app) as c:
        r = await c.get(f"/employees/company/{world.a.company_id}", headers=bearer(refresh))
    assert r.status_code == 401
    assert r.json()["detail"] == "Wrong token type"
    assert TYP_REFRESH == "refresh"


async def test_tampered_signature_is_401(world):
    token = world.tokens["admin_a"]
    head, payload, sig = token.split(".")
    tampered = f"{head}.{payload}.{'A' if sig[0] != 'A' else 'B'}{sig[1:]}"
    async with client(world.app) as c:
        r = await c.get(f"/employees/company/{world.a.company_id}", headers=bearer(tampered))
    assert r.status_code == 401


async def test_token_of_unknown_member_is_401(world):
    ghost = create_token(str(uuid.uuid4()), "ghost", typ=TYP_ACCESS, expires=timedelta(minutes=5))
    async with client(world.app) as c:
        r = await c.get(f"/employees/company/{world.a.company_id}", headers=bearer(ghost))
    assert r.status_code == 401
    assert r.json()["detail"] == "Member not found"


async def test_disabled_member_is_403(world):
    from sqlalchemy import update

    from src.config.database import async_session
    from src.models.member import Member, StatusType

    async with async_session() as db:
        await db.execute(
            update(Member).where(Member.memberId == world.b.employee.memberId).values(status=StatusType.DISABLED)
        )
        await db.commit()
    try:
        async with client(world.app) as c:
            r = await c.get(f"/employees/member/{world.b.employee.memberId}/companies", headers=world.auth("emp_b"))
        assert r.status_code == 403
        assert r.json()["detail"] == "Account disabled"
    finally:
        async with async_session() as db:
            await db.execute(
                update(Member).where(Member.memberId == world.b.employee.memberId).values(status=StatusType.ENABLE)
            )
            await db.commit()
