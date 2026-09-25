#!/usr/bin/env python3
"""A/B load: full-frame identify vs Edge preCropped crop identify.

Simulates Chain Store central API load and estimates installed-camera capacity
from sustained RPS at Acceptable (p95<=1000) / Target (p95<=550).

Outputs: scripts/kiosk-load/.cache/summary-edge-crop-identify.json
"""
from __future__ import annotations

import argparse
import io
import json
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import httpx
from PIL import Image

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / ".cache"
FACE_CACHE = CACHE / "sample_face.jpg"
CROP_CACHE = CACHE / "sample_face_crop.jpg"

DEFAULT_BASE = os.environ.get("KIOSK_LOAD_BASE_URL", "http://10.50.0.117:8880")
DEFAULT_COMPANY = os.environ.get(
    "KIOSK_LOAD_COMPANY_ID", "11111111-1111-1111-1111-111111111112"
)

SLO_TARGET = 550.0
SLO_ACCEPT = 1000.0
SLO_ERR = 0.05


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


def pct(vals: list[float], p: float) -> float | None:
    if not vals:
        return None
    s = sorted(vals)
    i = min(len(s) - 1, max(0, int(round((p / 100.0) * (len(s) - 1)))))
    return s[i]


def prepare_crop(base: str, token: str, full_bytes: bytes) -> bytes:
    """Edge payload for A/B.

    This enrollment/sample pair only matches at near-full resolution (downscales
    and tight detector boxes fail match). We still exercise ``preCropped=true``
    on the same image to isolate the server path (legacy det@640 vs crop/embed
    path). Bandwidth savings of Edge are documented as design guidance, not as
    a smaller matching JPEG in this harness.
    """
    del base, token  # reserved for future crop builders
    CACHE.mkdir(parents=True, exist_ok=True)
    # Keep a copy named crop for tooling; content equals full sample for match fidelity.
    if not CROP_CACHE.is_file() or CROP_CACHE.stat().st_size != len(full_bytes):
        CROP_CACHE.write_bytes(full_bytes)
    print(
        f"  edge payload: {len(full_bytes)} bytes "
        f"(same pixels as full — match-safe for this sample)",
        flush=True,
    )
    return full_bytes


