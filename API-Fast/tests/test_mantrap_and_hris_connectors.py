"""Tests for Hardware Mantrap Interlock and Native HRIS/Payroll Connectors."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from fastapi import HTTPException
import pytest

from src.controllers.sentinel_controller import check_mantrap_interlock
from src.services.hris_connector_service import format_payroll_for_connector


@pytest.mark.asyncio
async def test_mantrap_interlock_blocks_when_paired_door_open() -> None:
    company_id = uuid.uuid4()
    zone_a = SimpleNamespace(zoneId=uuid.uuid4(), companyId=company_id, name="Airlock Outer", deletedAt=None)
    zone_b = SimpleNamespace(
        zoneId=uuid.uuid4(),
        companyId=company_id,
        name="Airlock Inner",
        deletedAt=None,
        doorOpenSince=datetime.now(timezone.utc),
    )

    db = MagicMock()
    db.get = AsyncMock(return_value=zone_b)

    with patch("src.controllers.sentinel_controller.record_incident", new_callable=AsyncMock) as rec_mock:
        with pytest.raises(HTTPException) as exc_info:
            await check_mantrap_interlock(
                db,
                company_id,
                zone_a,
                zone_b.zoneId,
                subject_name="Operator",
            )
        assert exc_info.value.status_code == 409
        assert exc_info.value.detail["code"] == "MANTRAP_INTERLOCK_ACTIVE"
        rec_mock.assert_awaited_once()
        assert rec_mock.call_args.kwargs["event_type"] == "MANTRAP_INTERLOCK_BLOCKED"


@pytest.mark.asyncio
async def test_mantrap_interlock_allows_when_paired_door_closed() -> None:
    company_id = uuid.uuid4()
    zone_a = SimpleNamespace(zoneId=uuid.uuid4(), companyId=company_id, name="Airlock Outer", deletedAt=None)
    zone_b = SimpleNamespace(
        zoneId=uuid.uuid4(),
        companyId=company_id,
        name="Airlock Inner",
        deletedAt=None,
        doorOpenSince=None,
    )

    db = MagicMock()
    db.get = AsyncMock(return_value=zone_b)

    with patch("src.controllers.sentinel_controller.record_incident", new_callable=AsyncMock) as rec_mock:
        await check_mantrap_interlock(db, company_id, zone_a, zone_b.zoneId)
        rec_mock.assert_not_called()


def _sample_summary() -> dict:
    return {
        "companyId": str(uuid.uuid4()),
        "startDate": "2026-11-01",
        "endDate": "2026-11-15",
        "items": [
            {
                "company_employeeId": str(uuid.uuid4()),
                "employeeId": "EMP-001",
                "employeeName": "Somchai Jaidee",
                "department": "Engineering",
                "presentDays": 10,
                "absentDays": 1,
                "workMinutes": 4800,
                "lateMinutes": 15,
                "leaveHours": 4.0,
                "ot10Minutes": 60,
                "ot15Minutes": 120,
                "ot20Minutes": 0,
                "ot30Minutes": 0,
                "weightedOtHours": 4.0,
            }
        ],
        "total": 1,
    }


def test_hris_connectors_all_formats_and_invalid() -> None:
    summary = _sample_summary()

    sap = format_payroll_for_connector(summary, "SAP_CSV")
    assert sap["connector"] == "SAP_CSV"
    assert sap["contentType"] == "text/csv"
    assert "PERNR,ENAME,KOSTL" in sap["csv"]
    assert "EMP-001,Somchai Jaidee,Engineering" in sap["csv"]

    wd = format_payroll_for_connector(summary, "workday_json")
    assert wd["connector"] == "WORKDAY_JSON"
    assert wd["contentType"] == "application/json"
    assert wd["total"] == 1
    assert wd["workers"][0]["Worker_ID"] == "EMP-001"
    assert wd["workers"][0]["Regular_Hours"] == 80.0

    peak = format_payroll_for_connector(summary, "PEAK_CSV")
    assert peak["connector"] == "PEAK_CSV"
    assert "EmployeeCode,EmployeeName" in peak["csv"]
    assert "EMP-001,Somchai Jaidee" in peak["csv"]

    flow = format_payroll_for_connector(summary, "FLOWACCOUNT_CSV")
    assert flow["connector"] == "FLOWACCOUNT_CSV"
    assert "EmpID,FullName" in flow["csv"]
    assert "EMP-001,Somchai Jaidee" in flow["csv"]

    with pytest.raises(HTTPException) as exc_info:
        format_payroll_for_connector(summary, "UNKNOWN_ERP")
    assert exc_info.value.status_code == 400
