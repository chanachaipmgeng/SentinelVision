#!/usr/bin/env python3
"""GPU / queue soak: repeat identify load for ~2h while sampling queue + docker stats via SSH.

Example:
  python gpu_soak.py --kiosks 24 --chunk-hold 600 --total-hours 2
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / ".cache"
KIOSK_LOAD = ROOT / "kiosk_load.py"
SSH_REMOTE = CACHE / "ssh_remote.py"
PY = ROOT / ".venv" / "Scripts" / "python.exe"
if not PY.is_file():
    PY = Path(sys.executable)


def _ssh(cmd: str, *, timeout: int = 120, upload: list[str] | None = None) -> str:
    args = [str(PY), str(SSH_REMOTE), "--timeout", str(timeout)]
    user = os.environ.get("DPU_SSH_USER")
    password = os.environ.get("DPU_SSH_PASSWORD")
    if user:
        args += ["--user", user]
    if password:
        args += ["--password", password]
    for u in upload or []:
        args += ["--upload", u]
    args.append(cmd)
    try:
        return subprocess.check_output(args, text=True, encoding="utf-8", errors="replace")
    except subprocess.CalledProcessError as exc:
        return (exc.output or "") + str(exc)


def write_remote_metrics() -> Path:
    path = CACHE / "remote_soak_metrics.sh"
    path.write_text(
        r"""#!/bin/bash
set -euo pipefail
PW="${DPU_SUDO_PW:-}"
printf '%s\n' "$PW" | sudo -S -p '' -v
echo -n 'TS='
date -Is
echo '=== nvidia ==='
nvidia-smi --query-gpu=index,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits
echo '=== docker_stats ==='
sudo -n docker stats --no-stream --format '{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}}' \
  dpu-api dpu-api-gpu0b dpu-api-gpu1 dpu-api-gpu1b 2>/dev/null || true