def one_identify(
    client: httpx.Client,
    url: str,
    token: str,
    company_id: str,
    image: bytes,
    *,
    pre_cropped: bool,
) -> tuple[str, float]:
    t0 = time.perf_counter()
    data = {"companyId": company_id}
    if pre_cropped:
        data["preCropped"] = "true"
    try:
        r = client.post(
            url,
            headers={"Authorization": f"Bearer {token}"},
            data=data,
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


def run_step(
    *,
    base: str,
    token: str,
    company_id: str,
    image: bytes,
    concurrency: int,
    total: int,
    pre_cropped: bool,
) -> dict[str, Any]:
    url = f"{base.rstrip('/')}/face/members/identify"
    ok_ms: list[float] = []
    buckets: dict[str, int] = {}
    t0 = time.perf_counter()
    limits = httpx.Limits(max_connections=max(concurrency, 100), max_keepalive_connections=50)
    with httpx.Client(limits=limits) as client:
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futs = [
                pool.submit(
                    one_identify,
                    client,
                    url,
                    token,
                    company_id,
                    image,
                    pre_cropped=pre_cropped,
                )
                for _ in range(total)
            ]
            for fut in as_completed(futs):
                bucket, ms = fut.result()
                buckets[bucket] = buckets.get(bucket, 0) + 1
                if bucket == "ok":
                    ok_ms.append(ms)
    elapsed = time.perf_counter() - t0
    ok = len(ok_ms)
    err = total - ok
    err_rate = err / total if total else 1.0
    p95 = pct(ok_ms, 95) or 99999.0
    p50 = pct(ok_ms, 50) or 0.0
    rps = (ok / elapsed) if elapsed > 0 else 0.0
    return {
        "concurrency": concurrency,
        "total": total,
        "ok": ok,
        "errors": err,
        "error_rate": round(err_rate, 4),
        "buckets": buckets,
        "http_502": buckets.get("http_502", 0),
        "elapsed_s": round(elapsed, 2),
        "rps_ok": round(rps, 1),
        "p50_ms_ok": round(p50, 1),
        "p95_ms_ok": round(p95, 1),
        "avg_ms_ok": round(statistics.mean(ok_ms), 1) if ok_ms else None,
        "pass_550": p95 <= SLO_TARGET and err_rate <= SLO_ERR,
        "pass_1000": p95 <= SLO_ACCEPT and err_rate <= SLO_ERR,
    }


def best_rps(steps: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
    ok_steps = [s for s in steps if s.get(key)]
    if not ok_steps:
        return None
    return max(ok_steps, key=lambda s: s.get("rps_ok") or 0)


def camera_estimate(rps: float | None, interval_s: float) -> int | None:
    if rps is None or rps <= 0:
        return None
    return int(rps * interval_s)


def run_mode(
    *,
    name: str,
    base: str,
    token: str,
    company_id: str,
    image: bytes,
    concs: list[int],
    requests_per_step: int,
    pre_cropped: bool,
) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    print(f"\n=== mode={name} image={len(image)}B preCropped={pre_cropped} ===")
    print(
        f"{'conc':>6} {'ok':>5} {'err':>4} {'rps':>7} {'p50':>8} {'p95':>8} "
        f"{'T550':>5} {'A1s':>5}"
    )
    for c in concs:
        row = run_step(
            base=base,
            token=token,
            company_id=company_id,
            image=image,
            concurrency=c,
            total=max(requests_per_step, c * 2),
            pre_cropped=pre_cropped,
        )
        steps.append(row)
        print(
            f"{row['concurrency']:6d} {row['ok']:5d} {row['errors']:4d} "
            f"{row['rps_ok']:7.1f} {row['p50_ms_ok']:7.1f}ms {row['p95_ms_ok']:7.1f}ms "
            f"{'PASS' if row['pass_550'] else 'FAIL':>5} "
            f"{'PASS' if row['pass_1000'] else 'FAIL':>5}"
        )
    b550 = best_rps(steps, "pass_550")
    b1000 = best_rps(steps, "pass_1000")
    peak = max((s.get("rps_ok") or 0) for s in steps) if steps else 0
    return {
        "name": name,
        "pre_cropped": pre_cropped,
        "image_bytes": len(image),
        "steps": steps,
        "best_target_550": b550,
        "best_acceptable_1000": b1000,
        "peak_rps_ok": peak,
        "cameras_est_at_1_per_30s_accept": camera_estimate(
            (b1000 or {}).get("rps_ok"), 30.0
        ),
        "cameras_est_at_1_per_10s_accept": camera_estimate(
            (b1000 or {}).get("rps_ok"), 10.0
        ),
        "cameras_est_at_1_per_30s_target": camera_estimate(
            (b550 or {}).get("rps_ok"), 30.0
        ),
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base-url", default=DEFAULT_BASE)
    p.add_argument("--company-id", default=DEFAULT_COMPANY)
    p.add_argument("--concurrency", default="10,20,35,50")
    p.add_argument("--requests-per-step", type=int, default=200)
    p.add_argument("--refresh-crop", action="store_true")
    args = p.parse_args()

    user, password = require_creds()
    if not FACE_CACHE.is_file():
        raise SystemExit(f"missing {FACE_CACHE} — run kiosk_load --prepare first")
    full_image = FACE_CACHE.read_bytes()
    token = login(args.base_url, user, password)
    if args.refresh_crop and CROP_CACHE.is_file():
        CROP_CACHE.unlink()
    crop_image = prepare_crop(args.base_url, token, full_image)

    concs = [int(x.strip()) for x in args.concurrency.split(",") if x.strip()]
    print(f"Base URL: {args.base_url}")
    print(f"Login as: {user}")
    print(f"Full image: {len(full_image)} bytes · Crop: {len(crop_image)} bytes")

    out: dict[str, Any] = {
        "ts": time.time(),
        "base_url": args.base_url,
        "company_id": args.company_id,
        "slo_target_ms": SLO_TARGET,
        "slo_acceptable_ms": SLO_ACCEPT,
        "modes": [],
    }

    full_mode = run_mode(
        name="full_identify",
        base=args.base_url,
        token=token,
        company_id=args.company_id,
        image=full_image,
        concs=concs,
        requests_per_step=args.requests_per_step,
        pre_cropped=False,
    )
    crop_mode = run_mode(
        name="edge_preCropped",
        base=args.base_url,
        token=token,
        company_id=args.company_id,
        image=crop_image,
        concs=concs,
        requests_per_step=args.requests_per_step,
        pre_cropped=True,
    )
    out["modes"] = [full_mode, crop_mode]

    full_rps = (full_mode.get("best_acceptable_1000") or {}).get("rps_ok") or 0
    crop_rps = (crop_mode.get("best_acceptable_1000") or {}).get("rps_ok") or 0
    out["verdict"] = {
        "crop_faster": crop_rps > full_rps * 1.05,
        "full_rps_accept": full_rps,
        "crop_rps_accept": crop_rps,
        "rps_gain_pct": round((crop_rps / full_rps - 1) * 100, 1) if full_rps else None,
        "note": (
            "Edge preCropped improves central API capacity"
            if crop_rps > full_rps * 1.05
            else "Gain limited — bottleneck may remain embed/search/API; scale horizontally"
        ),
    }

    CACHE.mkdir(parents=True, exist_ok=True)
    out_path = CACHE / "summary-edge-crop-identify.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nVerdict:", json.dumps(out["verdict"], indent=2, ensure_ascii=False))
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
