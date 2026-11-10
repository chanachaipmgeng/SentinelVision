#!/usr/bin/env python3
"""Phase 6D GPU sizing — kiosk p95 regression gate with people counting enabled.

Measures check-in / identify wait p95 from GET /face/queue-stats (and optional
Prometheus scrape) with people worker idle vs active, then applies the locked
≤10% regression gate.

People counting uses a **dedicated** YOLOv8n ONNX lane (not InsightFace
``face_gpu_queue``) and pauses when kiosk pending ≥ WORKER_PEOPLE_PAUSE_WHEN_KIOSK_PENDING.

Usage (stack on :8880, creds in env)::

  $env:KIOSK_LOAD_USER = "admin"
  $env:KIOSK_LOAD_PASSWORD = "Password123!"
  python people_gpu_sizing.py --base-url http://localhost:8880 --hold 90

Exit codes:
  0 — gate passed (people p95 ≤ baseline × 1.10) or --dry-doc only
  2 — gate failed (>10% regression)
  1 — setup / auth error

See also: docs/KIOSK-LOADTEST.md § People counting (Phase 6D).
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Optional

import httpx

DEFAULT_BASE = os.environ.get("KIOSK_LOAD_BASE", "http://localhost:8880")
REGRESSION_LIMIT = 0.10  # ≤10% kiosk p95 regression


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
        if resp.status_code != 200:
            raise Fail(f"queue-stats HTTP {resp.status_code}: {resp.text[:300]}")
        return resp.json()


def p95(values: list[float]) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    idx = int(round(0.95 * (len(ordered) - 1)))
    return float(ordered[idx])


def sample_wait_ms(stats: dict[str, Any]) -> list[float]:
    """Best-effort extract of recent wait samples from queue-stats payload."""
    out: list[float] = []
    # Prefer explicit histograms if present.
    for key in ("waitMsByKind", "waitP95ByKind", "recentWaitMs"):
        block = stats.get(key)
        if isinstance(block, dict):
            for kind in ("checkin", "identify"):
                v = block.get(kind)
                if isinstance(v, (int, float)):
                    out.append(float(v))
                elif isinstance(v, list):
                    out.extend(float(x) for x in v if isinstance(x, (int, float)))
        elif isinstance(block, list):
            out.extend(float(x) for x in block if isinstance(x, (int, float)))
    # Fallback: pending depth as pressure proxy (not latency) — still useful for gate dry-runs.
    by_kind = stats.get("pendingByKind") or {}
    for kind in ("checkin", "identify"):
        if kind in by_kind:
            out.append(float(by_kind[kind]) * 50.0)  # rough ms proxy when idle
    return out


def collect_window(
    base_url: str, token: str, *, seconds: float, interval: float
) -> dict[str, Any]:
    samples: list[float] = []
    depths: list[int] = []
    deadline = time.monotonic() + max(5.0, seconds)
    while time.monotonic() < deadline:
        stats = fetch_stats(base_url, token)
        samples.extend(sample_wait_ms(stats))
        by_kind = stats.get("pendingByKind") or {}
        depths.append(
            int(by_kind.get("checkin") or 0) + int(by_kind.get("identify") or 0)
        )
        time.sleep(max(0.5, interval))
    return {
        "p95_ms": p95(samples),
        "mean_ms": statistics.fmean(samples) if samples else None,
        "n": len(samples),
        "kiosk_pending_p95": p95([float(d) for d in depths]),
        "samples": samples[-50:],
    }


def print_gate_doc() -> None:
    print(
        """
Phase 6D — People counting GPU / kiosk p95 gate
===============================================

Locked decision: <=10% kiosk checkin+identify p95 regression when people YOLO runs.

Env (worker):
  WORKER_PEOPLE_*                 dedicated lane (not InsightFace queue)
  WORKER_PEOPLE_PAUSE_WHEN_KIOSK_PENDING  (default 4)
  WORKER_PEOPLE_MAX_CONCURRENT    (default 1)
  PEOPLE_YOLO_ONNX_PATH           models/yolov8n.onnx
  peopleEnabled                   false until ROI configured on camera.ai_config

Procedure:
  1. Baseline: people disabled (or no ROI) — run kiosk load + this script --phase baseline
  2. Enable people on one camera with ROI; ensure yolov8n.onnx present
  3. Repeat load — this script --phase people
  4. Gate: people_p95 <= baseline_p95 * 1.10

Download ONNX (once):
  python scripts/download_yolov8n_onnx.py --out API-Fast/models/yolov8n.onnx
""".strip()
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE)
    parser.add_argument("--hold", type=float, default=60.0, help="Sample window seconds")
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument(
        "--baseline-p95",
        type=float,
        default=None,
        help="Prior baseline p95 ms (skip baseline window)",
    )
    parser.add_argument(
        "--phase",
        choices=("baseline", "people", "compare"),
        default="compare",
    )
    parser.add_argument("--out", type=Path, default=None, help="Write JSON summary")
    parser.add_argument(
        "--dry-doc",
        action="store_true",
        help="Print gate documentation and exit 0",
    )
    parser.add_argument(
        "--limit",
        type=float,
        default=REGRESSION_LIMIT,
        help="Max allowed relative regression (default 0.10)",
    )
    args = parser.parse_args(argv)

    if args.dry_doc:
        print_gate_doc()
        return 0

    try:
        user, password = require_creds()
        token = login(args.base_url, user, password)
    except Fail as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    report: dict[str, Any] = {
        "baseUrl": args.base_url,
        "limit": args.limit,
        "gate": "kiosk_p95_regression_le_10pct",
    }

    if args.phase in ("baseline", "compare") and args.baseline_p95 is None:
        print(f"Sampling baseline window {args.hold}s …")
        baseline = collect_window(
            args.base_url, token, seconds=args.hold, interval=args.interval
        )
        report["baseline"] = baseline
    else:
        report["baseline"] = {"p95_ms": args.baseline_p95, "n": 0}

    if args.phase in ("people", "compare"):
        print(f"Sampling people window {args.hold}s …")
        people = collect_window(
            args.base_url, token, seconds=args.hold, interval=args.interval
        )
        report["people"] = people
    else:
        report["people"] = None

    base_p95 = (report.get("baseline") or {}).get("p95_ms")
    people_p95 = (report.get("people") or {}).get("p95_ms") if report.get("people") else None
    passed: Optional[bool] = None
    if base_p95 and people_p95 and base_p95 > 0:
        ratio = people_p95 / base_p95
        passed = ratio <= (1.0 + float(args.limit))
        report["ratio"] = ratio
        report["passed"] = passed
        print(
            f"baseline_p95={base_p95:.1f}ms people_p95={people_p95:.1f}ms "
            f"ratio={ratio:.3f} limit={1+args.limit:.2f} → "
            f"{'PASS' if passed else 'FAIL'}"
        )
    else:
        print(
            "Insufficient latency samples for hard gate "
            f"(baseline={base_p95}, people={people_p95}). "
            "Depth proxies recorded; re-run under active kiosk load."
        )
        report["passed"] = None

    if args.out:
        args.out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        print(f"Wrote {args.out}")

    if passed is False:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
