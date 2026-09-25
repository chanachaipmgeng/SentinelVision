#!/usr/bin/env python3
"""Hunt max kiosks under p95 ≤ 1000 ms (also report 550 ms).

Runs rush ×1/×3 at full-rate (90 ms) and gated (600 ms), writes
scripts/kiosk-load/.cache/summary-ceiling-1s.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / ".cache"
PY = ROOT / ".venv" / "Scripts" / "python.exe"
if not PY.is_file():
    PY = Path(sys.executable)
KIOSK = ROOT / "kiosk_load.py"

SLO_DROP = 0.05
SLO_TARGET = 550.0
SLO_ACCEPT = 1000.0

# (name, faces, detect_ms, hold_s, kiosk_steps)
# Pass A: high ladder (historical ceilings). Pass B: low ladder if A finds no PASS@1000.
SERIES_HIGH = [
    ("rush_x3_full", 3, 90.0, 60.0, [24, 32, 40, 48]),
    ("rush_x1_full", 1, 90.0, 60.0, [32, 40, 48, 56]),
    ("rush_x3_gated", 3, 600.0, 90.0, [32, 40, 48, 56]),
    ("rush_x1_gated", 1, 600.0, 90.0, [48, 56, 64, 72]),
]
SERIES_LOW = [
    ("rush_x3_full_low", 3, 90.0, 45.0, [8, 12, 16, 20, 24]),
    ("rush_x1_full_low", 1, 90.0, 45.0, [12, 16, 20, 24, 32]),
    ("rush_x3_gated_low", 3, 600.0, 60.0, [12, 16, 20, 24, 32]),
    ("rush_x1_gated_low", 1, 600.0, 60.0, [16, 24, 32, 40, 48]),
]
SERIES = SERIES_HIGH


def load_steps(path: Path) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    if not path.is_file():
        return steps
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("event") == "step_summary":
            steps.append(row)
    return steps


def parse_kiosks(label: str) -> int | None:
    m = re.search(r"kiosks=(\d+)", label or "")
    return int(m.group(1)) if m else None


def verdict_ms(p95: float | None, drop: float, limit: float) -> str:
    if p95 is None:
        return "n/a"
    if p95 <= limit and drop <= SLO_DROP:
        return "PASS"
    if p95 <= limit * 1.15 and drop <= 0.10:
        return "MARGIN"
    return "FAIL"


def summarize_step(row: dict[str, Any]) -> dict[str, Any]:
    det = row.get("detect") or {}
    ident = row.get("identify") or {}
    chk = row.get("checkin") or {}
    drop = float(det.get("dropped_rate") or 0)
    det_p95 = det.get("p95_ms")
    id_p95 = ident.get("p95_ms")
    # Decision metric: worst of detect/identify p95 (check-in tracked separately)
    candidates = [x for x in (det_p95, id_p95) if x is not None]
    worst = max(candidates) if candidates else None
    k = parse_kiosks(str(row.get("step") or ""))
    return {
        "kiosks": k,
        "step": row.get("step"),
        "detect_p95_ms": det_p95,
        "identify_p95_ms": id_p95,
        "checkin_p95_ms": chk.get("p95_ms"),
        "drop_rate": round(drop, 4),
        "worst_p95_ms": worst,
        "pass_550": verdict_ms(worst, drop, SLO_TARGET) == "PASS",
        "pass_1000": verdict_ms(worst, drop, SLO_ACCEPT) == "PASS",
        "verdict_550": verdict_ms(worst, drop, SLO_TARGET),
        "verdict_1000": verdict_ms(worst, drop, SLO_ACCEPT),
        "face_core_down": row.get("face_core_down") or 0,
        "throughput_detect_per_s": row.get("throughput_detect_per_s"),
    }


def max_pass(steps: list[dict[str, Any]], key: str) -> int | None:
    ok = [s["kiosks"] for s in steps if s.get(key) and s.get("kiosks") is not None]
    return max(ok) if ok else None


def run_series(
    *,
    name: str,
    faces: int,
    detect_ms: float,
    hold_s: float,
    kiosks: list[int],
    base_url: str,
    company_id: str,
    member_id: str,
    lat: str,
    lon: str,
) -> dict[str, Any]:
    jsonl = CACHE / f"results-ceiling-1s-{name}.jsonl"
    if jsonl.exists():
        jsonl.unlink()
    cmd = [
        str(PY),
        str(KIOSK),
        "--base-url",
        base_url,
        "--company-id",
        company_id,
        "--member-id",
        member_id,
        "--lat",
        lat,
        "--lon",
        lon,
        "--profile",
        "rush",
        "--faces-per-kiosk",
        str(faces),
        "--kiosks",
        ",".join(str(k) for k in kiosks),
        "--hold",
        str(hold_s),
        "--detect-interval-ms",
        str(detect_ms),
        "--jsonl",
        str(jsonl),
    ]
    print("RUN:", " ".join(cmd), flush=True)
    t0 = time.time()
    rc = subprocess.call(cmd, env=os.environ.copy())
    elapsed = round(time.time() - t0, 1)
    steps = [summarize_step(s) for s in load_steps(jsonl)]
    # Early-stop hint in summary: first FAIL@1000
    first_fail = next((s["kiosks"] for s in steps if s.get("verdict_1000") == "FAIL"), None)
    return {
        "name": name,
        "faces_per_kiosk": faces,
        "detect_interval_ms": detect_ms,
        "hold_s": hold_s,
        "kiosks_planned": kiosks,
        "exit_code": rc,
        "elapsed_s": elapsed,
        "jsonl": str(jsonl),
        "steps": steps,
        "max_pass_550": max_pass(steps, "pass_550"),
        "max_pass_1000": max_pass(steps, "pass_1000"),
        "first_fail_1000": first_fail,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base-url", default=os.environ.get("KIOSK_LOAD_BASE_URL", "http://10.50.0.117:8880"))
    p.add_argument("--company-id", default=os.environ.get("KIOSK_LOAD_COMPANY_ID", "11111111-1111-1111-1111-111111111112"))
    p.add_argument("--member-id", default=os.environ.get("KIOSK_LOAD_MEMBER_ID", "66c8402f-4538-4479-ae54-946582d41098"))
    p.add_argument("--lat", default="13.877239958879965")
    p.add_argument("--lon", default="100.51154729391773")
    p.add_argument(
        "--ladder",
        choices=("high", "low", "all"),
        default="high",
        help="high=historical ceilings; low=find floor when host is slower; all=both",
    )
    p.add_argument(
        "--series",
        default="all",
        help="Comma names or 'all'",
    )
    args = p.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)

    pool = []
    if args.ladder in ("high", "all"):
        pool.extend(SERIES_HIGH)
    if args.ladder in ("low", "all"):
        pool.extend(SERIES_LOW)

    wanted = {s.strip() for s in args.series.split(",") if s.strip()}
    series_defs = pool if "all" in wanted else [s for s in pool if s[0] in wanted]
    if not series_defs:
        raise SystemExit(f"No series matched: ladder={args.ladder} series={args.series}")

    out: dict[str, Any] = {
        "ts": time.time(),
        "base_url": args.base_url,
        "slo_target_ms": SLO_TARGET,
        "slo_acceptable_ms": SLO_ACCEPT,
        "slo_drop": SLO_DROP,
        "metric": "worst(detect_p95, identify_p95)",
        "series": [],
    }

    for name, faces, detect_ms, hold_s, kiosks in series_defs:
        result = run_series(
            name=name,
            faces=faces,
            detect_ms=detect_ms,
            hold_s=hold_s,
            kiosks=kiosks,
            base_url=args.base_url,
            company_id=args.company_id,
            member_id=args.member_id,
            lat=args.lat,
            lon=args.lon,
        )
        out["series"].append(result)
        print(
            f"== {name}: max@550={result['max_pass_550']} "
            f"max@1000={result['max_pass_1000']} "
            f"first_fail_1000={result['first_fail_1000']}",
            flush=True,
        )

    ceilings = {
        s["name"]: {
            "max_pass_550": s["max_pass_550"],
            "max_pass_1000": s["max_pass_1000"],
            "first_fail_1000": s["first_fail_1000"],
        }
        for s in out["series"]
    }
    out["ceilings"] = ceilings
    out_path = CACHE / "summary-ceiling-1s.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(ceilings, indent=2, ensure_ascii=False), flush=True)
    print(f"Wrote {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
