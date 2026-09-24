#!/usr/bin/env python3
"""Estimate kiosk inbound bandwidth from known frame sizes + concurrent screens.

Uses measured frame bytes from kiosk_load prepare (~1280px jpeg q70) and
gated detect interval (default 600 ms).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

CACHE = Path(__file__).resolve().parent / ".cache"
FACE = CACHE / "sample_face.jpg"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--frame-bytes", type=int, default=0, help="0 = use sample_face or 128830")
    p.add_argument("--kiosks", default="24,32")
    p.add_argument("--detect-interval-ms", type=float, default=600.0)
    p.add_argument("--out", type=Path, default=CACHE / "summary-bandwidth.json")
    args = p.parse_args()

    frame = args.frame_bytes
    if frame <= 0:
        if FACE.is_file():
            # detect frame is slightly larger than raw face; use measured ~128830 from prior runs
            frame = 128830
        else:
            frame = 128830

    interval_s = args.detect_interval_ms / 1000.0
    rows = []
    for k in [int(x) for x in args.kiosks.split(",") if x.strip()]:
        bytes_per_s = k * frame / interval_s
        rows.append(
            {
                "kiosks": k,
                "frame_bytes": frame,
                "detect_interval_ms": args.detect_interval_ms,
                "inbound_MBps": round(bytes_per_s / (1024 * 1024), 2),
                "inbound_Mbps": round(bytes_per_s * 8 / (1024 * 1024), 2),
                "note": "detect frames only (identify/checkin crop is smaller/rarer)",
            }
        )
    out = {"rows": rows}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
