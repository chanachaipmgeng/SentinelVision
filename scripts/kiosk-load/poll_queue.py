#!/usr/bin/env python3
"""Poll GET /face/queue-stats while a kiosk load test is running.

Optionally samples nvidia-smi + docker stats so capacity reports can show
whether the bottleneck is GPU SM% or API container CPU (GIL).

Credentials from env:
  KIOSK_LOAD_USER
  KIOSK_LOAD_PASSWORD
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional

import httpx

DEFAULT_BASE = "http://localhost:8880"
DEFAULT_API_CONTAINER = os.environ.get("KIOSK_LOAD_API_CONTAINER", "dpu-api")


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


def _run(cmd: list[str], timeout: float = 8.0) -> str:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if result.returncode != 0:
            return ""
        return result.stdout or ""
    except Exception:
        return ""


def sample_nvidia() -> dict[str, Optional[float]]:
    """Return gpu0_sm, gpu1_sm, gpu0_mem_pct, gpu1_mem_pct (utilization %)."""
    out = _run(
        [
            "nvidia-smi",
            "--query-gpu=index,utilization.gpu,utilization.memory",
            "--format=csv,noheader,nounits",
        ]
    )
    stats: dict[str, Optional[float]] = {
        "gpu0_sm": None,
        "gpu1_sm": None,
        "gpu0_mem_pct": None,
        "gpu1_mem_pct": None,
    }
    if not out.strip():
        return stats
    for line in out.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 3:
            continue
        try:
            idx = int(parts[0])
            sm = float(parts[1])
            mem = float(parts[2])
        except ValueError:
            continue
        if idx == 0:
            stats["gpu0_sm"] = sm
            stats["gpu0_mem_pct"] = mem
        elif idx == 1:
            stats["gpu1_sm"] = sm
            stats["gpu1_mem_pct"] = mem
    return stats


def sample_docker_cpu(containers: list[str]) -> Optional[float]:
    """Sum CPU% across named containers (docker stats --no-stream)."""
    names = [c for c in containers if c]
    if not names:
        return None
    # Prefer sudo-less docker; callers on the server may wrap with sudo.
    docker_bin = os.environ.get("DOCKER_BIN", "docker")
    out = _run(
        [docker_bin, "stats", "--no-stream", "--format", "{{.Name}} {{.CPUPerc}}", *names],
        timeout=12.0,
    )
    if not out.strip():
        # Retry without explicit names (filter ourselves) when container list is wrong.
        out = _run(
            [docker_bin, "stats", "--no-stream", "--format", "{{.Name}} {{.CPUPerc}}"],
            timeout=12.0,
        )
    total = 0.0
    found = 0
    want = set(names)
    for line in out.strip().splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        name, perc = parts[0], parts[1]
        if want and name not in want and not any(name.endswith(w) or w in name for w in want):
            continue
        m = re.search(r"([\d.]+)", perc)
        if not m:
            continue
        total += float(m.group(1))
        found += 1
    if found == 0:
        return None
    return total


def main() -> int:
    parser = argparse.ArgumentParser(description="Poll /face/queue-stats + host metrics")
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
    parser.add_argument(
        "--host-metrics",
        action="store_true",
        help="Also sample nvidia-smi + docker stats each tick",
    )
    parser.add_argument(
        "--api-container",
        default=DEFAULT_API_CONTAINER,
        help=(
            "Comma-separated docker container names for CPU%% "
            f"(default {DEFAULT_API_CONTAINER}; dual-GPU: dpu-api,dpu-api-gpu1)"
        ),
    )
    args = parser.parse_args()
    containers = [c.strip() for c in str(args.api_container).split(",") if c.strip()]

    csv_fh = None
    try:
        user, password = require_creds()
        token = login(args.base_url, user, password)
        print(f"Polling {args.base_url.rstrip('/')}/face/queue-stats every {args.interval}s")
        hdr = (
            f"{'ts':>12}  {'pending':>7}  {'active':>6}  {'completed':>9}  "
            f"{'delta/s':>7}"
        )
        if args.host_metrics:
            hdr += f"  {'apiCPU%':>8}  {'gpu0':>5}  {'gpu1':>5}"
        hdr += "  devices / source"
        print(hdr)
        print("-" * len(hdr))

        fieldnames = [
            "ts",
            "pending",
            "active",
            "completed",
            "throughput_per_s",
            "workers",
            "devices",
            "source",
            "api_cpu_pct",
            "gpu0_sm",
            "gpu1_sm",
            "gpu0_mem_pct",
            "gpu1_mem_pct",
        ]
        csv_writer: Optional[csv.DictWriter] = None
        if args.csv:
            args.csv.parent.mkdir(parents=True, exist_ok=True)
            new_file = not args.csv.exists()
            csv_fh = args.csv.open("a", newline="", encoding="utf-8")
            csv_writer = csv.DictWriter(csv_fh, fieldnames=fieldnames)
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

            api_cpu: Optional[float] = None
            gpu = {
                "gpu0_sm": None,
                "gpu1_sm": None,
                "gpu0_mem_pct": None,
                "gpu1_mem_pct": None,
            }
            if args.host_metrics:
                api_cpu = sample_docker_cpu(containers)
                gpu = sample_nvidia()

            device_s = ",".join(str(d) for d in devices) if devices else "-"
            by_kind = stats.get("pendingByKind") or {}
            kind_s = ""
            if by_kind:
                kind_s = " " + ",".join(
                    f"{k}:{by_kind[k]}" for k in sorted(by_kind) if by_kind[k]
                )
            line = (
                f"{now:12.1f}  {pending:7d}  {active:6d}  {completed:9d}  "
                f"{throughput:7.1f}"
            )
            if args.host_metrics:
                cpu_s = f"{api_cpu:8.1f}" if api_cpu is not None else f"{'—':>8}"
                g0 = f"{gpu['gpu0_sm']:5.0f}" if gpu["gpu0_sm"] is not None else f"{'—':>5}"
                g1 = f"{gpu['gpu1_sm']:5.0f}" if gpu["gpu1_sm"] is not None else f"{'—':>5}"
                line += f"  {cpu_s}  {g0}  {g1}"
            line += f"  {device_s}  [{source}]{kind_s}"
            print(line)

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
                        "api_cpu_pct": "" if api_cpu is None else f"{api_cpu:.2f}",
                        "gpu0_sm": "" if gpu["gpu0_sm"] is None else f"{gpu['gpu0_sm']:.1f}",
                        "gpu1_sm": "" if gpu["gpu1_sm"] is None else f"{gpu['gpu1_sm']:.1f}",
                        "gpu0_mem_pct": (
                            ""
                            if gpu["gpu0_mem_pct"] is None
                            else f"{gpu['gpu0_mem_pct']:.1f}"
                        ),
                        "gpu1_mem_pct": (
                            ""
                            if gpu["gpu1_mem_pct"] is None
                            else f"{gpu['gpu1_mem_pct']:.1f}"
                        ),
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
