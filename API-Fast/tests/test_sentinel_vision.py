from datetime import datetime
from uuid import uuid4

from src.models.sentinel import (
    SentinelAccessZone,
    SentinelEvent,
    SentinelIdentity,
    SentinelIncidentLog,
)
from src.routes.sentinel_routes import (
    _bangkok_tz,
    _is_within_schedule,
    _serialize_event,
    _serialize_identity,
    _serialize_incident,
    _serialize_zone,
)
from src.security.middleware import _company_id, _is_kiosk_path_allowed


def test_sentinel_company_id_extraction_and_kiosk_scope():
    cid = str(uuid4())
    assert _company_id(f"/sentinel/company/{cid}/overview") == cid
    assert _company_id(f"/sentinel/company/{cid}/identities") == cid
    assert _company_id(f"/sentinel/company/{cid}/scan") == cid

    # Kiosk tokens can POST /scan and GET /edge-sync or /zones, but CANNOT delete or mutate identities
    assert _is_kiosk_path_allowed("POST", f"/sentinel/company/{cid}/scan") is True
    assert _is_kiosk_path_allowed("GET", f"/sentinel/company/{cid}/edge-sync") is True
    assert _is_kiosk_path_allowed("GET", f"/sentinel/company/{cid}/zones") is True
    assert _is_kiosk_path_allowed("DELETE", f"/sentinel/company/{cid}/identities/123") is False
    assert _is_kiosk_path_allowed("POST", f"/sentinel/company/{cid}/identities") is False


def test_sentinel_access_zone_schedule_window():
    tz = _bangkok_tz()
    morning = datetime(2026, 11, 7, 10, 30, 0, tzinfo=tz)
    late_night = datetime(2026, 11, 7, 23, 15, 0, tzinfo=tz)

    assert _is_within_schedule("08:00", "18:00", morning) is True
    assert _is_within_schedule("08:00", "18:00", late_night) is False
    # Cross-midnight schedule (22:00 -> 06:00)
    assert _is_within_schedule("22:00", "06:00", late_night) is True
    assert _is_within_schedule("22:00", "06:00", morning) is False


def test_sentinel_serializers():
    cid = uuid4()
    ident = SentinelIdentity(
        identityId=uuid4(),
        companyId=cid,
        identityType="BLACKLIST",
        fullName="Test Target",
        severity="CRITICAL",
        alertNote="Do not admit",
        allowedZoneIds=[],
        status="ACTIVE",
    )
    s_ident = _serialize_identity(ident)
    assert s_ident["identityType"] == "BLACKLIST"
    assert s_ident["severity"] == "CRITICAL"
    assert s_ident["hasFaceEnrolled"] is False

    zone = SentinelAccessZone(
        zoneId=uuid4(),
        companyId=cid,
        name="Server Room Gate",
        code="SRV-01",
        stationMode="ACCESS_CONTROL",
        allowedIdentityTypes=["EMPLOYEE"],
        scheduleStart="08:00",
        scheduleEnd="20:00",
        require2FA=True,
        isActive=True,
    )
    s_zone = _serialize_zone(zone)
    assert s_zone["code"] == "SRV-01"
    assert s_zone["require2FA"] is True

    now = datetime.now(_bangkok_tz())
    ev = SentinelEvent(
        eventId=uuid4(),
        companyId=cid,
        name="Sentinel AI Summit",
        locationName="Hall A",
        startAt=now,
        endAt=now,
        capacity=300,
        autoExpireDays=7,
        status="LIVE",
    )
    s_ev = _serialize_event(ev, attendee_count=45, checked_in_count=12)
    assert s_ev["attendeeCount"] == 45
    assert s_ev["checkedInCount"] == 12

    inc = SentinelIncidentLog(
        incidentId=uuid4(),
        companyId=cid,
        eventType="BLACKLIST_ALERT",
        severity="CRITICAL",
        subjectName="Test Target",
        identityType="BLACKLIST",
        zoneName="Main Gate",
        confidencePercent=96.4,
        actionTaken="Silent alarm dispatched",
    )
    s_inc = _serialize_incident(inc)
    assert s_inc["eventType"] == "BLACKLIST_ALERT"
    assert s_inc["confidencePercent"] == 96.4



def _nginx_conf_dir():
    """``docker/nginx`` of the repository checkout; ``None`` inside the API image (only API-Fast is copied)."""
    from pathlib import Path

    for parent in Path(__file__).resolve().parents:
        candidate = parent / "docker" / "nginx"
        if candidate.is_dir():
            return candidate
    return None


def test_nginx_configs_include_sentinel_prefix():
    import pytest

    conf_dir = _nginx_conf_dir()
    if conf_dir is None:
        pytest.skip("docker/nginx not present (tests running from the API image, not a repo checkout)")
    # B4: routing is shared by every gateway variant through snippets/gateway.conf.
    shared = (conf_dir / "snippets" / "gateway.conf").read_text(encoding="utf-8")
    assert "|hr|sentinel|" in shared, "gateway.conf is missing 'sentinel' in FastAPI proxy regex"
    for conf_name in ("default.conf", "default.dual-gpu.conf", "default.quad-gpu.conf", "default.hexa-gpu.conf"):
        text = (conf_dir / conf_name).read_text(encoding="utf-8")
        assert "include /etc/nginx/snippets/gateway.conf;" in text, f"{conf_name} does not include the shared gateway"
