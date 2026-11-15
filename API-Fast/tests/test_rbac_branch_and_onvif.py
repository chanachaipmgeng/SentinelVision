"""Unit tests for Branch-scoped RBAC (allowed_location_ids) and ONVIF WS-Discovery/PTZ."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.models.camera import Camera
from src.models.company_employee import CompanyEmployee, CompanyRoleType
from src.models.member import Member, RoleType
from src.services import onvif_service, rbac_service


@pytest.mark.asyncio
async def test_allowed_location_ids_unrestricted_vs_branch_scoped(monkeypatch):
    cid = uuid4()
    branch_id = uuid4()

    sys_admin = Member(memberId=uuid4(), username="sa", email="sa@x", passwordHash="x", role=RoleType.ADMIN_SYSTEM)
    assert await rbac_service.allowed_location_ids(MagicMock(), sys_admin, cid) is None

    # Branch-scoped manager with locationId
    mgr = Member(memberId=uuid4(), username="mgr", email="mgr@x", passwordHash="x", role=RoleType.MEMBER)
    emp = CompanyEmployee(
        company_employeeId=uuid4(),
        memberId=mgr.memberId,
        companyId=cid,
        departmentId=uuid4(),
        positionId=uuid4(),
        locationId=branch_id,
        companyRoleType=CompanyRoleType.EMP,
    )
    monkeypatch.setattr(rbac_service, "get_company_employment", AsyncMock(return_value=emp))
    monkeypatch.setattr(rbac_service, "roles_for_member", AsyncMock(return_value={"MANAGER"}))
    scoped = await rbac_service.allowed_location_ids(MagicMock(), mgr, cid)
    assert scoped == {branch_id}

    # HR_ADMIN is unrestricted across branches
    monkeypatch.setattr(rbac_service, "roles_for_member", AsyncMock(return_value={"HR_ADMIN"}))
    assert await rbac_service.allowed_location_ids(MagicMock(), mgr, cid) is None


def test_parse_ws_discovery_response_extracts_camera_fields():
    xml = (
        b'<?xml version="1.0" encoding="UTF-8"?>'
        b'<e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope" '
        b'xmlns:w="http://schemas.xmlsoap.org/ws/2004/08/addressing" '
        b'xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery">'
        b"<e:Body><d:ProbeMatches><d:ProbeMatch>"
        b"<w:EndpointReference><w:Address>urn:uuid:cam-123</w:Address></w:EndpointReference>"
        b"<d:Scopes>onvif://www.onvif.org/name/Lobby%20Gate onvif://www.onvif.org/hardware/IPC-4K</d:Scopes>"
        b"<d:XAddrs>http://192.168.1.55/onvif/device_service</d:XAddrs>"
        b"</d:ProbeMatch></d:ProbeMatches></e:Body></e:Envelope>"
    )
    parsed = onvif_service.parse_ws_discovery_response(xml, "192.168.1.55")
    assert parsed is not None
    assert parsed["ip"] == "192.168.1.55"
    assert parsed["name"] == "Lobby Gate"
    assert parsed["hardware"] == "IPC-4K"
    assert parsed["onvifServiceUrl"] == "http://192.168.1.55/onvif/device_service"


def test_ptz_envelope_and_loopback_guard():
    cam = Camera(
        cameraId=uuid4(),
        companyId=uuid4(),
        name="Loopback",
        streamUrl="rtsp://127.0.0.1:554/stream1",
    )
    with pytest.raises(HTTPException) as exc:
        onvif_service._resolve_ptz_endpoint(cam)
    assert exc.value.status_code == 400

    move_xml = onvif_service.build_ptz_soap_envelope(action="move", pan=2.5, tilt=-0.5, zoom=0.25)
    assert "<tptz:ContinuousMove>" in move_xml
    assert 'x="1.000" y="-0.500"' in move_xml

    stop_xml = onvif_service.build_ptz_soap_envelope(action="stop")
    assert "<tptz:Stop>" in stop_xml
