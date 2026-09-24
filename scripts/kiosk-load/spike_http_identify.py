#!/usr/bin/env python3
"""Spike HTTP identify: high concurrency sweep with 502/504/timeout + RPS.

Optionally samples Postgres connections via SSH (remote_pool_snapshot.sh).

Example:
  set KIOSK_LOAD_USER / KIOSK_LOAD_PASSWORD / KIOSK_LOAD_BASE_URL
  python spike_http_identify.py --concurrency 50,100,200,500,1000 --requests-per-step 500
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / ".cache"
FACE_CACHE = CACHE / "sample_face.jpg"
SSH_REMOTE = CACHE / "ssh_remote.py"
POOL_HELPER = ROOT / "remote" / "remote_pool_snapshot.sh"
PY = ROOT / ".venv" / "Scripts" / "python.exe"
if not PY.is_file():
    PY = Path(sys.executable)

DEFAULT_BASE = os.environ.get("KIOSK_LOAD_BASE_URL", "http://10.50.0.117:8880")
DEFAULT_COMPANY = os.environ.get(
    "KIOSK_LOAD_COMPANY_ID", "11111111-1111-1111-1111-111111111112"
)


def require_creds() -> tuple[str, str]:
    user = os.environ.get("KIOSK_LOAD_USER", "").strip()
    password = os.environ.get("KIOSK_LOAD_PASSWORD", "").strip()
    if not user or not password:
        raise SystemExit("Set KIOSK_LOAD_USER and KIOSK_LOAD_PASSWORD")
    return user, password


def login(base: str, user: str, password: str) -> str:
    with httpx.Client(timeout=30.0) as client:
        r = client.post(
            f"{base.rstrip('/')}/auth/login",
            json={"username": user, "password": password},
        )
        r.raise_for_status()
        return r.json()["access_token"]


def one_identify(
    client: httpx.Client,
    url: str,
    token: str,
    company_id: str,
    image: bytes,
) -> tuple[str, float]:
    """Return (bucket, latency_ms). bucket: ok|http_4xx|http_502|http_504|http_5xx|timeout|error."""
    t0 = time.perf_counter()
    try:
        r = client.post(
            url,
            headers={"Authorization": f"Bearer {token}"},
            data={"companyId": company_id},
            files={"file": ("face.jpg", image, "image/jpeg")},
            timeout=60.0,
        )
        ms = (time.perf_counter() - t0) * 1000
        code = r.status_code
        if code < 400:
            return "ok", ms
        if code == 502:
            return "http_502", ms
        if code == 504:
            return "http_504", ms
        if 400 <= code < 500:
            return "http_4xx", ms
        return "http_5xx", ms
    except httpx.TimeoutException:
        return "timeout", (time.perf_counter() - t0) * 1000
    except Exception:  # noqa: BLE001
        return "error", (time.perf_counter() - t0) * 1000


def pct(vals: list[float], p: float) -> float | None:
    if not vals:
        return None
    s = sorted(vals)
    i = min(len(s) - 1, max(0, int(round((p / 100.0) * (len(s) - 1)))))
    return round(s[i], 1)


def pool_snapshot() -> dict[str, Any] | None:
    if not SSH_REMOTE.is_file() or not POOL_HELPER.is_file():
        return None
    helper = CACHE / "remote_pool_snapshot.sh"
    text = POOL_HELPER.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    helper.write_text(text, encoding="utf-8", newline="\n")
    args = [str(PY), str(SSH_REMOTE), "--timeout", "60"]
    user = os.environ.get("DPU_SSH_USER")
    password = os.environ.get("DPU_SSH_PASSWORD")
    if user:
        args += ["--user", user]
    if password:
        args += ["--password", password]
    args += [
        "--upload",
        f"{helper}::/tmp/remote_pool_snapshot.sh",
        "export DPU_SUDO_PW='{PW}'; bash /tmp/remote_pool_snapshot.sh",
    ]
    try:
        out = subprocess.check_output(args, text=True, encoding="utf-8", errors="replace")
    except subprocess.CalledProcessError as exc:
        return {"error": str(exc), "stdout": (exc.output or "")[-500:]}
    # Parse last JSON object line
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return {"raw": out[-800:]}


def run_step(
    *,
    base: str,
    token: str,
    company_id: str,
    image: bytes,
    concurrency: int,
    total: int,
    sample_pool: bool,
) -> dict[str, Any]:
    url = f"{base.rstrip('/')}/face/members/identify"
    buckets: Counter[str] = Counter()
    ok_ms: list[float] = []
    all_ms: list[float] = []
    pool_before = pool_snapshot() if sample_pool else None
    t0 = time.perf_counter()
    limits = httpx.Limits(max_connections=max(concurrency, 100), max_keepalive_connections=50)
    with httpx.Client(limits=limits) as client:
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futs = [
                pool.submit(one_identify, client, url, token, company_id, image)
                for _ in range(total)
            ]
            for fut in as_completed(futs):
                bucket, ms = fut.result()
                buckets[bucket] += 1
                all_ms.append(ms)
                if bucket == "ok":
                    ok_ms.append(ms)
    elapsed = time.perf_counter() - t0
    pool_after = pool_snapshot() if sample_pool else None
    ok = buckets.get("ok", 0)
    err = total - ok
    p95 = pct(ok_ms, 95) or pct(all_ms, 95) or 0.0
    return {
        "concurrency": concurrency,
        "total": total,
        "ok": ok,
        "errors": err,
        "buckets": dict(buckets),
        "http_502": buckets.get("http_502", 0),
        "http_504": buckets.get("http_504", 0),
        "timeout": buckets.get("timeout", 0),
        "elapsed_s": round(elapsed, 2),
        "rps_ok": round(ok / elapsed, 1) if elapsed > 0 else 0.0,
        "rps_attempted": round(total / elapsed, 1) if elapsed > 0 else 0.0,
        "p50_ms_ok": pct(ok_ms, 50),
        "p95_ms_ok": pct(ok_ms, 95),
        "p95_ms_all": pct(all_ms, 95),
        "avg_ms_ok": round(statistics.mean(ok_ms), 1) if ok_ms else None,
        "cross_1s": bool(p95 > 1000),
        "cross_2s": bool(p95 > 2000),
        "pool_before": pool_before,
        "pool_after": pool_after,
        "slo_http_1s": (pct(ok_ms, 95) or 99999) <= 1000 and (err / total) <= 0.05 if total else False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base-url", default=DEFAULT_BASE)
    p.add_argument("--company-id", default=DEFAULT_COMPANY)
    p.add_argument("--concurrency", default="20,50,100")
    p.add_argument("--requests-per-step", type=int, default=500)
    p.add_argument("--sample-pool", action="store_true", default=True)
    p.add_argument("--no-sample-pool", action="store_true")
    p.add_argument("--out", type=Path, default=CACHE / "summary-spike-http.json")
    args = p.parse_args()
    sample_pool = args.sample_pool and not args.no_sample_pool

    user, password = require_creds()
    if not FACE_CACHE.is_file():
        raise SystemExit(f"missing {FACE_CACHE} — run kiosk_load --prepare first")
    image = FACE_CACHE.read_bytes()
    token = login(args.base_url, user, password)
    CACHE.mkdir(parents=True, exist_ok=True)

    concs = [int(x.strip()) for x in args.concurrency.split(",") if x.strip()]
    summary: dict[str, Any] = {
        "ts": time.time(),
        "base_url": args.base_url,
        "company_id": args.company_id,
        "image_bytes": len(image),
        "steps": [],
    }
    print(
        f"{'conc':>6} {'ok':>5} {'502':>4} {'504':>4} {'to':>4} "
        f"{'rps':>7} {'p95ok':>8} {'p95all':>8} {'cross':>8}"
    )
    first_cross_1s = None
    first_cross_2s = None
    for c in concs:
        total = max(args.requests_per_step, c)
        row = run_step(
            base=args.base_url,
            token=token,
            company_id=args.company_id,
            image=image,
            concurrency=c,
            total=total,
            sample_pool=sample_pool,
        )
        summary["steps"].append(row)
        cross = []
        if row["cross_1s"]:
            cross.append("1s")
            if first_cross_1s is None:
                first_cross_1s = c
        if row["cross_2s"]:
            cross.append("2s")
            if first_cross_2s is None:
                first_cross_2s = c
        print(
            f"{c:6d} {row['ok']:5d} {row['http_502']:4d} {row['http_504']:4d} "
            f"{row['timeout']:4d} {row['rps_ok']:7.1f} "
            f"{(row['p95_ms_ok'] or 0):7.1f}ms {(row['p95_ms_all'] or 0):7.1f}ms "
            f"{','.join(cross) or '-':>8}"
        )
        if row.get("pool_after") and isinstance(row["pool_after"], dict):
            pa = row["pool_after"]
            if "active" in pa:
                print(
                    f"         pool active={pa.get('active')} "
                    f"idle={pa.get('idle')} max={pa.get('max_conn')} "
                    f"waiting={pa.get('waiting', 0)}"
                )

    summary["first_conc_p95_over_1s"] = first_cross_1s
    summary["first_conc_p95_over_2s"] = first_cross_2s
    peak_rps = max((s["rps_ok"] for s in summary["steps"]), default=0)
    summary["peak_rps_ok"] = peak_rps
    args.out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"peak_rps_ok={peak_rps} first_cross_1s={first_cross_1s} first_cross_2s={first_cross_2s}")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
