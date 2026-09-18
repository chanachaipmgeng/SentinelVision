"""Local disk storage with optional retention. S3 is selected via STORAGE_BACKEND=s3."""
from __future__ import annotations

import time
from pathlib import Path

from ..config.settings import settings

ROOTS = {
    "uploaded_images": Path("uploaded_images"),
    "enrolled_images": Path("enrolled_images"),
    "temp_images": Path("temp_images"),
}


def ensure_dirs() -> None:
    for path in ROOTS.values():
        path.mkdir(exist_ok=True)


def purge_older_than(folder: str, max_age_seconds: int) -> int:
    root = ROOTS[folder]
    if not root.exists():
        return 0
    cutoff = time.time() - max_age_seconds
    removed = 0
    for path in root.iterdir():
        try:
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink()
                removed += 1
        except OSError:
            continue
    return removed


def retention_tick() -> dict:
    if settings.STORAGE_BACKEND not in {"local", "s3"}:
        raise RuntimeError(f"Unknown STORAGE_BACKEND {settings.STORAGE_BACKEND}")
    if settings.STORAGE_BACKEND == "s3":
        # Interface point: plug boto3 here. Local volumes remain the default.
        return {"backend": "s3", "note": "S3 purge not configured; set STORAGE_BACKEND=local"}
    temp = purge_older_than("temp_images", int(settings.TEMP_RETENTION_HOURS) * 3600)
    punches = purge_older_than("uploaded_images", int(settings.IMAGE_RETENTION_DAYS) * 86400)
    return {"backend": "local", "tempRemoved": temp, "uploadsRemoved": punches}
