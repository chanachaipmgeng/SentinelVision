#!/usr/bin/env python3
"""Download / export YOLOv8n ONNX for Phase 6D people counting.

Prefer a direct ONNX asset when available; otherwise export via ultralytics
(``pip install ultralytics`` once on the build machine).

  python scripts/download_yolov8n_onnx.py --out API-Fast/models/yolov8n.onnx
"""
from __future__ import annotations

import argparse
import shutil
import sys
import urllib.request
from pathlib import Path

# Community / release mirrors occasionally host pre-exported ONNX; try then fall back.
ONNX_CANDIDATES = [
    # Placeholder — Ultralytics does not always publish ONNX on GitHub releases.
]


def export_via_ultralytics(out: Path) -> None:
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit(
            "ultralytics not installed. Run: pip install ultralytics\n"
            f"Original import error: {exc}"
        ) from exc
    model = YOLO("yolov8n.pt")
    exported = model.export(format="onnx", imgsz=640, simplify=True)
    src = Path(str(exported))
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, out)
    print(f"Exported {out} ({out.stat().st_size} bytes)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("API-Fast/models/yolov8n.onnx"),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing file",
    )
    args = parser.parse_args()
    out: Path = args.out
    if out.is_file() and not args.force:
        print(f"Already exists: {out} ({out.stat().st_size} bytes)")
        return 0

    for url in ONNX_CANDIDATES:
        try:
            out.parent.mkdir(parents=True, exist_ok=True)
            print(f"Downloading {url} …")
            urllib.request.urlretrieve(url, out)
            print(f"Saved {out}")
            return 0
        except Exception as exc:  # noqa: BLE001
            print(f"download failed: {exc}", file=sys.stderr)

    print("Falling back to ultralytics export …")
    export_via_ultralytics(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
