#!/usr/bin/env python3
"""Build a capacity report from kiosk_load step_summary JSONL (+ optional queue CSV)."""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any, Optional


SLO_DETECT_P95 = 550.0
SLO_DROP = 0.05


def load_steps(path: Path) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if row.get("event") != "step_summary":
            continue
        steps.append(row)
    return steps


def parse_step_label(label: str) -> dict[str, Any]:
    # e.g. kiosks=4 faces/kiosk=3 profile=rush hold=35.0s
    out: dict[str, Any] = {"raw": label}
    m = re.search(r"kiosks=(\d+)", label)
    if m:
        out["kiosks"] = int(m.group(1))
    m = re.search(r"faces/kiosk=(\d+)", label)
    if m:
        out["faces"] = int(m.group(1))
    m = re.search(r"profile=(\w+)", label)
    if m:
        out["profile"] = m.group(1)
    return out


def verdict(detect: dict[str, Any]) -> str:
    p95 = detect.get("p95_ms")
    drop = float(detect.get("dropped_rate") or 0)
    if p95 is None:
        return "n/a"
    if p95 <= SLO_DETECT_P95 and drop <= SLO_DROP:
        return "OK"
    if p95 <= SLO_DETECT_P95 * 1.5 and drop <= 0.15:
        return "MARGIN"
    return "FAIL"


def queue_peaks(csv_path: Optional[Path]) -> dict[str, Any]:
    if not csv_path or not csv_path.exists():
        return {}
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    if not rows:
        return {}

    def col(name: str) -> list[float]:
        vals = []
        for r in rows:
            raw = r.get(name)
            if raw is None or raw == "":
                continue
            try:
                vals.append(float(raw))
            except ValueError:
                pass
        return vals

    active = col("active")
    pending = col("pending")
    keys = rows[0].keys() if rows else []
    thr_key = next(
        (k for k in ("throughput_per_s", "delta_per_s", "delta/s") if k in keys),
        None,
    )
    delta = col(thr_key) if thr_key else []
    api_cpu = col("api_cpu_pct")
    gpu0 = col("gpu0_sm")
    gpu1 = col("gpu1_sm")
    devices = {r.get("devices") or r.get("device") or "" for r in rows}
    workers = {r.get("workers") for r in rows if r.get("workers") not in (None, "")}

    def avg(vals: list[float]) -> Optional[float]:
        return round(sum(vals) / len(vals), 1) if vals else None

    return {
        "samples": len(rows),
        "max_active": max(active) if active else None,
        "max_pending": max(pending) if pending else None,
        "peak_throughput": max(delta) if delta else None,
        "devices": sorted(d for d in devices if d),
        "workers": sorted(workers),
        "api_cpu_avg": avg(api_cpu),
        "api_cpu_max": max(api_cpu) if api_cpu else None,
        "gpu0_sm_avg": avg(gpu0),
        "gpu0_sm_max": max(gpu0) if gpu0 else None,
        "gpu1_sm_avg": avg(gpu1),
        "gpu1_sm_max": max(gpu1) if gpu1 else None,
    }


def md_table(steps: list[dict[str, Any]]) -> str:
    lines = [
        "| จอ | faces | detect p50 | detect p95 | drop | identify p95 | checkin p95 | verdict |",
        "|----|-------|------------|------------|------|--------------|-------------|---------|",
    ]
    decorated = []
    for row in steps:
        meta = parse_step_label(str(row.get("step", "")))
        decorated.append((int(meta.get("kiosks") or 0), meta, row))
    decorated.sort(key=lambda x: x[0])
    for _k, meta, row in decorated:
        d = row.get("detect") or {}
        i = row.get("identify") or {}
        c = row.get("checkin") or {}
        lines.append(
            "| {k} | {f} | {p50} | {p95} | {drop} | {ip95} | {cp95} | {v} |".format(
                k=meta.get("kiosks", "?"),
                f=meta.get("faces", "?"),
                p50=_ms(d.get("p50_ms")),
                p95=_ms(d.get("p95_ms")),
                drop=_pct(d.get("dropped_rate")),
                ip95=_ms(i.get("p95_ms")),
                cp95=_ms(c.get("p95_ms")),
                v=verdict(d),
            )
        )
    return "\n".join(lines)


def _ms(v: Any) -> str:
    if v is None:
        return "—"
    return f"{float(v):.0f} ms"


def _pct(v: Any) -> str:
    if v is None:
        return "—"
    return f"{float(v) * 100:.1f}%"


def find_ceiling(steps: list[dict[str, Any]], profile: str, faces: int) -> dict[str, Any]:
    ok_max = None
    fail_min = None
    ordered = []
    for row in steps:
        meta = parse_step_label(str(row.get("step", "")))
        if meta.get("profile") != profile or meta.get("faces") != faces:
            continue
        ordered.append((meta.get("kiosks", 0), row, verdict(row.get("detect") or {})))
    ordered.sort(key=lambda x: x[0])
    for k, _row, v in ordered:
        if v == "OK":
            ok_max = k
        elif v in ("MARGIN", "FAIL") and fail_min is None:
            fail_min = k
    return {"ok_max": ok_max, "fail_min": fail_min, "steps": ordered}


