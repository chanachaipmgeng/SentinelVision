"""Per-company admin SPA session policy (SystemSetting JSON blob).

Key ``session:{companyId}`` — idle timeout minutes for automatic logout.
``0`` disables idle logout (default, preserves prior behaviour).
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.system_setting import SystemSetting

IDLE_TIMEOUT_MIN = 0
IDLE_TIMEOUT_MAX = 480  # 8 hours
DEFAULT_IDLE_TIMEOUT_MINUTES = 0


def session_settings_key(company_id: str | UUID) -> str:
    return f"session:{company_id}"


def default_session_settings() -> dict[str, int]:
    return {"idleTimeoutMinutes": DEFAULT_IDLE_TIMEOUT_MINUTES}


def _clamp_idle(raw: Any) -> int | None:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return max(IDLE_TIMEOUT_MIN, min(IDLE_TIMEOUT_MAX, value))


async def get_session_settings(
    db: AsyncSession, company_id: UUID | str
) -> dict[str, int]:
    row = await db.get(SystemSetting, session_settings_key(str(company_id)))
    base = default_session_settings()
    if row and isinstance(row.value, dict):
        minutes = _clamp_idle(row.value.get("idleTimeoutMinutes"))
        if minutes is not None:
            base["idleTimeoutMinutes"] = minutes
    return base


async def put_session_settings(
    db: AsyncSession, company_id: UUID | str, body: dict[str, Any] | None
) -> dict[str, int]:
    key = session_settings_key(str(company_id))
    current = await get_session_settings(db, company_id)
    if body and "idleTimeoutMinutes" in body:
        minutes = _clamp_idle(body["idleTimeoutMinutes"])
        if minutes is not None:
            current["idleTimeoutMinutes"] = minutes
    row = await db.get(SystemSetting, key)
    if row:
        row.value = current
    else:
        db.add(SystemSetting(key=key, value=current))
    await db.commit()
    return current
