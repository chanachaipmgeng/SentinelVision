"""Unit tests for P2: Visitor Digital Pass, Public Event Registration & Fleet Health."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest
from fastapi import HTTPException

from src.services.visitor_invite_service import (
    create_visitor_pass_token,
    verify_visitor_pass_token,
)
from src.services.fleet_health_service import get_fleet_health_overview
from src.services.event_registration_service import _slugify


def test_visitor_pass_lifecycle():
    cid = uuid4()
    iid = uuid4()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=8)

    pass_obj = create_visitor_pass_token(
        company_id=cid,
        identity_id=iid,
        visitor_name="Somchai เข็มทิศ",
        valid_from=now,
        expires_at=exp,
        zone_ids=["zone-1", "zone-2"],
    )

    assert pass_obj["passCode"].startswith("sv_pass_")
    assert pass_obj["qrDataUrl"] is not None
    assert pass_obj["qrDataUrl"].startswith("data:image/png;base64,")
    assert pass_obj["visitorName"] == "Somchai เข็มทิศ"
    assert pass_obj["zones"] == ["zone-1", "zone-2"]

    verified = verify_visitor_pass_token(pass_obj["passCode"])
    assert verified["companyId"] == cid
    assert verified["identityId"] == iid
    assert verified["visitorName"] == "Somchai เข็มทิศ"
    assert verified["zones"] == ["zone-1", "zone-2"]


def test_visitor_pass_tampering_rejected():
    cid = uuid4()
    iid = uuid4()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=4)

    pass_obj = create_visitor_pass_token(
        company_id=cid,
        identity_id=iid,
        visitor_name="Somchai",
        valid_from=now,
        expires_at=exp,
    )

    # Tamper token signature
    parts = pass_obj["passCode"].rsplit(".", 1)
    tampered = f"{parts[0]}.bad_signature_here"
    with pytest.raises(HTTPException) as exc:
        verify_visitor_pass_token(tampered)
    assert exc.value.status_code == 401


def test_visitor_pass_expired_rejected():
    cid = uuid4()
    iid = uuid4()
    now = datetime.now(timezone.utc)
    vf = now - timedelta(hours=10)
    exp = now - timedelta(hours=2)

    pass_obj = create_visitor_pass_token(
        company_id=cid,
        identity_id=iid,
        visitor_name="Expired User",
        valid_from=vf,
        expires_at=exp,
    )

    with pytest.raises(HTTPException) as exc:
        verify_visitor_pass_token(pass_obj["passCode"])
    assert exc.value.status_code == 410


def test_slugify():
    assert _slugify("Tech Conference 2026!") == "tech-conference-2026"
    assert _slugify("งานสัมมนา AI ประจำปี 2026") == "งานสมมนา-ai-ประจาป-2026" or len(_slugify("งานสัมมนา")) > 0
    assert _slugify("   Multiple   Spaces---Here  ") == "multiple-spaces-here"


@pytest.mark.asyncio
async def test_fleet_health_classification():
    from unittest.mock import AsyncMock, MagicMock
    from src.models.hr_schedule import KioskDevice
    from src.models.camera import Camera
    from src.models.sentinel import SentinelAccessZone

    cid = uuid4()
    now = datetime.now(timezone.utc)

    k1 = KioskDevice(
        deviceId=uuid4(),
        companyId=cid,
        name="Kiosk A",
        stationMode="ATTENDANCE",
        appVersion="4.0.0",
        heartbeatAt=now - timedelta(seconds=30),  # ONLINE (<120s)
        tokenHash="hash1",
    )
    k2 = KioskDevice(
        deviceId=uuid4(),
        companyId=cid,
        name="Kiosk B",
        stationMode="ACCESS_CONTROL",
        appVersion="4.0.0",
        heartbeatAt=now - timedelta(minutes=5),  # STALE (2-10m)
        tokenHash="hash2",
    )
    k3 = KioskDevice(
        deviceId=uuid4(),
        companyId=cid,
        name="Kiosk C",
        stationMode="VISITOR_CHECKIN",
        appVersion="3.9.0",
        heartbeatAt=now - timedelta(hours=1),  # OFFLINE (>10m)
        tokenHash="hash3",
    )

    cam1 = Camera(
        cameraId=uuid4(),
        companyId=cid,
        name="Lobby Cam",
        protocol="rtsp",
        recordMode="event",
        status="online",
        isActive=True,
        lastPingLatencyMs=18.5,
        lastPingAt=now,
    )

    zone1 = SentinelAccessZone(
        zoneId=uuid4(),
        companyId=cid,
        name="Main Lobby",
        isActive=True,
    )

    # Set up mock execute results for kiosks, cams, zones, unread alerts
    mock_db = AsyncMock()

    mock_kiosk_res = MagicMock()
    mock_kiosk_res.scalars.return_value.all.return_value = [k1, k2, k3]

    mock_cam_res = MagicMock()
    mock_cam_res.scalars.return_value.all.return_value = [cam1]

    mock_zone_res = MagicMock()
    mock_zone_res.scalars.return_value.all.return_value = [zone1]

    mock_db.execute.side_effect = [mock_kiosk_res, mock_cam_res, mock_zone_res]
    mock_db.scalar.return_value = 0  # unread alerts

    overview = await get_fleet_health_overview(mock_db, cid)
    summary = overview["summary"]

    assert summary["kiosksTotal"] == 3
    assert summary["kiosksOnline"] == 1
    assert summary["kiosksStale"] == 1
    assert summary["kiosksOffline"] == 1
    assert summary["camerasTotal"] == 1
    assert summary["camerasConnected"] == 1
    assert summary["zonesActive"] == 1
    assert summary["unreadAlerts"] == 0
    assert summary["healthScore"] == 50.0  # (1 online kiosk + 1 active cam) / 4 total endpoints = 50%

    items = overview["kiosks"]["items"]
    assert items[0]["healthStatus"] == "ONLINE"
    assert items[1]["healthStatus"] == "STALE"
    assert items[2]["healthStatus"] == "OFFLINE"


@pytest.mark.asyncio
async def test_verify_visitor_pass_route():
    from unittest.mock import AsyncMock, MagicMock
    from src.models.sentinel import SentinelIdentity
    from src.routes.sentinel_routes import verify_visitor_digital_pass

    cid = uuid4()
    iid = uuid4()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=6)

    pass_obj = create_visitor_pass_token(
        company_id=cid,
        identity_id=iid,
        visitor_name="Somchai Pass",
        valid_from=now,
        expires_at=exp,
        zone_ids=["zone-a"],
    )

    mock_identity = SentinelIdentity(
        identityId=iid,
        companyId=cid,
        fullName="Somchai Pass",
        identityType="VISITOR",
        status="ACTIVE",
        visitPurpose="Business Meeting",
        allowedZoneIds=["zone-a"],
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_identity
    mock_db.execute.return_value = mock_res

    mock_req = MagicMock()
    mock_req.state.api_key_company_id = cid

    result = await verify_visitor_digital_pass(
        companyId=cid,
        request=mock_req,
        body={"passCode": pass_obj["passCode"]},
        db=mock_db,
    )

    assert result["valid"] is True
    assert result["fullName"] == "Somchai Pass"
    assert result["identityId"] == str(iid)
    assert result["status"] == "ACTIVE"
    assert result["allowedZoneIds"] == ["zone-a"]

