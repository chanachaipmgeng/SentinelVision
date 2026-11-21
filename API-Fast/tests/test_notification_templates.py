"""Tests for notification templates, preview engine, and security event catalog."""
from __future__ import annotations

import pytest
from uuid import uuid4

from src.services.notification_templates import (
    DEFAULT_TEMPLATES,
    EVENT_I18N_KEYS,
    EVENT_SAMPLE_PAYLOADS,
    builtin_template,
    i18n_key_for_event,
    preview_template,
    render_template,
)


def test_render_template_safe_formatting():
    template = "สวัสดี {employeeName} ลงเวลาเข้างานแล้ว เวลา {time}"
    data = {"employeeName": "สมศรี", "time": "08:30 น."}
    assert render_template(template, data) == "สวัสดี สมศรี ลงเวลาเข้างานแล้ว เวลา 08:30 น."

    # Missing key defaults safely to empty string without raising KeyError
    assert render_template("ยินดีต้อนรับ {employeeName} สังกัด {department}", {"employeeName": "สมชาย"}) == "ยินดีต้อนรับ สมชาย สังกัด "


def test_builtin_template_lookup():
    th_tmpl = builtin_template("attendance.checked_in", locale="th", channel="line")
    assert th_tmpl is not None
    assert "{employeeName}" in th_tmpl["bodyTemplate"]
    assert "{time}" in th_tmpl["bodyTemplate"]

    en_tmpl = builtin_template("attendance.checked_in", locale="en", channel="line")
    assert en_tmpl is not None
    assert "checked in at" in en_tmpl["bodyTemplate"]


def test_security_events_catalog():
    # Verify enterprise security events are present in catalog
    assert "sentinel.blacklist_hit" in EVENT_I18N_KEYS
    assert "sentinel.vip_detected" in EVENT_I18N_KEYS
    assert "sentinel.poi_detected" in EVENT_I18N_KEYS
    assert "sentinel.door_alarm" in EVENT_I18N_KEYS
    assert "sentinel.emergency_muster" in EVENT_I18N_KEYS
    assert "attendance.late_arrival" in EVENT_I18N_KEYS

    # Verify matching templates in default list
    keys = {t["eventKey"] for t in DEFAULT_TEMPLATES}
    assert "sentinel.blacklist_hit" in keys
    assert "sentinel.vip_detected" in keys
    assert "sentinel.poi_detected" in keys
    assert "sentinel.door_alarm" in keys
    assert "sentinel.emergency_muster" in keys
    assert "attendance.late_arrival" in keys


def test_preview_template_with_sample_payload():
    assert len(EVENT_SAMPLE_PAYLOADS) >= 5
    # Test previewing blacklist hit template
    tmpl = "ตรวจพบบุคคลต้องห้าม: {personName} ณ {zoneName} เวลา {time}"
    rendered = preview_template(tmpl, "sentinel.blacklist_hit")
    assert "นายบุญมี (Blacklist)" in rendered
    assert "Zone A" in rendered

    # Test preview with custom overrides
    custom_rendered = preview_template(
        tmpl,
        "sentinel.blacklist_hit",
        custom_payload={"personName": "เป้าหมายทดสอบ", "zoneName": "ประตู 2"},
    )
    assert "เป้าหมายทดสอบ" in custom_rendered
    assert "ประตู 2" in custom_rendered


def test_i18n_key_fallback():
    assert i18n_key_for_event("sentinel.blacklist_hit") == "notify.sentinel.blacklist_hit"
    assert i18n_key_for_event("unknown.event") == "notify.event.unknown.event"


@pytest.mark.asyncio
async def test_preview_template_route_mock():
    from unittest.mock import AsyncMock, MagicMock
    from src.models.member import RoleType
    from src.routes.notification_routes import preview_template_route

    company_id = uuid4()
    mock_member = MagicMock()
    mock_member.role = RoleType.ADMIN_SYSTEM
    mock_db = AsyncMock()

    body = {
        "eventKey": "attendance.checked_in",
        "bodyTemplate": "แจ้งเตือน {employeeName} ลงเวลา {time}",
    }

    result = await preview_template_route(
        companyId=company_id,
        body=body,
        member=mock_member,
        db=mock_db,
    )
    assert result["eventKey"] == "attendance.checked_in"
    assert "สมชาย ใจดี" in result["rendered"]
    assert "08:45 น." in result["rendered"]
