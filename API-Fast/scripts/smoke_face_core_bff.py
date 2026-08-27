#!/usr/bin/env python3
"""Smoke Face Core BFF flows via DPU /face/* (run inside compose network)."""

from __future__ import annotations

import json
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

import httpx

BASE = "http://api:8000"
COMPANY_A = "11111111-1111-1111-1111-111111111111"
COMPANY_B = "11111111-1111-1111-1111-111111111112"
MEMBER_EMP1 = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4"  # emp1 / Company A
MEMBER_STAFF1 = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb3"  # staff1 / Company B
FACE_URL = "https://raw.githubusercontent.com/deepinsight/insightface/master/python-package/insightface/data/images/t1.jpg"
# HQ Bangkok approx (inside demo geofence)
LAT, LON = 13.7563, 100.5018


class Fail(Exception):
    pass


def ok(msg: str) -> None:
    print(f"  PASS  {msg}")


def get_json(path: str) -> dict:
    with urllib.request.urlopen(f"{BASE}{path}", timeout=60) as resp:
        return json.loads(resp.read().decode())


def post_multipart(path: str, fields: dict, files: list[tuple[str, bytes]]) -> dict:
    boundary = "----smokeboundary"
    body = bytearray()
    for key, val in fields.items():
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode())
        body.extend(f"{val}\r\n".encode())
    for field_name, content in files:
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(
            f'Content-Disposition: form-data; name="{field_name}"; filename="face.jpg"\r\n'.encode()
        )
        body.extend(b"Content-Type: image/jpeg\r\n\r\n")
        body.extend(content)
        body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode())
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise Fail(f"POST {path} -> {e.code}: {e.read().decode()[:300]}") from e


def main() -> int:
    print(f"Face Core BFF smoke -> {BASE}\n")

    root = get_json("/")
    if "Face Core BFF" not in str(root.get("face", "")):
        raise Fail(f"expected Face Core BFF mode, got: {root}")
    ok("GET / (Face Core BFF mode)")

    stats = get_json("/face/queue-stats")
    if stats.get("source") != "face-core":
        raise Fail(f"queue-stats not from face-core: {stats}")
    ok("GET /face/queue-stats (proxied to Face Core)")

    img = httpx.get(FACE_URL, timeout=60).content
    if len(img) < 1000:
        raise Fail("failed to download sample face image")
    ok(f"Downloaded sample face ({len(img)} bytes)")

    enrolled = post_multipart(
        f"/face/members/{MEMBER_EMP1}/add-face",
        {},
        [("file", img)],
    )
    face_id = enrolled.get("faceEncodingId")
    if not face_id:
        raise Fail(f"add-face missing faceEncodingId: {enrolled}")
    ok(f"POST add-face emp1 -> faceEncodingId={face_id}")

    identified = post_multipart(
        "/face/members/identify",
        {"companyId": COMPANY_A},
        [("file", img)],
    )
    if not identified.get("matched") or identified.get("memberId") != MEMBER_EMP1:
        raise Fail(f"identify company A failed: {identified}")
    img_url = identified.get("enrolledImageUrl") or ""
    if not img_url.startswith("/face/enrolled-images/"):
        raise Fail(f"identify missing BFF proxy enrolledImageUrl: {identified}")
    ok(f"POST identify company A -> {identified.get('member', {}).get('fullName')}")

    proxy_path = img_url if img_url.startswith("/") else f"/{img_url}"
    with urllib.request.urlopen(f"{BASE}{proxy_path}", timeout=60) as resp:
        body = resp.read()
        ctype = resp.headers.get("Content-Type", "")
    if len(body) < 500 or "image" not in ctype:
        raise Fail(f"enrolled-image proxy failed: {len(body)} bytes, {ctype}")
    ok(f"GET enrolled-image proxy ({len(body)} bytes, {ctype})")

    # Cross-company isolation: same face should NOT match in company B
    try:
        post_multipart(
            "/face/members/identify",
            {"companyId": COMPANY_B},
            [("file", img)],
        )
        raise Fail("identify in company B should fail for company-A-only face")
    except Fail:
        ok("POST identify company B rejects company-A face (401)")

    checkin = post_multipart(
        "/face/members/check-in-walkby",
        {
            "companyId": COMPANY_A,
            "latitude": str(LAT),
            "longitude": str(LON),
            "note": "smoke BFF walkby",
        },
        [("files", img), ("files", img)],
    )
    if not checkin.get("checkedIn") and not checkin.get("duplicate"):
        raise Fail(f"walk-by check-in unexpected: {checkin}")
    ok(
        f"POST check-in-walkby -> checkedIn={checkin.get('checkedIn')} "
        f"duplicate={checkin.get('duplicate')}"
    )

    roster = get_json(f"/face/kiosk-attendance/{COMPANY_A}")
    if "checkedIn" not in roster:
        raise Fail(f"kiosk-attendance missing checkedIn: {roster}")
    ok(f"GET kiosk-attendance ({roster.get('summary', {}).get('checkedInCount', 0)} today)")

    verify = post_multipart(
        f"/face/members/{MEMBER_EMP1}/verify",
        {},
        [("file", img)],
    )
    if not verify.get("matched"):
        raise Fail(f"verify failed: {verify}")
    ok(f"POST verify emp1 -> confidencePercent={verify.get('confidencePercent')}")

    encodings = json.loads(
        urllib.request.urlopen(
            f"{BASE}/face/members/{MEMBER_EMP1}/encodings", timeout=60
        ).read().decode()
    )
    if not encodings:
        raise Fail("GET encodings empty")
    ok(f"GET encodings ({len(encodings)} face(s) from Face Core)")

    print(f"\nAll {9} Face Core BFF smoke checks passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as e:
        print(f"\nFAIL  {e}", file=sys.stderr)
        raise SystemExit(1)
