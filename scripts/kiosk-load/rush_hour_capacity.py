#!/usr/bin/env python3
"""Rush-window capacity: gated identify (and optional rush) then summarize scans/min.

Also can prepare ~N rotated members (copied embeddings) to reduce check-in dedupe
collapse when many kiosks share one face — still one face image, but many member
rows so ORDER BY distance may spread; for true unique punches set
CHECK_IN_DEDUPE_SECONDS=0 temporarily on the server.

Example:
  set KIOSK_LOAD_USER / KIOSK_LOAD_PASSWORD / KIOSK_LOAD_BASE_URL
  python rush_hour_capacity.py --kiosks 24,32 --hold 1200 --detect-interval-ms 600
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / ".cache"
KIOSK_LOAD = ROOT / "kiosk_load.py"
SSH_REMOTE = CACHE / "ssh_remote.py"
PY = ROOT / ".venv" / "Scripts" / "python.exe"
if not PY.is_file():
    PY = Path(sys.executable)

ROTATE_TAG = "caprush_rot_"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def summarize_jsonl(path: Path, hold_s: float) -> dict[str, Any]:
    rows = _load_jsonl(path)
    by_step: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_step[str(r.get("step") or "unknown")].append(r)

    steps_out: list[dict[str, Any]] = []
    for step, items in by_step.items():
        id_ok = [r for r in items if r.get("event") == "identified"]
        id_err = [r for r in items if r.get("event") == "identify_error"]
        det = [r for r in items if r.get("event") == "detected"]
        det_drop = [r for r in det if r.get("dropped")]
        cin = [r for r in items if r.get("event") == "checked_in"]
        cin_dup = [r for r in cin if r.get("duplicate")]
        cin_new = [r for r in cin if r.get("checkedIn") and not r.get("duplicate")]
        fcd = sum(1 for r in items if r.get("event") == "face_core_down")

        def p95(vals: list[float]) -> float | None:
            if not vals:
                return None
            s = sorted(vals)
            idx = min(len(s) - 1, max(0, int(round(0.95 * (len(s) - 1)))))
            return round(s[idx], 1)

        id_lat = [float(r["latency_ms"]) for r in id_ok if r.get("latency_ms") is not None]
        det_lat = [
            float(r["latency_ms"])
            for r in det
            if r.get("latency_ms") is not None and not r.get("dropped")
        ]
        n_id = len(id_ok)
        n_det = len(det)
        drop_rate = (len(det_drop) / n_det) if n_det else 0.0
        per_min = (n_id / hold_s * 60.0) if hold_s > 0 else 0.0
        per_20 = per_min * 20.0
        per_hour = per_min * 60.0
        slo_id = (p95(id_lat) or 9999) <= 550 and drop_rate <= 0.05
        slo_relaxed = (p95(id_lat) or 9999) <= 800 and drop_rate <= 0.05

        steps_out.append(
            {
                "step": step,
                "identify_ok": n_id,
                "identify_errors": len(id_err),
                "identify_p95_ms": p95(id_lat),
                "detect_n": n_det,
                "detect_p95_ms": p95(det_lat),
                "drop_rate": round(drop_rate, 4),
                "checkin_new": len(cin_new),
                "checkin_duplicate": len(cin_dup),
                "checkin_total_events": len(cin),
                "face_core_down": fcd,
                "scans_per_min": round(per_min, 1),
                "scans_per_20min": round(per_20, 0),
                "scans_per_hour": round(per_hour, 0),
                "slo_pass_550": slo_id,
                "slo_pass_800": slo_relaxed,
            }
        )
    return {"file": str(path), "hold_s": hold_s, "steps": steps_out}


def _ssh(cmd: str, *, timeout: int = 600, upload: list[str] | None = None) -> str:
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
    print("SSH:", cmd[:200], flush=True)
    out = subprocess.check_output(args, text=True, encoding="utf-8", errors="replace")
    print(out[-1500:] if len(out) > 1500 else out, flush=True)
    return out


def prepare_rotated_members(company_id: str, source_member: str, n: int) -> None:
    """Create N members with copied face embeddings via remote_rush_rotate_fixed.sh."""
    src = None
    for cand in (ROOT / "remote" / "remote_rush_rotate_fixed.sh", CACHE / "remote_rush_rotate_fixed.sh"):
        if cand.is_file():
            src = cand
            break
    if src is None:
        raise SystemExit("missing remote_rush_rotate_fixed.sh")
    helper = CACHE / "remote_rush_rotate_fixed.sh"
    helper.write_text(
        src.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n"),
        encoding="utf-8",
        newline="\n",
    )
    pw = os.environ.get("DPU_SSH_PASSWORD", "")
    _ssh(
        f"export DPU_SUDO_PW='{pw}'; bash /tmp/remote_rush_rotate_fixed.sh prepare {n} {company_id} {source_member}",
        timeout=300,
        upload=[f"{helper}::/tmp/remote_rush_rotate_fixed.sh"],
    )


def cleanup_rotated_members() -> None:
    src = None
    for cand in (ROOT / "remote" / "remote_rush_rotate_fixed.sh", CACHE / "remote_rush_rotate_fixed.sh"):
        if cand.is_file():
            src = cand
            break
    if src is None:
        return
    helper = CACHE / "remote_rush_rotate_fixed.sh"
    helper.write_text(
        src.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n"),
        encoding="utf-8",
        newline="\n",
    )
    pw = os.environ.get("DPU_SSH_PASSWORD", "")
    cid = os.environ.get("KIOSK_LOAD_COMPANY_ID", "11111111-1111-1111-1111-111111111112")
    mid = os.environ.get("KIOSK_LOAD_MEMBER_ID", "66c8402f-4538-4479-ae54-946582d41098")
    _ssh(
        f"export DPU_SUDO_PW='{pw}'; bash /tmp/remote_rush_rotate_fixed.sh cleanup 0 {cid} {mid}",
        timeout=300,
        upload=[f"{helper}::/tmp/remote_rush_rotate_fixed.sh"],
    )


def run_kiosk_load(
    *,
    base_url: str,
    company_id: str,
    member_id: str,
    profile: str,
    kiosks: str,
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
        profile,
        "--kiosks",
        kiosks,
        "--hold",
        str(hold),
        "--faces-per-kiosk",
        "1",
        "--frame-width",
        "1280",
        "--jpeg-quality",
        "70",
        "--detect-interval-ms",
        str(detect_interval_ms),
        "--jsonl",
        str(jsonl),
    ]
    if prepare:
        cmd.append("--prepare")
    print("RUN:", " ".join(cmd), flush=True)
    env = os.environ.copy()
    return subprocess.call(cmd, env=env)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base-url", default=os.environ.get("KIOSK_LOAD_BASE_URL", "http://10.50.0.117:8880"))
    p.add_argument("--company-id", default=os.environ.get("KIOSK_LOAD_COMPANY_ID", "11111111-1111-1111-1111-111111111112"))
    p.add_argument("--member-id", default=os.environ.get("KIOSK_LOAD_MEMBER_ID", "66c8402f-4538-4479-ae54-946582d41098"))
    p.add_argument("--lat", default="13.877239958879965")
    p.add_argument("--lon", default="100.51154729391773")
    p.add_argument("--kiosks", default="24,32", help="Identify window kiosk counts")
    p.add_argument("--hold", type=float, default=1200.0, help="Seconds per identify step (default 20 min)")
    p.add_argument("--detect-interval-ms", type=float, default=600.0)
    p.add_argument("--skip-identify", action="store_true")
    p.add_argument("--rush-kiosks", type=int, default=24)
    p.add_argument("--rush-hold", type=float, default=600.0, help="Rush secondary hold (default 10 min)")
    p.add_argument("--skip-rush", action="store_true")
    p.add_argument("--rotate-members", type=int, default=300, help="Prepare N rotated members before rush (0=skip)")
    p.add_argument("--out", type=Path, default=CACHE / "summary-rush-capacity.json")
    args = p.parse_args()

    CACHE.mkdir(parents=True, exist_ok=True)
    summary: dict[str, Any] = {
        "ts": time.time(),
        "base_url": args.base_url,
        "detect_interval_ms": args.detect_interval_ms,
        "runs": [],
    }

    prepare_once = True
    if not args.skip_identify:
        for k in args.kiosks.split(","):
            k = k.strip()
            if not k:
                continue
            jsonl = CACHE / f"results-rushwin-id-{k}.jsonl"
            rc = run_kiosk_load(
                base_url=args.base_url,
                company_id=args.company_id,
                member_id=args.member_id,
                profile="identify",
                kiosks=k,
                hold=args.hold,
                detect_interval_ms=args.detect_interval_ms,
                jsonl=jsonl,
                prepare=prepare_once,
                lat=args.lat,
                lon=args.lon,
            )
            prepare_once = False
            block = summarize_jsonl(jsonl, args.hold)
            block["profile"] = "identify"
            block["kiosks"] = int(k)
            block["exit_code"] = rc
            summary["runs"].append(block)
            print(json.dumps(block, ensure_ascii=False, indent=2), flush=True)

    if not args.skip_rush:
        if args.rotate_members > 0 and SSH_REMOTE.is_file():
            try:
                prepare_rotated_members(args.company_id, args.member_id, args.rotate_members)
                summary["rotated_members"] = args.rotate_members
            except Exception as exc:  # noqa: BLE001
                print(f"WARN rotate members failed: {exc}", flush=True)
                summary["rotated_members_error"] = str(exc)

        jsonl = CACHE / f"results-rushwin-rush-{args.rush_kiosks}.jsonl"
        rc = run_kiosk_load(
            base_url=args.base_url,
            company_id=args.company_id,
            member_id=args.member_id,
            profile="rush",
            kiosks=str(args.rush_kiosks),
            hold=args.rush_hold,
            detect_interval_ms=args.detect_interval_ms,
            jsonl=jsonl,
            prepare=prepare_once,
            lat=args.lat,
            lon=args.lon,
        )
        block = summarize_jsonl(jsonl, args.rush_hold)
        block["profile"] = "rush"
        block["kiosks"] = args.rush_kiosks
        block["exit_code"] = rc
        block["note"] = (
            "Same face image → many checkin_duplicate under CHECK_IN_DEDUPE; "
            "rotated members increase gallery density. Primary people metric = identify_ok."
        )
        summary["runs"].append(block)
        print(json.dumps(block, ensure_ascii=False, indent=2), flush=True)

        if args.rotate_members > 0 and SSH_REMOTE.is_file():
            try:
                cleanup_rotated_members()
            except Exception as exc:  # noqa: BLE001
                print(f"WARN rotate cleanup failed: {exc}", flush=True)

    args.out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
