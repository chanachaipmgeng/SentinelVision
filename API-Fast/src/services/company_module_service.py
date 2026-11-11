"""Per-company module & post-detection action policy (`modules:{companyId}` in system_setting).

CORE and GOVERNANCE are always on. The five operational modules can be toggled per company.
Defaults keep every module enabled so existing tenants behave like today.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.sentinel import SentinelAccessZone, SentinelEvent
from ..models.system_setting import SystemSetting

ALL_PLATFORM_MODULES = (
    "CORE",
    "ATTENDANCE",
    "ACCESS_CONTROL",
    "WATCHLIST",
    "VISITOR",
    "EVENTS",
    "CCTV",
    "GOVERNANCE",
)
ALWAYS_ON_MODULES = ("CORE", "GOVERNANCE")
TOGGLEABLE_COMPANY_MODULES = (
    "ATTENDANCE",
    "ACCESS_CONTROL",
    "WATCHLIST",
    "VISITOR",
    "EVENTS",
    "CCTV",
)
VALID_STATION_MODES = (
    "ATTENDANCE",
    "ACCESS_CONTROL",
    "WATCHLIST_MONITOR",
    "VISITOR_CHECKIN",
    "EVENT_CHECKIN",
    "UNIFIED_HYBRID",
)
VALID_UNKNOWN_FACE_ACTIONS = ("IGNORE", "LOG_INCIDENT")

# Package → allowed toggleable modules (D5 atop modules:{companyId}).
PACKAGE_PRESETS_MODULES: dict[str, list[str]] = {
    "STARTER": ["ATTENDANCE"],
    "PRO": ["ATTENDANCE", "ACCESS_CONTROL", "WATCHLIST", "VISITOR", "CCTV"],
    "ENTERPRISE": ["ATTENDANCE", "ACCESS_CONTROL", "WATCHLIST", "VISITOR", "EVENTS", "CCTV"],
}

DEFAULT_COMPANY_MODULE_CONFIG: dict[str, Any] = {
    "enabledModules": [
        "ATTENDANCE",
        "ACCESS_CONTROL",
        "WATCHLIST",
        "VISITOR",
        "EVENTS",
        "CCTV",
    ],
    "defaultStationMode": "ATTENDANCE",
    "defaultZoneId": None,
    "defaultEventId": None,
    "packageCode": None,
    "quotas": {
        "maxDevices": None,
        "maxEmployees": None,
        "gpuPriority": 0,
    },
    "scanActionRules": {
        "enableBlacklistSilentAlarm": True,
        "enableVipGreeting": True,
        "enableTtsVoice": True,
        "enableDoorRelayOnAttendance": False,
        "unknownFaceAction": "IGNORE",
    },
    "moduleSettings": {
        "attendance": {"defaultPunchMode": "AUTO", "requireGps": True},
        "accessControl": {"autoLockSeconds": 5, "require2FA": False},
        "watchlist": {"silentAlarmOnPoi": True},
        "visitor": {"defaultPassHours": 12},
        "events": {"showSeatFullscreen": True},
    },
}


def modules_config_key(company_id: str | UUID) -> str:
    return f"modules:{company_id}"


def _clean_uuid(value: Any, *, field: str) -> Optional[str]:
    if value in (None, ""):
        return None
    try:
        return str(UUID(str(value)))
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid UUID for {field}") from None


def _deep_merge(base: dict, overlay: dict) -> dict:
    out = deepcopy(base)
    for key, value in (overlay or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def merge_module_config(stored: Optional[dict]) -> dict:
    """Merge persisted JSON with defaults; always expose alwaysOnModules."""
    merged = _deep_merge(DEFAULT_COMPANY_MODULE_CONFIG, stored if isinstance(stored, dict) else {})
    # Strip always-on modules from enabled list; they are implied separately.
    enabled = []
    for raw in merged.get("enabledModules") or []:
        name = str(raw).strip().upper()
        if name in TOGGLEABLE_COMPANY_MODULES and name not in enabled:
            enabled.append(name)
    if not enabled:
        enabled = list(DEFAULT_COMPANY_MODULE_CONFIG["enabledModules"])
    merged["enabledModules"] = enabled
    mode = str(merged.get("defaultStationMode") or "ATTENDANCE").strip().upper()
    if mode not in VALID_STATION_MODES:
        mode = "ATTENDANCE"
    merged["defaultStationMode"] = mode
    rules = merged.setdefault("scanActionRules", {})
    rules["enableBlacklistSilentAlarm"] = bool(rules.get("enableBlacklistSilentAlarm", True))
    rules["enableVipGreeting"] = bool(rules.get("enableVipGreeting", True))
    rules["enableTtsVoice"] = bool(rules.get("enableTtsVoice", True))
    rules["enableDoorRelayOnAttendance"] = bool(rules.get("enableDoorRelayOnAttendance", False))
    unknown = str(rules.get("unknownFaceAction") or "IGNORE").strip().upper()
    if unknown not in VALID_UNKNOWN_FACE_ACTIONS:
        unknown = "IGNORE"
    rules["unknownFaceAction"] = unknown
    merged["alwaysOnModules"] = list(ALWAYS_ON_MODULES)
    pkg = merged.get("packageCode")
    if pkg not in (None, ""):
        merged["packageCode"] = str(pkg).strip().upper()
    else:
        merged["packageCode"] = None
    raw_quotas = merged.get("quotas")
    quotas = raw_quotas if isinstance(raw_quotas, dict) else {}
    merged["quotas"] = {
        "maxDevices": quotas.get("maxDevices"),
        "maxEmployees": quotas.get("maxEmployees"),
        "gpuPriority": int(quotas.get("gpuPriority") or 0),
    }
    return merged


def normalize_module_config(payload: dict) -> dict:
    """Validate and normalize a PUT body before persistence (no alwaysOnModules stored)."""
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="module-config body must be an object")

    enabled_raw = payload.get("enabledModules")
    if enabled_raw is None:
        enabled_raw = DEFAULT_COMPANY_MODULE_CONFIG["enabledModules"]
    if not isinstance(enabled_raw, list):
        raise HTTPException(status_code=400, detail="enabledModules must be a list")
    enabled: list[str] = []
    for raw in enabled_raw:
        name = str(raw).strip().upper()
        if name in ALWAYS_ON_MODULES:
            continue
        if name not in TOGGLEABLE_COMPANY_MODULES:
            raise HTTPException(status_code=400, detail=f"Unknown or non-toggleable module: {name}")
        if name not in enabled:
            enabled.append(name)

    mode = str(payload.get("defaultStationMode") or "ATTENDANCE").strip().upper()
    if mode not in VALID_STATION_MODES:
        raise HTTPException(
            status_code=400,
            detail=f"defaultStationMode must be one of {', '.join(VALID_STATION_MODES)}",
        )

    rules_in = payload.get("scanActionRules") or {}
    if not isinstance(rules_in, dict):
        raise HTTPException(status_code=400, detail="scanActionRules must be an object")
    defaults_rules = DEFAULT_COMPANY_MODULE_CONFIG["scanActionRules"]
    unknown = str(rules_in.get("unknownFaceAction", defaults_rules["unknownFaceAction"])).strip().upper()
    if unknown not in VALID_UNKNOWN_FACE_ACTIONS:
        raise HTTPException(status_code=400, detail="unknownFaceAction must be IGNORE or LOG_INCIDENT")
    rules = {
        "enableBlacklistSilentAlarm": bool(
            rules_in.get("enableBlacklistSilentAlarm", defaults_rules["enableBlacklistSilentAlarm"])
        ),
        "enableVipGreeting": bool(rules_in.get("enableVipGreeting", defaults_rules["enableVipGreeting"])),
        "enableTtsVoice": bool(rules_in.get("enableTtsVoice", defaults_rules["enableTtsVoice"])),
        "enableDoorRelayOnAttendance": bool(
            rules_in.get("enableDoorRelayOnAttendance", defaults_rules["enableDoorRelayOnAttendance"])
        ),
        "unknownFaceAction": unknown,
    }

    settings_in = payload.get("moduleSettings") or {}
    if not isinstance(settings_in, dict):
        raise HTTPException(status_code=400, detail="moduleSettings must be an object")
    module_settings = _deep_merge(DEFAULT_COMPANY_MODULE_CONFIG["moduleSettings"], settings_in)

    package_code = payload.get("packageCode")
    if package_code not in (None, ""):
        package_code = str(package_code).strip().upper()
        if package_code not in PACKAGE_PRESETS_MODULES:
            raise HTTPException(
                status_code=400,
                detail=f"packageCode must be one of {', '.join(PACKAGE_PRESETS_MODULES)}",
            )
        allowed = set(PACKAGE_PRESETS_MODULES[package_code])
        enabled = [m for m in enabled if m in allowed]
    else:
        package_code = None

    quotas_in_raw = payload.get("quotas") or {}
    if quotas_in_raw is not None and not isinstance(quotas_in_raw, dict):
        raise HTTPException(status_code=400, detail="quotas must be an object")
    quotas_in = quotas_in_raw if isinstance(quotas_in_raw, dict) else {}
    defaults_q = DEFAULT_COMPANY_MODULE_CONFIG["quotas"]
    quotas = {
        "maxDevices": quotas_in.get("maxDevices", defaults_q["maxDevices"]),
        "maxEmployees": quotas_in.get("maxEmployees", defaults_q["maxEmployees"]),
        "gpuPriority": int(quotas_in.get("gpuPriority", defaults_q["gpuPriority"]) or 0),
    }

    return {
        "enabledModules": enabled,
        "defaultStationMode": mode,
        "defaultZoneId": _clean_uuid(payload.get("defaultZoneId"), field="defaultZoneId"),
        "defaultEventId": _clean_uuid(payload.get("defaultEventId"), field="defaultEventId"),
        "packageCode": package_code,
        "quotas": quotas,
        "scanActionRules": rules,
        "moduleSettings": module_settings,
    }


async def _assert_zone_belongs(db: AsyncSession, company_id: UUID, zone_id: Optional[str]) -> None:
    if not zone_id:
        return
    zone = await db.get(SentinelAccessZone, UUID(zone_id))
    if zone is None or zone.companyId != company_id or zone.deletedAt is not None:
        raise HTTPException(status_code=400, detail="defaultZoneId does not belong to this company")


async def _assert_event_belongs(db: AsyncSession, company_id: UUID, event_id: Optional[str]) -> None:
    if not event_id:
        return
    event = await db.get(SentinelEvent, UUID(event_id))
    if event is None or event.companyId != company_id or event.deletedAt is not None:
        raise HTTPException(status_code=400, detail="defaultEventId does not belong to this company")


async def get_company_module_config(db: AsyncSession, company_id: str | UUID) -> dict:
    row = await db.get(SystemSetting, modules_config_key(company_id))
    stored = row.value if row and isinstance(row.value, dict) else None
    return merge_module_config(stored)


async def save_company_module_config(
    db: AsyncSession,
    company_id: str | UUID,
    payload: dict,
) -> dict:
    cid = UUID(str(company_id))
    clean = normalize_module_config(payload)
    await _assert_zone_belongs(db, cid, clean.get("defaultZoneId"))
    await _assert_event_belongs(db, cid, clean.get("defaultEventId"))
    key = modules_config_key(cid)
    row = await db.get(SystemSetting, key)
    if row:
        row.value = clean
    else:
        db.add(SystemSetting(key=key, value=clean))
    await db.commit()
    return merge_module_config(clean)
