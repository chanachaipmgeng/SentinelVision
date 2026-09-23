#!/usr/bin/env python3
"""HTTP one-shot identify load: POST /face/members/identify concurrently.

Measures what 'send a photo, get a name' supports without kiosk WS / check-in.
"""
from __future__ import annotations

import argparse
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx

DEFAULT_BASE = os.environ.get("KIOSK_LOAD_BASE_URL", "http://10.50.0.117:8880")
DEFAULT_COMPANY = os.environ.get(
    "KIOSK_LOAD_COMPANY_ID", "11111111-1111-1111-1111-111111111111"
)
FACE_CACHE = Path(__file__).resolve().parent / ".cache" / "sample_face.jpg"


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
) -> tuple[bool, float, str]:
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
        if r.status_code >= 400:
            return False, ms, f"http_{r.status_code}"
        return True, ms, "ok"
    except Exception as e:  # noqa: BLE001
        ms = (time.perf_counter() - t0) * 1000
        return False, ms, type(e).__name__


def pct(vals: list[float], p: float) -> float | None:
    if not vals:
        return None
    s = sorted(vals)
    i = min(len(s) - 1, max(0, int(round((p / 100.0) * (len(s) - 1)))))
    return s[i]


def run_step(
    *,
    base: str,
    token: str,
    company_id: str,
    image: bytes,
    concurrency: int,
    total: int,
) -> dict:
    url = f"{base.rstrip('/')}/face/members/identify"
    ok_ms: list[float] = []
    err = 0
    t0 = time.perf_counter()
    with httpx.Client() as client:
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futs = [
                pool.submit(one_identify, client, url, token, company_id, image)
                for _ in range(total)
            ]
            for fut in as_completed(futs):
                success, ms, _ = fut.result()
                if success:
                    ok_ms.append(ms)
                else:
                    err += 1
    elapsed = time.perf_counter() - t0
    return {
        "concurrency": concurrency,
        "total": total,
        "ok": len(ok_ms),
        "errors": err,
        "elapsed_s": round(elapsed, 2),
        "rps": round(len(ok_ms) / elapsed, 1) if elapsed > 0 else 0.0,
        "p50_ms": round(pct(ok_ms, 50) or 0, 1),
        "p95_ms": round(pct(ok_ms, 95) or 0, 1),
        "avg_ms": round(statistics.mean(ok_ms), 1) if ok_ms else None,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default=DEFAULT_BASE)
    p.add_argument("--company-id", default=DEFAULT_COMPANY)
    p.add_argument(
        "--concurrency",
        default="20,50,100,150",
        help="Comma-separated concurrent in-flight request counts",
    )
    p.add_argument(
        "--requests-per-step",
        type=int,
        default=200,
        help="Total HTTP identify calls per concurrency step",
    )
    args = p.parse_args()
    user, password = require_creds()
    if not FACE_CACHE.is_file():
        raise SystemExit(f"missing sample face {FACE_CACHE} — run kiosk_load --prepare first")
    image = FACE_CACHE.read_bytes()
    token = login(args.base_url, user, password)
    print(f"Base URL: {args.base_url}")
    print(f"Login as: {user}")
    print(f"Image: {len(image)} bytes")
    concs = [int(x.strip()) for x in args.concurrency.split(",") if x.strip()]
    print(
        f"{'conc':>6} {'ok':>5} {'err':>4} {'rps':>7} {'p50':>8} {'p95':>8} {'elapsed':>8}"
    )
    for c in concs:
        row = run_step(
            base=args.base_url,
            token=token,
            company_id=args.company_id,
            image=image,
            concurrency=c,
            total=max(args.requests_per_step, c * 2),
        )
        print(
            f"{row['concurrency']:6d} {row['ok']:5d} {row['errors']:4d} "
            f"{row['rps']:7.1f} {row['p50_ms']:7.1f}ms {row['p95_ms']:7.1f}ms "
            f"{row['elapsed_s']:7.2f}s"
        )
        # SLO-ish for one-shot UX: p95 <= 1000 ms and error rate < 5%
        err_rate = row["errors"] / row["total"] if row["total"] else 1
        verdict = "OK" if row["p95_ms"] <= 1000 and err_rate <= 0.05 else "FAIL"
        print(f"         -> {verdict} (SLO: identify p95<=1000ms, err<=5%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
