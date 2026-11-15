"""Unit tests for SCIM 2.0 provisioning & real-time Incident WebSocket hub."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.models.company_employee import CompanyEmployee
from src.models.department import Department
from src.models.member import Member, StatusType
from src.models.position import Position
from src.services import incident_ws_hub as ws_mod
from src.services import scim_service


class _FakeWs:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.messages: list[str] = []

    async def send_text(self, text: str) -> None:
        if self.fail:
            raise RuntimeError("socket closed")
        self.messages.append(text)


@pytest.mark.asyncio
async def test_incident_ws_hub_broadcast_and_cleanup(monkeypatch):
    hub = ws_mod.IncidentWsHub()
    monkeypatch.setattr(ws_mod, "incident_ws_hub", hub)
    monkeypatch.setattr(ws_mod, "get_redis", lambda: None)

    cid = uuid4()
    good = _FakeWs()
    stale = _FakeWs(fail=True)

    await hub.subscribe(cid, good)  # type: ignore[arg-type]
    await hub.subscribe(cid, stale)  # type: ignore[arg-type]
    assert hub.subscriber_count(cid) == 2

    await ws_mod.publish_incident_event(cid, {"incidentId": "inc-1", "severity": "CRITICAL"})
    assert len(good.messages) == 1
    assert '"inc-1"' in good.messages[0]
    # Stale socket was automatically evicted
    assert hub.subscriber_count(cid) == 1

    await hub.unsubscribe(cid, good)  # type: ignore[arg-type]
    assert hub.subscriber_count(cid) == 0


@pytest.mark.asyncio
async def test_scim_service_create_patch_delete(monkeypatch):
    cid = uuid4()
    dept = Department(departmentId=uuid4(), thName="IT", engName="IT", companyId=cid)
    pos = Position(positionId=uuid4(), thName="Dev", engName="Dev", companyId=cid)

    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # dup check
            MagicMock(scalar_one_or_none=MagicMock(return_value=dept)),  # default dept
            MagicMock(scalar_one_or_none=MagicMock(return_value=pos)),  # default pos
        ]
    )

    created = await scim_service.create_scim_user(
        db,
        cid,
        {
            "userName": "alice.scim",
            "externalId": "EMP-9001",
            "name": {"givenName": "Alice", "familyName": "Smith"},
            "emails": [{"value": "alice@example.com", "primary": True}],
            "active": True,
        },
    )
    assert created["userName"] == "alice.scim"
    assert created["externalId"] == "EMP-9001"
    assert created["active"] is True

    # Patch active=false & givenName
    member = Member(
        memberId=uuid4(),
        username="alice.scim",
        email="alice@example.com",
        passwordHash="x",
        status=StatusType.ENABLE,
    )
    emp = CompanyEmployee(
        company_employeeId=uuid4(),
        memberId=member.memberId,
        companyId=cid,
        departmentId=dept.departmentId,
        positionId=pos.positionId,
        employeeId="EMP-9001",
    )
    db.execute = AsyncMock(
        return_value=MagicMock(first=MagicMock(return_value=(member, emp)))
    )
    patched = await scim_service.patch_scim_user(
        db,
        cid,
        member.memberId,
        {
            "Operations": [
                {"op": "replace", "path": "active", "value": False},
                {"op": "replace", "path": "name.givenName", "value": "Alicia"},
            ]
        },
    )
    assert patched["active"] is False
    assert patched["name"]["givenName"] == "Alicia"

    # Delete triggers PDPA biometric erasure & soft-delete
    erased = AsyncMock(return_value={"erasedEncodings": 0})
    monkeypatch.setattr(scim_service, "erase_member_personal_data", erased)
    db.execute = AsyncMock(
        side_effect=[
            MagicMock(first=MagicMock(return_value=(member, emp))),  # lookup
            MagicMock(scalar=MagicMock(return_value=0)),  # other_active count
        ]
    )
    res = await scim_service.delete_scim_user(db, cid, member.memberId)
    assert res["deleted"] is True
    assert emp.deletedAt is not None
    assert member.status == StatusType.DISABLED
    assert erased.await_count == 1


@pytest.mark.asyncio
async def test_scim_filter_rejects_invalid_syntax():
    db = MagicMock()
    with pytest.raises(HTTPException) as exc:
        await scim_service.list_scim_users(db, uuid4(), filter_str="badFilter")
    assert exc.value.status_code == 400
