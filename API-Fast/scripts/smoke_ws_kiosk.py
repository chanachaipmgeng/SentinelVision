#!/usr/bin/env python3
"""Smoke WebSocket kiosk /face/ws/kiosk (Face Core BFF mode)."""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import sys
import time

import httpx
import websockets

COMPANY_A = "11111111-1111-1111-1111-111111111111"
MEMBER_EMP1 = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4"
FACE_URL = (
    "https://raw.githubusercontent.com/deepinsight/insightface/master/"
    "python-package/insightface/data/images/t1.jpg"
)
LAT, LON = 13.7563, 100.5018


class Fail(Exception):
    pass


def ok(msg: str) -> None:
    print(f"  PASS  {msg}")


async def recv_until(
    ws,
    *,
    want_type: str | None = None,
    want_request_id: str | None = None,
    timeout: float = 120.0,
) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        raw = await asyncio.wait_for(ws.recv(), timeout=max(0.1, remaining))
        msg = json.loads(raw)
        if want_type and msg.get("type") != want_type:
            if msg.get("type") == "error":
                raise Fail(f"unexpected error while waiting for {want_type}: {msg}")
            continue
        if want_request_id and msg.get("requestId") != want_request_id:
            continue
        return msg
    raise Fail(f"timeout waiting for type={want_type!r} requestId={want_request_id!r}")


async def run_smoke(ws_url: str) -> None:
    print(f"WS kiosk smoke -> {ws_url}\n")

    img = httpx.get(FACE_URL, timeout=60).content
    b64 = base64.b64encode(img).decode("ascii")
    ok(f"sample face ({len(img)} bytes)")

    async with websockets.connect(ws_url, open_timeout=30) as ws:
        ready = json.loads(await ws.recv())
        if ready.get("type") != "ready":
            raise Fail(f"expected ready, got {ready}")
        if not ready.get("faceCoreEnabled"):
            raise Fail("expected faceCoreEnabled=true")
        ok("WS ready (Face Core enabled)")

        await ws.send(
            json.dumps(
                {
                    "type": "session",
                    "companyId": COMPANY_A,
                    "latitude": LAT,
                    "longitude": LON,
                }
            )
        )
        session_ok = json.loads(await ws.recv())
        if session_ok.get("type") != "session_ok":
            raise Fail(f"session failed: {session_ok}")
        if session_ok.get("companyCode") != COMPANY_A:
            raise Fail(f"missing companyCode mapping: {session_ok}")
        ok("session → session_ok + companyCode")

        detect_id = "smoke-detect-1"
        await ws.send(
            json.dumps({"type": "detect", "requestId": detect_id, "image": b64})
        )
        detected = await recv_until(ws, want_type="detected", want_request_id=detect_id)
        if not detected.get("faces"):
            raise Fail(f"detect returned no faces: {detected}")
        ok(f"detect → {len(detected['faces'])} face box(es)")

        identify_id = "smoke-identify-1"
        await ws.send(
            json.dumps(
                {
                    "type": "identify",
                    "trackId": 1,
                    "requestId": identify_id,
                    "image": b64,
                }
            )
        )
        identified = await recv_until(
            ws, want_type="identified", want_request_id=identify_id
        )
        if identified.get("memberId") != MEMBER_EMP1:
            raise Fail(f"identify wrong member: {identified}")
        ok(f"identify → {identified.get('member', {}).get('fullName')}")

        checkin_id = "smoke-checkin-1"
        await ws.send(
            json.dumps(
                {
                    "type": "checkin",
                    "trackId": 1,
                    "requestId": checkin_id,
                    "images": [b64, b64],
                    "latitude": LAT,
                    "longitude": LON,
                    "note": "WS kiosk smoke",
                }
            )
        )
        checked = await recv_until(
            ws, want_type="checked_in", want_request_id=checkin_id
        )
        if checked.get("memberId") != MEMBER_EMP1:
            raise Fail(f"checkin wrong member: {checked}")
        if not (checked.get("checkedIn") or checked.get("duplicate")):
            raise Fail(f"checkin neither saved nor deduped: {checked}")
        ok(
            f"checkin → checkedIn={checked.get('checkedIn')} "
            f"duplicate={checked.get('duplicate')}"
        )

        await ws.send(json.dumps({"type": "ping"}))
        pong = json.loads(await ws.recv())
        if pong.get("type") != "pong":
            raise Fail(f"ping failed: {pong}")
        ok("ping → pong")

    print("\nAll WS kiosk smoke checks passed.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke /face/ws/kiosk")
    parser.add_argument(
        "--ws-url",
        default="ws://api:8000/face/ws/kiosk",
        help="WebSocket URL (default: inside compose network)",
    )
    args = parser.parse_args()
    try:
        asyncio.run(run_smoke(args.ws_url))
        return 0
    except Fail as exc:
        print(f"\nFAIL  {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
