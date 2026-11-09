"""Company incident SLA settings blob (incident-sla:{companyId})."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.services import incident_sla_service as sla  # noqa: E402


COMPANY_ID = uuid4()


@pytest.mark.asyncio
async def test_default_sla_when_missing():
    db = AsyncMock()
    db.get = AsyncMock(return_value=None)
    out = await sla.get_incident_sla_settings(db, COMPANY_ID)
    assert out == {"incidentSlaMinutesHigh": 15}


@pytest.mark.asyncio
async def test_put_and_clamp_minutes():
    db = AsyncMock()
    stored = MagicMock()
    stored.value = {"incidentSlaMinutesHigh": 15}
    db.get = AsyncMock(return_value=stored)
    db.commit = AsyncMock()
    db.add = MagicMock()

    out = await sla.put_incident_sla_settings(
        db, COMPANY_ID, {"incidentSlaMinutesHigh": 30}
    )
    assert out["incidentSlaMinutesHigh"] == 30
    assert stored.value["incidentSlaMinutesHigh"] == 30
    db.commit.assert_awaited()

    out2 = await sla.put_incident_sla_settings(
        db, COMPANY_ID, {"incidentSlaMinutesHigh": -5}
    )
    assert out2["incidentSlaMinutesHigh"] == 0


def test_high_severity_helpers():
    assert sla.is_high_severity("CRITICAL")
    assert sla.is_high_severity("warning")
    assert not sla.is_high_severity("INFO")
