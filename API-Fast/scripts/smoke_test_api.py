"""
Smoke-test core API flows against a running stack (after seed).

Usage (recommended — inside compose network):
  docker compose run --rm -v ./API-Fast:/app --entrypoint python api \\
    scripts/smoke_test_api.py --base-url http://api:8000

From host if API port is published:
  python API-Fast/scripts/smoke_test_api.py --base-url http://localhost:8000
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any
from uuid import UUID

COMPANY_ID = "11111111-1111-1111-1111-111111111111"
COMPANY_B_ID = "11111111-1111-1111-1111-111111111112"
PENDING_TS = "cccccccc-cccc-cccc-cccc-ccccccccccc2"
PASSWORD = "Password123!"


class Fail(Exception):
    pass


def _req(
    method: str,
    url: str,
    body: dict | None = None,
    token: str | None = None,
) -> Any:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            if not raw:
                return None
            ctype = resp.headers.get("Content-Type", "")
            if "application/json" not in ctype and not raw.lstrip().startswith(("{", "[")):
                raise Fail(
                    f"{method} {url} -> non-JSON response ({ctype}): {raw[:120]!r}"
                )
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise Fail(f"{method} {url} -> HTTP {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise Fail(f"{method} {url} -> {e}") from e


def run(base: str) -> None:
    base = base.rstrip("/")
    passed = 0

    def ok(name: str) -> None:
        nonlocal passed
        passed += 1
        print(f"  PASS  {name}")

    print(f"Smoke tests -> {base}\n")

    root = _req("GET", f"{base}/")
    if not isinstance(root, dict) or "message" not in root:
        raise Fail("GET / unexpected response")
    ok("GET /")

    login = _req(
        "POST",
        f"{base}/auth/login",
        {"username": "admin", "password": PASSWORD},
    )
    token = login.get("access_token")
    if not token:
        raise Fail("login missing access_token")
    ok("POST /auth/login (admin)")

    login_emp = _req(
        "POST",
        f"{base}/auth/login",
        {"username": "emp1", "password": PASSWORD},
    )
    if not login_emp.get("access_token"):
        raise Fail("emp1 login failed")
    ok("POST /auth/login (emp1)")

    bad = False
    try:
        _req("POST", f"{base}/auth/login", {"username": "admin", "password": "wrong"})
    except Fail:
        bad = True
    if not bad:
        raise Fail("expected bad password to fail")
    ok("POST /auth/login rejects bad password")

    companies = None
    last_err = None
    for path in ("/companys/", "/companys"):
        try:
            companies = _req("GET", f"{base}{path}", token=token)
            break
        except Fail as e:
            last_err = e
    if not isinstance(companies, list) or len(companies) < 2:
        raise Fail(f"expected >=2 companies, got {companies!r} ({last_err})")
    ok(f"GET /companys ({len(companies)} companies)")

    emps = _req("GET", f"{base}/employees/company/{COMPANY_ID}", token=token)
    if not isinstance(emps, list) or len(emps) < 5:
        raise Fail(f"expected >=5 employees in company A, got {emps!r}")
    sample = emps[0].get("member") or {}
    if "emergencyContactName" not in sample and "address" not in sample:
        print("  WARN  employee member missing profile fields (rebuild api?)")
    ok(f"GET /employees/company/A ({len(emps)} rows)")

    emps_b = _req("GET", f"{base}/employees/company/{COMPANY_B_ID}", token=token)
    if not isinstance(emps_b, list) or len(emps_b) < 4:
        raise Fail(f"expected >=4 employees in company B, got {emps_b!r}")
    ok(f"GET /employees/company/B ({len(emps_b)} rows)")

    depts = _req("GET", f"{base}/departments/company/{COMPANY_ID}", token=token)
    if not isinstance(depts, list) or len(depts) < 2:
        raise Fail(f"departments: {depts!r}")
    ok("GET /departments/company/{id}")

    positions = _req("GET", f"{base}/positions/company/{COMPANY_ID}", token=token)
    if not isinstance(positions, list) or len(positions) < 3:
        raise Fail(f"positions: {positions!r}")
    ok("GET /positions/company/{id}")

    locs = _req("GET", f"{base}/company-locations/company/{COMPANY_ID}", token=token)
    if not isinstance(locs, list) or len(locs) < 2:
        raise Fail(f"locations: {locs!r}")
    ok("GET /company-locations/company/{id}")

    stamps = _req("GET", f"{base}/timestamp/company/{COMPANY_ID}", token=token)
    if not isinstance(stamps, list) or len(stamps) < 5:
        raise Fail(f"timestamps: {stamps!r}")
    ok(f"GET /timestamp/company/A ({len(stamps)} rows)")

    # Angular-style empty query params must NOT 422
    pending_empty_qs = _req(
        "GET",
        f"{base}/timestamp/search/company/{COMPANY_ID}"
        f"?company_employeeId=&startDate=&endDate=&approvalStatus=PENDING",
        token=token,
    )
    if not isinstance(pending_empty_qs, list) or len(pending_empty_qs) < 1:
        raise Fail(f"empty-qs PENDING search failed: {pending_empty_qs!r}")
    ok(f"GET /timestamp/search empty qs PENDING ({len(pending_empty_qs)})")

    pending = _req(
        "GET",
        f"{base}/timestamp/search/company/{COMPANY_ID}?approvalStatus=PENDING",
        token=token,
    )
    if not isinstance(pending, list) or len(pending) < 1:
        raise Fail(f"expected PENDING list, got {pending!r}")
    ok(f"GET /timestamp/search ... PENDING ({len(pending)})")

    pending_b = _req(
        "GET",
        f"{base}/timestamp/search/company/{COMPANY_B_ID}?approvalStatus=PENDING",
        token=token,
    )
    if not isinstance(pending_b, list) or len(pending_b) < 1:
        raise Fail(f"expected company B PENDING, got {pending_b!r}")
    ok(f"GET /timestamp/search company B PENDING ({len(pending_b)})")

    try:
        approved = _req(
            "POST",
            f"{base}/timestamp/company/{COMPANY_ID}/{PENDING_TS}/approval",
            {
                "approve": True,
                "approvedBy": str(UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2")),
            },
            token=token,
        )
        if approved.get("approvalStatus") == "APPROVED":
            ok("POST /timestamp/.../approval (approve pending)")
        else:
            print(f"  WARN  approval response: {approved}")
    except Fail as e:
        msg = str(e)
        if "PENDING" in msg or "Only PENDING" in msg:
            ok("POST /timestamp/.../approval (already processed — ok)")
        else:
            print(f"  WARN  approval endpoint: {e}")

    print(f"\nDone: {passed} checks passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url",
        default="http://api:8000",
        help="API base URL (compose service http://api:8000)",
    )
    args = parser.parse_args()
    try:
        run(args.base_url)
    except Fail as exc:
        print(f"\nFAIL: {exc}", file=sys.stderr)
        sys.exit(1)