def build_report(
    *,
    title: str,
    env_lines: list[str],
    idle_path: Path,
    rush3_path: Path,
    rush1_path: OptionalPath,
    queue_path: OptionalPath,
    nvidia_notes: list[str],
) -> str:
    idle = load_steps(idle_path) if idle_path.exists() else []
    rush3 = load_steps(rush3_path) if rush3_path.exists() else []
    rush1 = load_steps(rush1_path) if rush1_path and rush1_path.exists() else []
    q = queue_peaks(queue_path)

    idle_c = find_ceiling(idle, "idle", 3)
    rush3_c = find_ceiling(rush3, "rush", 3)
    rush1_c = find_ceiling(rush1, "rush", 1) if rush1 else {}

    parts = [
        f"# {title}",
        "",
        "## สภาพแวดล้อม",
        "",
        *[f"- {line}" for line in env_lines],
        "",
        "## สรุปเพดาน (SLO: detect p95 ≤ 550 ms, drop ≤ 5%)",
        "",
        f"| โปรไฟล์ | ใช้ได้สูงสุด (OK) | เริ่มแย่ |",
        f"|---------|-------------------|----------|",
        f"| idle × 3 คน/จอ | **{idle_c.get('ok_max') or '—'}** จอ | {idle_c.get('fail_min') or '—'} จอ |",
        f"| rush × 3 คน/จอ | **{rush3_c.get('ok_max') or '—'}** จอ | {rush3_c.get('fail_min') or '—'} จอ |",
    ]
    if rush1:
        parts.append(
            f"| rush × 1 คน/จอ | **{rush1_c.get('ok_max') or '—'}** จอ | {rush1_c.get('fail_min') or '—'} จอ |"
        )
    parts += [
        "",
        "### คำแนะนำใช้งาน",
        "",
    ]
    r3 = rush3_c.get("ok_max")
    i3 = idle_c.get("ok_max")
    if r3:
        parts.append(
            f"- ชั่วโมงเร่งด่วน (identify + check-in, ~3 คนในเฟรม): **ไม่เกิน {r3} จอพร้อมกัน**"
        )
    if i3:
        parts.append(f"- กล้องว่าง / detect อย่างเดียว: ได้ถึงประมาณ **{i3} จอ**")
    if rush1_c.get("ok_max"):
        parts.append(
            f"- rush คนเดียวต่อจอ: ได้ถึงประมาณ **{rush1_c['ok_max']} จอ**"
        )
    parts += ["", "## Idle × 3 คน/จอ (อัตราเต็ม detect ~90 ms)", "", md_table(idle), ""]
    parts += ["## Rush × 3 คน/จอ (อัตราเต็ม UI caps)", "", md_table(rush3), ""]
    if rush1:
        parts += ["## Rush × 1 คน/จอ", "", md_table(rush1), ""]
    if q:
        parts += [
            "## คิว GPU ระหว่างเทส",
            "",
            f"- devices: `{', '.join(q.get('devices') or [])}`",
            f"- max active workers: **{q.get('max_active')}**",
            f"- max pending: **{q.get('max_pending')}**",
            f"- peak throughput (completed/s): **{q.get('peak_throughput')}**",
            f"- samples: {q.get('samples')}",
            "",
        ]
        if q.get("api_cpu_max") is not None or q.get("gpu0_sm_max") is not None:
            parts += [
                "### Host metrics (poll_queue --host-metrics)",
                "",
                f"- API container CPU%: avg **{q.get('api_cpu_avg')}** · max **{q.get('api_cpu_max')}**",
                f"- GPU0 SM%: avg **{q.get('gpu0_sm_avg')}** · max **{q.get('gpu0_sm_max')}**",
                f"- GPU1 SM%: avg **{q.get('gpu1_sm_avg')}** · max **{q.get('gpu1_sm_max')}**",
                "",
            ]
    if nvidia_notes:
        parts += ["## GPU (nvidia-smi)", "", *[f"- {n}" for n in nvidia_notes], ""]
    parts += [
        "## ไฟล์ดิบ",
        "",
        f"- `{idle_path.as_posix()}`",
        f"- `{rush3_path.as_posix()}`",
    ]
    if rush1_path:
        parts.append(f"- `{rush1_path.as_posix()}`")
    if queue_path:
        parts.append(f"- `{queue_path.as_posix()}`")
    parts.append("")
    return "\n".join(parts)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--idle", type=Path, required=True)
    p.add_argument("--rush3", type=Path, required=True)
    p.add_argument("--rush1", type=Path, default=None)
    p.add_argument("--queue", type=Path, default=None)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--title", default="Loadtest capacity — FACE_GPU_WORKERS=2")
    p.add_argument("--workers", type=int, default=2, help="FACE_GPU_WORKERS per API process")
    p.add_argument(
        "--env-note",
        action="append",
        default=[],
        help="Extra environment bullet (repeatable), e.g. code build / flags",
    )
    args = p.parse_args()

    report = build_report(
        title=args.title,
        env_lines=[
            "Host: `10.50.0.117` · URL: `http://10.50.0.117:8880`",
            "GPUs: 2× Quadro RTX 5000 16 GB",
            f"Dual API: `dpu-api` (GPU0) + `dpu-api-gpu1` (GPU1) · `FACE_GPU_WORKERS={args.workers}` each",
            "Client: realistic frames (1280 px, JPEG q70) · detect interval 90 ms",
            "SLO: session p95 ≤ 500 ms · detect p95 ≤ 550 ms · dropped ≤ 5%",
            *args.env_note,
        ],
        idle_path=args.idle,
        rush3_path=args.rush3,
        rush1_path=args.rush1,
        queue_path=args.queue,
        nvidia_notes=[],
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