""",
        encoding="utf-8",
        newline="\n",
    )
    return path


def parse_metrics(raw: str) -> dict[str, Any]:
    out: dict[str, Any] = {"raw_tail": raw[-1500:], "gpus": [], "containers": []}
    section = None
    for line in raw.splitlines():
        if line.startswith("TS="):
            out["ts_remote"] = line[3:].strip()
        elif "=== nvidia ===" in line:
            section = "nvidia"
        elif "=== docker_stats ===" in line:
            section = "docker"
        elif section == "nvidia" and line.strip() and not line.startswith("==="):
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 4:
                try:
                    out["gpus"].append(
                        {
                            "index": int(parts[0]),
                            "sm": float(parts[1]),
                            "mem_used_mib": float(parts[2]),
                            "mem_total_mib": float(parts[3]),
                        }
                    )
                except ValueError:
                    pass
        elif section == "docker" and "," in line and not line.startswith("==="):
            parts = line.split(",")
            if len(parts) >= 4:
                out["containers"].append(
                    {
                        "name": parts[0],
                        "cpu": parts[1],
                        "mem_usage": parts[2],
                        "mem_pct": parts[3].rstrip("%"),
                    }
                )
    return out


def run_kiosk_chunk(
    *,
    base_url: str,
    company_id: str,
    member_id: str,
    kiosks: int,
    hold: float,
    prepare: bool,
    jsonl: Path,
    lat: str,
    lon: str,
) -> int:
    if jsonl.exists():
        jsonl.unlink()
    cmd = [
        str(PY),
        str(KIOSK_LOAD),
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
        "identify",
        "--kiosks",
        str(kiosks),
        "--hold",
        str(hold),
        "--faces-per-kiosk",
        "1",
        "--detect-interval-ms",
        "600",
        "--jsonl",
        str(jsonl),
    ]
    if prepare:
        cmd.append("--prepare")
    print("RUN:", " ".join(cmd), flush=True)
    return subprocess.call(cmd, env=os.environ.copy())


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base-url", default=os.environ.get("KIOSK_LOAD_BASE_URL", "http://10.50.0.117:8880"))
    p.add_argument("--company-id", default=os.environ.get("KIOSK_LOAD_COMPANY_ID", "11111111-1111-1111-1111-111111111112"))
    p.add_argument("--member-id", default=os.environ.get("KIOSK_LOAD_MEMBER_ID", "66c8402f-4538-4479-ae54-946582d41098"))
    p.add_argument("--kiosks", type=int, default=24)
    p.add_argument("--chunk-hold", type=float, default=600.0, help="Seconds per kiosk_load chunk")
    p.add_argument("--total-hours", type=float, default=2.0)
    p.add_argument("--lat", default="13.877239958879965")
    p.add_argument("--lon", default="100.51154729391773")
    p.add_argument("--out", type=Path, default=CACHE / "summary-gpu-soak.json")
    p.add_argument("--metrics-csv", type=Path, default=CACHE / "gpu-soak-metrics.csv")
    args = p.parse_args()

    CACHE.mkdir(parents=True, exist_ok=True)
    helper = write_remote_metrics()
    pw = os.environ.get("DPU_SSH_PASSWORD", "")
    deadline = time.time() + args.total_hours * 3600.0
    samples: list[dict[str, Any]] = []
    chunks: list[dict[str, Any]] = []
    prepare_once = True
    chunk_i = 0

    # baseline metrics
    raw0 = _ssh(
        f"export DPU_SUDO_PW='{pw}'; bash /tmp/remote_soak_metrics.sh",
        upload=[f"{helper}::/tmp/remote_soak_metrics.sh"],
    )
    samples.append({"when": "start", "t": time.time(), **parse_metrics(raw0)})

    csv_fields = [
        "t",
        "chunk",
        "gpu0_sm",
        "gpu1_sm",
        "gpu0_mem",
        "gpu1_mem",
        "api_mem_pct",
        "api_cpu",
    ]
    with args.metrics_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=csv_fields)
        w.writeheader()

        while time.time() < deadline:
            chunk_i += 1
            remain = deadline - time.time()
            hold = min(args.chunk_hold, max(60.0, remain))
            jsonl = CACHE / f"results-soak-chunk-{chunk_i:02d}.jsonl"
            t_chunk = time.time()
            rc = run_kiosk_chunk(
                base_url=args.base_url,
                company_id=args.company_id,
                member_id=args.member_id,
                kiosks=args.kiosks,
                hold=hold,
                prepare=prepare_once,
                jsonl=jsonl,
                lat=args.lat,
                lon=args.lon,
            )
            prepare_once = False
            raw = _ssh(f"export DPU_SUDO_PW='{pw}'; bash /tmp/remote_soak_metrics.sh")
            parsed = parse_metrics(raw)
            samples.append({"when": f"after_chunk_{chunk_i}", "t": time.time(), **parsed})
            chunks.append(
                {
                    "chunk": chunk_i,
                    "hold_s": hold,
                    "exit_code": rc,
                    "elapsed_s": round(time.time() - t_chunk, 1),
                    "jsonl": str(jsonl),
                }
            )
            g0 = next((g for g in parsed.get("gpus", []) if g["index"] == 0), {})
            g1 = next((g for g in parsed.get("gpus", []) if g["index"] == 1), {})
            api = next(
                (c for c in parsed.get("containers", []) if c["name"] == "dpu-api"),
                {},
            )
            row = {
                "t": time.time(),
                "chunk": chunk_i,
                "gpu0_sm": g0.get("sm"),
                "gpu1_sm": g1.get("sm"),
                "gpu0_mem": g0.get("mem_used_mib"),
                "gpu1_mem": g1.get("mem_used_mib"),
                "api_mem_pct": api.get("mem_pct"),
                "api_cpu": api.get("cpu"),
            }
            w.writerow(row)
            fh.flush()
            print(json.dumps(row, ensure_ascii=False), flush=True)
            if time.time() >= deadline:
                break

    raw_end = _ssh(f"export DPU_SUDO_PW='{pw}'; bash /tmp/remote_soak_metrics.sh")
    samples.append({"when": "end", "t": time.time(), **parse_metrics(raw_end)})

    def mem_pct(sample: dict) -> float | None:
        for c in sample.get("containers") or []:
            if c.get("name") == "dpu-api":
                try:
                    return float(str(c.get("mem_pct", "")).replace("%", ""))
                except ValueError:
                    return None
        return None

    start_mem = mem_pct(samples[0])
    end_mem = mem_pct(samples[-1])
    leak_suspect = False
    if start_mem is not None and end_mem is not None and start_mem > 0:
        leak_suspect = (end_mem - start_mem) / start_mem >= 0.20

    # average sm from samples mid-run
    sm0: list[float] = []
    sm1: list[float] = []
    for s in samples:
        for g in s.get("gpus") or []:
            if g["index"] == 0 and g.get("sm") is not None:
                sm0.append(float(g["sm"]))
            if g["index"] == 1 and g.get("sm") is not None:
                sm1.append(float(g["sm"]))

    summary = {
        "ts": time.time(),
        "kiosks": args.kiosks,
        "total_hours": args.total_hours,
        "chunks": chunks,
        "start_mem_pct_dpu_api": start_mem,
        "end_mem_pct_dpu_api": end_mem,
        "leak_suspect_gt20pct": leak_suspect,
        "gpu0_sm_avg": round(sum(sm0) / len(sm0), 1) if sm0 else None,
        "gpu1_sm_avg": round(sum(sm1) / len(sm1), 1) if sm1 else None,
        "gpu_balance_note": (
            "balanced"
            if sm0 and sm1 and abs((sum(sm0) / len(sm0)) - (sum(sm1) / len(sm1))) < 25
            else "check_skew"
        ),
        "samples": samples,
    }
    # drop huge raw tails for readability in main file
    for s in summary["samples"]:
        s.pop("raw_tail", None)
    args.out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {args.out}", flush=True)
    print(
        f"leak_suspect={leak_suspect} gpu0_avg={summary['gpu0_sm_avg']} "
        f"gpu1_avg={summary['gpu1_sm_avg']} balance={summary['gpu_balance_note']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
