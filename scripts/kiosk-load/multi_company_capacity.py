#!/usr/bin/env python3
"""Multi-company capacity: N companies × 1 kiosk (fixed total screens).

Creates temporary companies/employees via docker/psql, copies the source face
embedding into each, runs parallel identify load (one process per company),
then deletes tagged rows.

Example:
  python multi_company_capacity.py --companies 20 --hold 180
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / ".cache"
SSH_REMOTE = CACHE / "ssh_remote.py"
KIOSK_LOAD = ROOT / "kiosk_load.py"
PY = ROOT / ".venv" / "Scripts" / "python.exe"
if not PY.is_file():
    PY = Path(sys.executable)

TAG_PREFIX = "capco_sweep_"


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
    print("SSH:", cmd[:220], flush=True)
    out = subprocess.check_output(args, text=True, encoding="utf-8", errors="replace")
    print(out[-2000:] if len(out) > 2000 else out, flush=True)
    return out


def write_remote_helper() -> Path:
    for cand in (ROOT / "remote" / "remote_multico_sql.sh", CACHE / "remote_multico_sql.sh"):
        if cand.is_file():
            path = CACHE / "remote_multico_sql.sh"
            text = cand.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
            path.write_text(text, encoding="utf-8", newline="\n")
            return path
    raise SystemExit("missing remote_multico_sql.sh (expected under scripts/kiosk-load/remote/)")



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


def run_one_kiosk(
    *,
    base_url: str,
    company_id: str,
    member_id: str,
    hold: float,
    detect_interval_ms: float,
    jsonl: Path,
    lat: str,
    lon: str,
    prepare: bool,
) -> dict[str, Any]:
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
        "1",
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
    rc = subprocess.call(cmd, env=os.environ.copy())
    block = summarize_jsonl(jsonl)
    block["company_id"] = company_id
    block["member_id"] = member_id
    block["exit_code"] = rc
    return block


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base-url", default=os.environ.get("KIOSK_LOAD_BASE_URL", "http://10.50.0.117:8880"))
    p.add_argument(
        "--source-company-id",
        default=os.environ.get("KIOSK_LOAD_COMPANY_ID", "11111111-1111-1111-1111-111111111112"),
    )
    p.add_argument(
        "--source-member-id",
        default=os.environ.get("KIOSK_LOAD_MEMBER_ID", "66c8402f-4538-4479-ae54-946582d41098"),
        help="Member whose face embedding is copied into each temp company",
    )
    p.add_argument(
        "--load-member-id",
        default=os.environ.get(
            "KIOSK_LOAD_LOGIN_MEMBER_ID",
            "282d30e3-a986-441e-88e1-145ed5b6e7e4",
        ),
        help="memberId of the login user (granted ADMIN_COMPANY on each temp company)",
    )
    p.add_argument("--companies", type=int, default=20)
    p.add_argument("--hold", type=float, default=180.0)
    p.add_argument("--detect-interval-ms", type=float, default=600.0)
    p.add_argument("--lat", default="13.877239958879965")
    p.add_argument("--lon", default="100.51154729391773")
    p.add_argument("--out", type=Path, default=CACHE / "summary-multico.json")
    args = p.parse_args()

    if not SSH_REMOTE.is_file():
        raise SystemExit(f"missing {SSH_REMOTE}")

    CACHE.mkdir(parents=True, exist_ok=True)
    helper = write_remote_helper()
    pw = os.environ.get("DPU_SSH_PASSWORD", "")
    remote_env = f"export DPU_SUDO_PW='{pw}'; "

    _ssh(
        f"{remote_env}bash /tmp/remote_multico_sql.sh delete 0 {args.source_company_id} {args.source_member_id} {TAG_PREFIX}",
        timeout=300,
        upload=[f"{helper}::/tmp/remote_multico_sql.sh"],
    )
    _ssh(
        f"{remote_env}bash /tmp/remote_multico_sql.sh insert {args.companies} {args.source_company_id} {args.source_member_id} {TAG_PREFIX} /tmp/capco_companies.json {args.load_member_id}",
        timeout=300,
    )
    list_out = _ssh(
        f"{remote_env}bash /tmp/remote_multico_sql.sh list 0 {args.source_company_id} {args.source_member_id} {TAG_PREFIX}",
        timeout=120,
    )
    # Parse last JSON array line
    companies: list[dict[str, Any]] = []
    for line in reversed(list_out.splitlines()):
        line = line.strip()
        if line.startswith("["):
            companies = json.loads(line)
            break
    if not companies:
        raise SystemExit(f"failed to parse company list from:\n{list_out[-800:]}")

    # Baseline: same total kiosks on one company
    base_jsonl = CACHE / "results-multico-baseline-singleco.jsonl"
    print(f"Baseline single-company {args.companies} kiosks ...", flush=True)
    cmd = [
        str(PY),
        str(KIOSK_LOAD),
        "--base-url",
        args.base_url,
        "--company-id",
        args.source_company_id,
        "--member-id",
        args.source_member_id,
        "--lat",
        args.lat,
        "--lon",
        args.lon,
        "--profile",
        "identify",
        "--kiosks",
        str(args.companies),
        "--hold",
        str(args.hold),
        "--faces-per-kiosk",
        "1",
        "--detect-interval-ms",
        str(args.detect_interval_ms),
        "--jsonl",
        str(base_jsonl),
        "--prepare",
    ]
    base_rc = subprocess.call(cmd, env=os.environ.copy())
    baseline = summarize_jsonl(base_jsonl)
    baseline["mode"] = "single_company"
    baseline["kiosks"] = args.companies
    baseline["exit_code"] = base_rc

    # Multi: 1 kiosk per company in parallel
    print(f"Multi-company {len(companies)} × 1 kiosk ...", flush=True)
    per_company: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(32, len(companies))) as pool:
        futs = []
        for i, co in enumerate(companies):
            jsonl = CACHE / f"results-multico-co-{i:02d}.jsonl"
            futs.append(
                pool.submit(
                    run_one_kiosk,
                    base_url=args.base_url,
                    company_id=str(co["companyId"]),
                    member_id=str(co["memberId"]),
                    hold=args.hold,
                    detect_interval_ms=args.detect_interval_ms,
                    jsonl=jsonl,
                    lat=args.lat,
                    lon=args.lon,
                    prepare=False,
                )
            )
        for fut in as_completed(futs):
            per_company.append(fut.result())

    # Aggregate multi
    all_p95 = [r["identify_p95_ms"] for r in per_company if r.get("identify_p95_ms") is not None]
    agg = {
        "mode": "multi_company",
        "companies": len(companies),
        "kiosks_total": len(companies),
        "identify_ok": sum(r.get("identify_ok", 0) for r in per_company),
        "identify_errors": sum(r.get("identify_errors", 0) for r in per_company),
        "identify_p95_ms_median_of_cos": (
            round(sorted(all_p95)[len(all_p95) // 2], 1) if all_p95 else None
        ),
        "identify_p95_ms_max_of_cos": (max(all_p95) if all_p95 else None),
        "drop_rate_avg": round(
            sum(r.get("drop_rate", 0) for r in per_company) / max(1, len(per_company)), 4
        ),
        "slo_pass_all": all(r.get("slo_pass_550") for r in per_company),
        "per_company": per_company,
    }

    _ssh(
        f"{remote_env}bash /tmp/remote_multico_sql.sh delete 0 {args.source_company_id} {args.source_member_id} {TAG_PREFIX}",
        timeout=300,
    )

    summary = {
        "ts": time.time(),
        "base_url": args.base_url,
        "hold_s": args.hold,
        "baseline_single_company": baseline,
        "multi_company": agg,
    }
    args.out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"baseline": baseline, "multi_agg": {k: v for k, v in agg.items() if k != "per_company"}}, indent=2), flush=True)
    print(f"Wrote {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
