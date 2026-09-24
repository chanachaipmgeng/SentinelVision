#!/usr/bin/env python3
"""pgvector HNSW concurrent read storm + optional R/W mix at ~20k gallery.

Uses SSH + docker/psql on the DPU host. Synthetic rows tagged capgal_sweep_
(reuses gallery helper insert/delete).

Example:
  python pgvector_concurrency.py --target-gallery 20000 --clients 100,250,500
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
GALLERY_HELPER = ROOT / "remote" / "remote_gallery_sql.sh"
PGVEC_HELPER = ROOT / "remote" / "remote_pgvector_bench.sh"
PY = ROOT / ".venv" / "Scripts" / "python.exe"
if not PY.is_file():
    PY = Path(sys.executable)

TAG = "capgal_sweep_"
DEFAULT_COMPANY = os.environ.get(
    "KIOSK_LOAD_COMPANY_ID", "11111111-1111-1111-1111-111111111112"
)
DEFAULT_MEMBER = os.environ.get(
    "KIOSK_LOAD_MEMBER_ID", "66c8402f-4538-4479-ae54-946582d41098"
)


def _ssh(cmd: str, *, timeout: int = 900, upload: list[str] | None = None) -> str:
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


def ensure_helpers() -> tuple[Path, Path]:
    CACHE.mkdir(parents=True, exist_ok=True)
    g = CACHE / "remote_gallery_sql.sh"
    g.write_text(
        GALLERY_HELPER.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n"),
        encoding="utf-8",
        newline="\n",
    )
    p = CACHE / "remote_pgvector_bench.sh"
    src = PGVEC_HELPER if PGVEC_HELPER.is_file() else None
    if src is None:
        raise SystemExit(f"missing {PGVEC_HELPER}")
    p.write_text(
        src.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n"),
        encoding="utf-8",
        newline="\n",
    )
    return g, p


def gallery_count(company_id: str, member_id: str, pw: str) -> int:
    out = _ssh(
        f"export DPU_SUDO_PW='{pw}'; bash /tmp/remote_gallery_sql.sh count 0 {company_id} {member_id} {TAG}",
        timeout=120,
    )
    for line in out.splitlines():
        if line.startswith("gallery_company="):
            return int(line.split("=", 1)[1].strip())
    return 0


def ensure_gallery(company_id: str, member_id: str, target: int, pw: str) -> None:
    g, _ = ensure_helpers()
    _ssh(
        f"export DPU_SUDO_PW='{pw}'; bash /tmp/remote_gallery_sql.sh delete 0 {company_id} {member_id} {TAG}",
        timeout=300,
        upload=[f"{g}::/tmp/remote_gallery_sql.sh"],
    )
    current = gallery_count(company_id, member_id, pw)
    need = max(0, target - current)
    print(f"gallery_company={current} need_synthetic={need}", flush=True)
    if need > 0:
        _ssh(
            f"export DPU_SUDO_PW='{pw}'; bash /tmp/remote_gallery_sql.sh insert {need} {company_id} {member_id} {TAG}",
            timeout=900,
        )


def cleanup_gallery(company_id: str, member_id: str, pw: str) -> None:
    g, _ = ensure_helpers()
    _ssh(
        f"export DPU_SUDO_PW='{pw}'; bash /tmp/remote_gallery_sql.sh delete 0 {company_id} {member_id} {TAG}",
        timeout=300,
        upload=[f"{g}::/tmp/remote_gallery_sql.sh"],
    )


def run_bench_remote(
    *,
    company_id: str,
    member_id: str,
    clients: int,
    queries_per_client: int,
    mode: str,
    write_every: int,
    pw: str,
) -> dict[str, Any]:
    _, helper = ensure_helpers()
    try:
        out = _ssh(
            f"export DPU_SUDO_PW='{pw}'; bash /tmp/remote_pgvector_bench.sh "
            f"{mode} {clients} {queries_per_client} {company_id} {member_id} {write_every}",
            timeout=1200,
            upload=[f"{helper}::/tmp/remote_pgvector_bench.sh"],
        )
    except subprocess.CalledProcessError as exc:
        out = (exc.output or "") + "\n" + str(exc)
        return {"error": "remote_failed", "raw": out[-1500:], "clients": clients, "mode": mode}
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return {"error": "parse_failed", "raw": out[-1000:], "clients": clients, "mode": mode}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--company-id", default=DEFAULT_COMPANY)
    p.add_argument("--member-id", default=DEFAULT_MEMBER)
    p.add_argument("--target-gallery", type=int, default=20000)
    p.add_argument("--clients", default="100,250,500")
    p.add_argument("--queries-per-client", type=int, default=20)
    p.add_argument("--write-every", type=int, default=10, help="R/W: insert every N searches per writer")
    p.add_argument("--skip-rw", action="store_true")
    p.add_argument("--out", type=Path, default=CACHE / "summary-pgvector-concurrency.json")
    args = p.parse_args()

    pw = os.environ.get("DPU_SSH_PASSWORD", "")
    if not pw and not (Path.home() / ".dpu_ssh_creds").is_file():
        raise SystemExit("Set DPU_SSH_PASSWORD or ~/.dpu_ssh_creds")

    ensure_gallery(args.company_id, args.member_id, args.target_gallery, pw)
    final_count = gallery_count(args.company_id, args.member_id, pw)

    summary: dict[str, Any] = {
        "ts": time.time(),
        "company_id": args.company_id,
        "gallery_company": final_count,
        "read_storm": [],
        "rw_mix": None,
    }

    for c in [int(x.strip()) for x in args.clients.split(",") if x.strip()]:
        row = run_bench_remote(
            company_id=args.company_id,
            member_id=args.member_id,
            clients=c,
            queries_per_client=args.queries_per_client,
            mode="read",
            write_every=0,
            pw=pw,
        )
        row["clients"] = c
        summary["read_storm"].append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)

    if not args.skip_rw:
        # Fixed mid concurrency for R/W
        rw = run_bench_remote(
            company_id=args.company_id,
            member_id=args.member_id,
            clients=250,
            queries_per_client=args.queries_per_client,
            mode="rw",
            write_every=args.write_every,
            pw=pw,
        )
        summary["rw_mix"] = rw
        print(json.dumps(rw, ensure_ascii=False), flush=True)

    cleanup_gallery(args.company_id, args.member_id, pw)
    args.out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
