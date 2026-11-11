"""Company incident SLA policy (SystemSetting JSON blob).

Key ``incident-sla:{companyId}`` — default 15 minutes for OPEN high-severity
(CRITICAL / WARNING) incidents when ``slaDueAt`` is stamped at create time.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.system_setting import SystemSetting

DEFAULT_SLA_MINUTES_HIGH = 15
HIGH_SEVERITIES = frozenset({"CRITICAL", "WARNING"})


def incident_sla_key(company_id: str | UUID) -> str:
    return f"incident-sla:{company_id}"


def default_incident_sla() -> dict[str, int]:
    return {"incidentSlaMinutesHigh": DEFAULT_SLA_MINUTES_HIGH}


async def get_incident_sla_settings(
    db: AsyncSession, company_id: UUID | str
) -> dict[str, int]:
    row = await db.get(SystemSetting, incident_sla_key(str(company_id)))
    base = default_incident_sla()
    if row and isinstance(row.value, dict):
        raw = row.value.get("incidentSlaMinutesHigh")
        try:
            minutes = int(raw) if raw is not None else -1
            if minutes >= 0:
                base["incidentSlaMinutesHigh"] = minutes
        except (TypeError, ValueError):
            pass
    return base


async def put_incident_sla_settings(
    db: AsyncSession, company_id: UUID | str, body: dict[str, Any] | None
) -> dict[str, int]:
    key = incident_sla_key(str(company_id))
    current = await get_incident_sla_settings(db, company_id)
    if body and "incidentSlaMinutesHigh" in body:
        try:
            minutes = max(0, int(body["incidentSlaMinutesHigh"]))
            current["incidentSlaMinutesHigh"] = minutes
        except (TypeError, ValueError):
            pass
    row = await db.get(SystemSetting, key)
    if row:
        row.value = current
    else:
        db.add(SystemSetting(key=key, value=current))
    await db.commit()
    return current


def is_high_severity(severity: str | None) -> bool:
    return str(severity or "").strip().upper() in HIGH_SEVERITIES
