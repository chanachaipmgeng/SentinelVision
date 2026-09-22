#!/usr/bin/env python3
"""Poll GET /face/queue-stats while a kiosk load test is running.

Run in a second terminal alongside kiosk_load.py. Credentials from env:
  KIOSK_LOAD_USER
  KIOSK_LOAD_PASSWORD
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from pathlib import Path
from typing import Any, Optional

import httpx

DEFAULT_BASE = "http://localhost:8880"


class Fail(Exception):
    pass


def require_creds() -> tuple[str, str]:
    user = os.environ.get("KIOSK_LOAD_USER", "").strip()
    password = os.environ.get("KIOSK_LOAD_PASSWORD", "").strip()
    if not user or not password:
        raise Fail(
            "Set KIOSK_LOAD_USER and KIOSK_LOAD_PASSWORD "
            "(demo local: admin / Password123! after seed)"
        )
    return user, password


def login(base_url: str, user: str, password: str) -> str:
    url = f"{base_url.rstrip('/')}/auth/login"
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(url, json={"username": user, "password": password})
        if resp.status_code != 200:
            raise Fail(f"login failed HTTP {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        token = data.get("access_token") or data.get("accessToken")
        if not token:
            raise Fail(f"login response missing access_token: {data}")
        return str(token)


def fetch_stats(base_url: str, token: str) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/face/queue-stats"
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(url, headers=headers)
        if resp.status_code == 401:
            raise Fail("token expired (401)")
        if resp.status_code != 200:
            raise Fail(f"queue-stats HTTP {resp.status_code}: {resp.text[:300]}")
        return resp.json()


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def main() -> int:
    parser = argparse.ArgumentParser(description="Poll /face/queue-stats")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("KIOSK_LOAD_BASE_URL", DEFAULT_BASE),
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Seconds between polls (default 1)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=0.0,
        help="Stop after N seconds (0 = until Ctrl+C)",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Append rows to a CSV file",
    )
    args = parser.parse_args()

    csv_fh = None
    try:
        user, password = require_creds()
        token = login(args.base_url, user, password)
        print(f"Polling {args.base_url.rstrip('/')}/face/queue-stats every {args.interval}s")
        print(f"{'ts':>12}  {'pending':>7}  {'active':>6}  {'completed':>9}  "
              f"{'delta/s':>7}  devices / source")
        print("-" * 78)

        csv_writer: Optional[csv.DictWriter] = None
        if args.csv:
            args.csv.parent.mkdir(parents=True, exist_ok=True)
            new_file = not args.csv.exists()
            csv_fh = args.csv.open("a", newline="", encoding="utf-8")
            csv_writer = csv.DictWriter(
                csv_fh,
                fieldnames=[
                    "ts",
                    "pending",
                    "active",
                    "completed",
                    "throughput_per_s",
                    "workers",
                    "devices",
                    "source",
                ],
            )
            if new_file:
                csv_writer.writeheader()

        prev_completed: Optional[int] = None
        prev_ts: Optional[float] = None
        started = time.monotonic()

        while True:
            if args.duration > 0 and (time.monotonic() - started) >= args.duration:
                break
            try:
                stats = fetch_stats(args.base_url, token)
            except Fail as exc:
                if "401" in str(exc):
                    token = login(args.base_url, user, password)
                    stats = fetch_stats(args.base_url, token)
                else:
                    raise

            now = time.time()
            pending = as_int(stats.get("pending"))
            if pending == 0 and isinstance(stats.get("pendingByCompany"), dict):
                pending = sum(as_int(v) for v in stats["pendingByCompany"].values())
            active = as_int(stats.get("active"))
            completed = as_int(stats.get("completed"))
            workers = stats.get("workers", "")
            devices = stats.get("devices") or []
            source = stats.get("source") or "local"

            throughput = 0.0
            if prev_completed is not None and prev_ts is not None:
                dt = max(now - prev_ts, 1e-6)
                throughput = (completed - prev_completed) / dt
            prev_completed = completed
            prev_ts = now

            device_s = ",".join(str(d) for d in devices) if devices else "-"
            print(
                f"{now:12.1f}  {pending:7d}  {active:6d}  {completed:9d}  "
                f"{throughput:7.1f}  {device_s}  [{source}]"
            )

            if csv_writer:
                csv_writer.writerow(
                    {
                        "ts": f"{now:.3f}",
                        "pending": pending,
                        "active": active,
                        "completed": completed,
                        "throughput_per_s": f"{throughput:.2f}",
                        "workers": workers,
                        "devices": device_s,
                        "source": source,
                    }
                )
                csv_fh.flush()

            time.sleep(max(0.1, args.interval))

        return 0
    except Fail as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nStopped")
        return 0
    finally:
        try:
            if csv_fh:
                csv_fh.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
