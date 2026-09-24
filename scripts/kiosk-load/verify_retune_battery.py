#!/usr/bin/env python3
"""Post-retune verification battery V1–V5 → summary-verify-battery.json."""
from __future__ import annotations

import argparse
import json
import os
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
SPIKE = ROOT / "spike_http_identify.py"
SOAK = ROOT / "gpu_soak.py"
PGVEC = ROOT / "pgvector_concurrency.py"
RUSH_SUM = ROOT / "rush_hour_capacity.py"


def run(cmd: list[str]) -> int:
    print("RUN:", " ".join(cmd), flush=True)
    return subprocess.call(cmd, env=os.environ.copy())


def summarize_identify_jsonl(path: Path, hold_s: float) -> dict[str, Any]:
    id_ok = 0
    id_lat: list[float] = []
    det_n = 0
    det_drop = 0
    if path.is_file():
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ev = r.get("event")
                if ev == "identified" and r.get("latency_ms") is not None:
                    id_ok += 1
                    id_lat.append(float(r["latency_ms"]))
                elif ev == "detected":
                    det_n += 1
                    if r.get("dropped"):
                        det_drop += 1

    def p95(vals: list[float]) -> float | None:
        if not vals:
            return None
        s = sorted(vals)
        return round(s[min(len(s) - 1, max(0, int(round(0.95 * (len(s) - 1)))))], 1)

    drop = (det_drop / det_n) if det_n else 0.0
    per_min = (id_ok / hold_s * 60.0) if hold_s > 0 else 0.0
    return {
        "identify_ok": id_ok,
        "identify_p95_ms": p95(id_lat),
        "drop_rate": round(drop, 4),
        "scans_per_min": round(per_min, 1),
        "slo_pass_550": (p95(id_lat) or 9999) <= 550 and drop <= 0.05,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base-url", default=os.environ.get("KIOSK_LOAD_BASE_URL", "http://10.50.0.117:8880"))
    p.add_argument("--company-id", default=os.environ.get("KIOSK_LOAD_COMPANY_ID", "11111111-1111-1111-1111-111111111112"))
    p.add_argument("--member-id", default=os.environ.get("KIOSK_LOAD_MEMBER_ID", "66c8402f-4538-4479-ae54-946582d41098"))
    p.add_argument("--lat", default="13.877239958879965")
    p.add_argument("--lon", default="100.51154729391773")
    p.add_argument("--skip-soak", action="store_true")
    p.add_argument("--skip-pgvector", action="store_true")
    p.add_argument("--out", type=Path, default=CACHE / "summary-verify-battery.json")
    args = p.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        "ts": time.time(),
        "base_url": args.base_url,
        "baseline_ref": {
            "v1_scans_per_min": 900,
            "v2_scans_per_min": 1139,
            "spike_502_at_50": 0,
            "spike_502_at_100": 9,
            "spike_peak_rps": 22.6,
            "pgvector_p95_at_250": 681,
        },
        "results": {},
        "verdict": {},
    }

    # V1
    j1 = CACHE / "results-verify-id-24.jsonl"
    run(
        [
            str(PY),
            str(KIOSK),
            "--base-url",
            args.base_url,
            "--company-id",
            args.company_id,
            "--member-id",
            args.member_id,
            "--lat",
            args.lat,
            "--lon",
            args.lon,
            "--profile",
            "identify",
            "--kiosks",
            "24",
            "--hold",
            "600",
            "--faces-per-kiosk",
            "1",
            "--detect-interval-ms",
            "600",
            "--jsonl",
            str(j1),
            "--prepare",
        ]
    )
    v1 = summarize_identify_jsonl(j1, 600.0)
    summary["results"]["V1_identify_24"] = v1

    # V2
    j2 = CACHE / "results-verify-id-32.jsonl"
    run(
        [
            str(PY),
            str(KIOSK),
            "--base-url",
            args.base_url,
            "--company-id",
            args.company_id,
            "--member-id",
            args.member_id,
            "--lat",
            args.lat,
            "--lon",
            args.lon,
            "--profile",
            "identify",
            "--kiosks",
            "32",
            "--hold",
            "600",
            "--faces-per-kiosk",
            "1",
            "--detect-interval-ms",
            "600",
            "--jsonl",
            str(j2),
        ]
    )
    v2 = summarize_identify_jsonl(j2, 600.0)
    summary["results"]["V2_identify_32"] = v2

    # V3 spike
    spike_out = CACHE / "summary-verify-spike.json"
    run(
        [
            str(PY),
            str(SPIKE),
            "--base-url",
            args.base_url,
            "--company-id",
            args.company_id,
            "--concurrency",
            "20,50,100",
            "--requests-per-step",
            "500",
            "--out",
            str(spike_out),
        ]
    )
    spike = json.loads(spike_out.read_text(encoding="utf-8")) if spike_out.is_file() else {}
    summary["results"]["V3_spike"] = spike

    # V4 soak 45 min
    if not args.skip_soak:
        soak_out = CACHE / "summary-verify-soak.json"
        soak_csv = CACHE / "verify-soak-metrics.csv"
        run(
            [
                str(PY),
                str(SOAK),
                "--base-url",
                args.base_url,
                "--company-id",
                args.company_id,
                "--member-id",
                args.member_id,
                "--kiosks",
                "24",
                "--chunk-hold",
                "600",
                "--total-hours",
                "0.75",
                "--out",
                str(soak_out),
                "--metrics-csv",
                str(soak_csv),
            ]
        )
        soak = json.loads(soak_out.read_text(encoding="utf-8")) if soak_out.is_file() else {}
        summary["results"]["V4_soak"] = {
            k: soak.get(k)
            for k in (
                "start_mem_pct_dpu_api",
                "end_mem_pct_dpu_api",
                "leak_suspect_gt20pct",
                "gpu0_sm_avg",
                "gpu1_sm_avg",
                "gpu_balance_note",
                "chunks",
            )
        }

    # V5 pgvector
    if not args.skip_pgvector:
        pg_out = CACHE / "summary-verify-pgvector.json"
        run(
            [
                str(PY),
                str(PGVEC),
                "--company-id",
                args.company_id,
                "--member-id",
                args.member_id,
                "--target-gallery",
                "20000",
                "--clients",
                "100,250",
                "--queries-per-client",
                "20",
                "--out",
                str(pg_out),
            ]
        )
        pg = json.loads(pg_out.read_text(encoding="utf-8")) if pg_out.is_file() else {}
        summary["results"]["V5_pgvector"] = pg

    # Verdicts
    ref = summary["baseline_ref"]
    v = summary["verdict"]
    v["V1_ok"] = bool(v1.get("slo_pass_550")) and (v1.get("scans_per_min") or 0) >= ref["v1_scans_per_min"] * 0.85
    v["V2_ok"] = bool(v2.get("slo_pass_550")) and (v2.get("scans_per_min") or 0) >= ref["v2_scans_per_min"] * 0.85
    steps = {s["concurrency"]: s for s in spike.get("steps", [])}
    s50 = steps.get(50, {})
    s100 = steps.get(100, {})
    peak = spike.get("peak_rps_ok") or 0
    v["V3_502_not_worse"] = (s50.get("http_502", 99) <= ref["spike_502_at_50"]) and (
        s100.get("http_502", 99) <= ref["spike_502_at_100"]
    )
    v["V3_rps_ok"] = peak >= ref["spike_peak_rps"] * 0.85
    v["V3_ok"] = bool(v["V3_502_not_worse"] and v["V3_rps_ok"])
    if "V4_soak" in summary["results"]:
        soak_r = summary["results"]["V4_soak"]
        fail_chunks = sum(1 for c in (soak_r.get("chunks") or []) if c.get("exit_code", 1) != 0)
        v["V4_ok"] = (not soak_r.get("leak_suspect_gt20pct")) and fail_chunks == 0
        v["V4_fail_chunks"] = fail_chunks
    if "V5_pgvector" in summary["results"]:
        reads = summary["results"]["V5_pgvector"].get("read_storm") or []
        p95_250 = next((r.get("p95_ms") for r in reads if r.get("clients") == 250), None)
        errs = sum(r.get("errors", 1) for r in reads)
        v["V5_ok"] = errs == 0 and p95_250 is not None and p95_250 <= ref["pgvector_p95_at_250"] * 1.15
        v["V5_p95_at_250"] = p95_250
    v["overall_ok"] = all(
        v.get(k)
        for k in ("V1_ok", "V2_ok", "V3_ok", "V4_ok", "V5_ok")
        if k in v
    )
    v["nginx_tune_keep"] = bool(v.get("V3_ok")) and bool(v.get("V1_ok")) and bool(v.get("V2_ok"))

    args.out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(v, ensure_ascii=False, indent=2), flush=True)
    print(f"Wrote {args.out}", flush=True)
    return 0 if v.get("overall_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
