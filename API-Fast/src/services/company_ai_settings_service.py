"""Per-company AI / CCTV analysis knobs (SystemSetting JSON blob).

Key ``ai:{companyId}`` — bounded face match threshold override and optional
CCTV camera analysis interval. Missing keys fall back to deploy env defaults.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..config.settings import settings
from ..models.system_setting import SystemSetting

# Cosine distance cutoff (lower = stricter). Keep within a safe operational band.
FACE_THRESHOLD_MIN = 0.15
FACE_THRESHOLD_MAX = 0.70
CCTV_INTERVAL_MIN = 10
CCTV_INTERVAL_MAX = 600


def ai_settings_key(company_id: str | UUID) -> str:
    return f"ai:{company_id}"


def default_ai_settings() -> dict[str, Any]:
    return {
        "faceMatchThreshold": float(settings.FACE_RECOGNITION_THRESHOLD),
        "cctvCameraIntervalSeconds": int(settings.WORKER_CCTV_CAMERA_INTERVAL_SECONDS),
        "faceMatchThresholdOverride": False,
        "cctvCameraIntervalOverride": False,
    }


def _clamp_threshold(raw: Any) -> float | None:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if value != value:  # NaN
        return None
    return max(FACE_THRESHOLD_MIN, min(FACE_THRESHOLD_MAX, value))


def _clamp_interval(raw: Any) -> int | None:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    return max(CCTV_INTERVAL_MIN, min(CCTV_INTERVAL_MAX, value))


def _merge_row(row_value: dict | None) -> dict[str, Any]:
    base = default_ai_settings()
    if not isinstance(row_value, dict):
        return base
    thr = _clamp_threshold(row_value.get("faceMatchThreshold"))
    if thr is not None and row_value.get("faceMatchThresholdOverride", True):
        # Legacy rows may store only the number; treat present number as override.
        override = bool(row_value.get("faceMatchThresholdOverride", True))
        if override or "faceMatchThreshold" in row_value:
            base["faceMatchThreshold"] = thr
            base["faceMatchThresholdOverride"] = True
    interval = _clamp_interval(row_value.get("cctvCameraIntervalSeconds"))
    if interval is not None and (
        row_value.get("cctvCameraIntervalOverride", True)
        or "cctvCameraIntervalSeconds" in row_value
    ):
        base["cctvCameraIntervalSeconds"] = interval
        base["cctvCameraIntervalOverride"] = True
    return base


async def get_ai_settings(db: AsyncSession, company_id: UUID | str) -> dict[str, Any]:
    row = await db.get(SystemSetting, ai_settings_key(str(company_id)))
    return _merge_row(row.value if row else None)


async def put_ai_settings(
    db: AsyncSession, company_id: UUID | str, body: dict[str, Any] | None
) -> dict[str, Any]:
    key = ai_settings_key(str(company_id))
    current = await get_ai_settings(db, company_id)
    body = body or {}

    if "faceMatchThresholdOverride" in body:
        current["faceMatchThresholdOverride"] = bool(body["faceMatchThresholdOverride"])
    if "faceMatchThreshold" in body:
        thr = _clamp_threshold(body["faceMatchThreshold"])
        if thr is not None:
            current["faceMatchThreshold"] = thr
            current["faceMatchThresholdOverride"] = True
    if body.get("faceMatchThresholdOverride") is False:
        current["faceMatchThreshold"] = float(settings.FACE_RECOGNITION_THRESHOLD)
        current["faceMatchThresholdOverride"] = False

    if "cctvCameraIntervalOverride" in body:
        current["cctvCameraIntervalOverride"] = bool(body["cctvCameraIntervalOverride"])
    if "cctvCameraIntervalSeconds" in body:
        interval = _clamp_interval(body["cctvCameraIntervalSeconds"])
        if interval is not None:
            current["cctvCameraIntervalSeconds"] = interval
            current["cctvCameraIntervalOverride"] = True
    if body.get("cctvCameraIntervalOverride") is False:
        current["cctvCameraIntervalSeconds"] = int(settings.WORKER_CCTV_CAMERA_INTERVAL_SECONDS)
        current["cctvCameraIntervalOverride"] = False

    # Persist only the override flags + values (defaults stay env-driven when flags off).
    stored: dict[str, bool | float | int] = {
        "faceMatchThresholdOverride": bool(current["faceMatchThresholdOverride"]),
        "cctvCameraIntervalOverride": bool(current["cctvCameraIntervalOverride"]),
    }
    if stored["faceMatchThresholdOverride"]:
        stored["faceMatchThreshold"] = float(current["faceMatchThreshold"])
    if stored["cctvCameraIntervalOverride"]:
        stored["cctvCameraIntervalSeconds"] = int(current["cctvCameraIntervalSeconds"])

    row = await db.get(SystemSetting, key)
    if row:
        row.value = stored
    else:
        db.add(SystemSetting(key=key, value=stored))
    await db.commit()
    return await get_ai_settings(db, company_id)


async def resolve_face_match_threshold(
    db: AsyncSession, company_id: UUID | str | None
) -> float:
    """Effective cosine-distance cutoff for a company (env default when no override)."""
    if company_id is None:
        return float(settings.FACE_RECOGNITION_THRESHOLD)
    cfg = await get_ai_settings(db, company_id)
    if cfg.get("faceMatchThresholdOverride"):
        return float(cfg["faceMatchThreshold"])
    return float(settings.FACE_RECOGNITION_THRESHOLD)


async def resolve_cctv_camera_interval(
    db: AsyncSession, company_id: UUID | str | None
) -> int:
    if company_id is None:
        return max(CCTV_INTERVAL_MIN, int(settings.WORKER_CCTV_CAMERA_INTERVAL_SECONDS))
    cfg = await get_ai_settings(db, company_id)
    if cfg.get("cctvCameraIntervalOverride"):
        return int(cfg["cctvCameraIntervalSeconds"])
    return max(CCTV_INTERVAL_MIN, int(settings.WORKER_CCTV_CAMERA_INTERVAL_SECONDS))
