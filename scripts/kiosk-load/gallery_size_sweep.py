#!/usr/bin/env python3
"""Sweep identify latency vs company-scoped gallery size (synthetic pgvector rows).

Inserts tagged synthetic members+embeddings via docker/psql on the DPU host,
runs gated identify @ N kiosks, then deletes the tagged rows.

Requires SSH creds (env DPU_SSH_USER/PASSWORD or ~/.dpu_ssh_creds) and
KIOSK_LOAD_USER / KIOSK_LOAD_PASSWORD for the load client.

Example:
  python gallery_size_sweep.py --sizes 1000,10000,25000 --kiosks 16 --hold 90
"""
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
SSH_REMOTE = CACHE / "ssh_remote.py"
KIOSK_LOAD = ROOT / "kiosk_load.py"
PY = ROOT / ".venv" / "Scripts" / "python.exe"
if not PY.is_file():
    PY = Path(sys.executable)

TAG_PREFIX = "capgal_sweep_"


def _ssh(cmd: str, *, timeout: int = 600, upload: list[str] | None = None) -> str:
    args = [
        str(PY),
        str(SSH_REMOTE),
        "--timeout",
        str(timeout),
    ]
    user = os.environ.get("DPU_SSH_USER")
    password = os.environ.get("DPU_SSH_PASSWORD")
    if user:
        args += ["--user", user]
    if password:
        args += ["--password", password]
    for u in upload or []:
        args += ["--upload", u]
    args.append(cmd)
    print("SSH:", cmd[:200], flush=True)
    out = subprocess.check_output(args, text=True, encoding="utf-8", errors="replace")
    print(out[-2000:] if len(out) > 2000 else out, flush=True)
    return out


def write_remote_sql_helper() -> Path:
    """Ensure remote helper exists (prefer versioned remote/, else .cache)."""
    for cand in (ROOT / "remote" / "remote_gallery_sql.sh", CACHE / "remote_gallery_sql.sh"):
        if cand.is_file():
            path = CACHE / "remote_gallery_sql.sh"
            text = cand.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
            path.write_text(text, encoding="utf-8", newline="\n")
            return path
    raise SystemExit("missing remote_gallery_sql.sh (expected under scripts/kiosk-load/remote/)")


def summarize_jsonl(path: Path) -> dict[str, Any]:
    id_lat: list[float] = []
    id_ok = id_err = det_n = det_drop = 0
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
                elif ev == "identify_error":
                    id_err += 1
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
    return {
        "identify_ok": id_ok,
        "identify_errors": id_err,
        "identify_p95_ms": p95(id_lat),
        "detect_n": det_n,
        "drop_rate": round(drop, 4),
        "slo_pass_550": (p95(id_lat) or 9999) <= 550 and drop <= 0.05,
    }


def run_identify(
    *,
    base_url: str,
    company_id: str,
    member_id: str,
    kiosks: int,
    hold: float,
    detect_interval_ms: float,
    jsonl: Path,
    prepare: bool,
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
        str(detect_interval_ms),
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
    p.add_argument("--sizes", default="1000,10000,25000")
    p.add_argument("--kiosks", type=int, default=16)
    p.add_argument("--hold", type=float, default=90.0)
    p.add_argument("--detect-interval-ms", type=float, default=600.0)
    p.add_argument("--lat", default="13.877239958879965")
    p.add_argument("--lon", default="100.51154729391773")
    p.add_argument("--skip-baseline", action="store_true")
    p.add_argument("--out", type=Path, default=CACHE / "summary-gallery-sweep.json")
    args = p.parse_args()

    if not SSH_REMOTE.is_file():
        raise SystemExit(f"missing {SSH_REMOTE}")

    CACHE.mkdir(parents=True, exist_ok=True)
    helper = write_remote_sql_helper()
    pw = os.environ.get("DPU_SSH_PASSWORD", "")
    remote_env = f"export DPU_SUDO_PW='{pw}'; "

    summary: dict[str, Any] = {
        "ts": time.time(),
        "base_url": args.base_url,
        "company_id": args.company_id,
        "kiosks": args.kiosks,
        "hold_s": args.hold,
        "runs": [],
    }

    # Always start clean of prior tagged rows
    _ssh(
        f"{remote_env}bash /tmp/remote_gallery_sql.sh delete 0 {args.company_id} {args.member_id} {TAG_PREFIX}",
        timeout=300,
        upload=[f"{helper}::/tmp/remote_gallery_sql.sh"],
    )

    prepare_once = True
    sizes = [0] if not args.skip_baseline else []
    sizes += [int(x.strip()) for x in args.sizes.split(",") if x.strip()]

    for size in sizes:
        if size > 0:
            _ssh(
                f"{remote_env}bash /tmp/remote_gallery_sql.sh insert {size} {args.company_id} {args.member_id} {TAG_PREFIX}",
                timeout=900,
            )
        count_out = _ssh(
            f"{remote_env}bash /tmp/remote_gallery_sql.sh count 0 {args.company_id} {args.member_id} {TAG_PREFIX}",
            timeout=120,
        )
        jsonl = CACHE / f"results-gallery-{size}.jsonl"
        rc = run_identify(
            base_url=args.base_url,
            company_id=args.company_id,
            member_id=args.member_id,
            kiosks=args.kiosks,
            hold=args.hold,
            detect_interval_ms=args.detect_interval_ms,
            jsonl=jsonl,
            prepare=prepare_once,
            lat=args.lat,
            lon=args.lon,
        )
        prepare_once = False
        block = summarize_jsonl(jsonl)
        block["synthetic_size"] = size
        block["exit_code"] = rc
        block["count_out"] = count_out[-500:]
        summary["runs"].append(block)
        print(json.dumps(block, ensure_ascii=False, indent=2), flush=True)
        if size > 0:
            _ssh(
                f"{remote_env}bash /tmp/remote_gallery_sql.sh delete 0 {args.company_id} {args.member_id} {TAG_PREFIX}",
                timeout=300,
            )

    # Final cleanup
    _ssh(
        f"{remote_env}bash /tmp/remote_gallery_sql.sh delete 0 {args.company_id} {args.member_id} {TAG_PREFIX}",
        timeout=300,
    )

    args.out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
