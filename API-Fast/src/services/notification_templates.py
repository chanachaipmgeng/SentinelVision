"""Built-in notification templates + i18n key map (D3).

UI / ngx-translate keys live under ``notify.*`` in ``Web-Manage/src/assets/i18n``.
Template bodies use ``{name}`` placeholders filled from event ``data``.
"""
from __future__ import annotations

from typing import Any, Optional

# eventKey → i18n key prefix (title / body under assets/i18n/{locale}.json)
EVENT_I18N_KEYS: dict[str, str] = {
    "attendance.checked_in": "notify.attendance.checked_in",
    "attendance.checked_out": "notify.attendance.checked_out",
    "attendance.approved": "notify.attendance.approved",
    "attendance.missing": "notify.attendance.missing",
    "import.finished": "notify.import.finished",
    "system.test": "notify.system.test",
    "system.alert": "notify.system.alert",
    "approval.pending": "notify.approval.pending",
    "sentinel.blacklist_hit": "notify.sentinel.blacklist_hit",
}

DEFAULT_TEMPLATES: list[dict[str, Any]] = [
    {
        "eventKey": "attendance.checked_in",
        "locale": "th",
        "channel": "line",
        "subject": "ลงเวลาเข้างาน",
        "bodyTemplate": "{employeeName} ลงเวลาเข้างานแล้ว เวลา {time} ({location})",
    },
    {
        "eventKey": "attendance.checked_in",
        "locale": "en",
        "channel": "line",
        "subject": "Checked in",
        "bodyTemplate": "{employeeName} checked in at {time} ({location})",
    },
    {
        "eventKey": "attendance.checked_out",
        "locale": "th",
        "channel": "line",
        "subject": "ลงเวลาออกงาน",
        "bodyTemplate": "{employeeName} ลงเวลาออกงานแล้ว เวลา {time}",
    },
    {
        "eventKey": "attendance.checked_out",
        "locale": "en",
        "channel": "line",
        "subject": "Checked out",
        "bodyTemplate": "{employeeName} checked out at {time}",
    },
    {
        "eventKey": "attendance.missing",
        "locale": "th",
        "channel": "line",
        "subject": "ยังไม่ลงเวลาเข้างาน",
        "bodyTemplate": "มีพนักงาน {missingCount} คนที่ยังไม่ลงเวลาเข้างาน วันที่ {date}",
    },
    {
        "eventKey": "attendance.missing",
        "locale": "en",
        "channel": "line",
        "subject": "Missing check-in",
        "bodyTemplate": "{missingCount} employees have no check-in on {date}",
    },
    {
        "eventKey": "import.finished",
        "locale": "th",
        "channel": "line",
        "subject": "นำเข้าข้อมูลเสร็จสิ้น",
        "bodyTemplate": "งานนำเข้า {jobId} เสร็จแล้ว สำเร็จ {ok} / ล้มเหลว {failed}",
    },
    {
        "eventKey": "import.finished",
        "locale": "en",
        "channel": "line",
        "subject": "Import finished",
        "bodyTemplate": "Import job {jobId} finished: ok={ok} failed={failed}",
    },
    {
        "eventKey": "system.test",
        "locale": "th",
        "channel": "line",
        "subject": "ทดสอบการแจ้งเตือน",
        "bodyTemplate": "ข้อความทดสอบจาก DPU Attendance",
    },
    {
        "eventKey": "system.test",
        "locale": "en",
        "channel": "line",
        "subject": "Notification test",
        "bodyTemplate": "DPU Attendance notification test",
    },
]


def render_template(body_template: str, data: Optional[dict[str, Any]] = None) -> str:
    """Safe ``str.format_map`` — missing keys become empty string."""
    class _Safe(dict):
        def __missing__(self, key: str) -> str:  # noqa: D105
            return ""

    return (body_template or "").format_map(_Safe(data or {}))


def builtin_template(
    event_key: str,
    *,
    locale: str = "th",
    channel: str = "line",
) -> Optional[dict[str, Any]]:
    locale_norm = (locale or "th").lower()[:2]
    for row in DEFAULT_TEMPLATES:
        if (
            row["eventKey"] == event_key
            and row["locale"] == locale_norm
            and row["channel"] == channel
        ):
            return row
    for row in DEFAULT_TEMPLATES:
        if row["eventKey"] == event_key and row["channel"] == channel:
            return row
    return None


def i18n_key_for_event(event_key: str) -> str:
    return EVENT_I18N_KEYS.get(event_key, f"notify.event.{event_key}")
