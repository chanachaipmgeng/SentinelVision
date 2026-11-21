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
    "attendance.late_arrival": "notify.attendance.late_arrival",
    "import.finished": "notify.import.finished",
    "system.test": "notify.system.test",
    "system.alert": "notify.system.alert",
    "approval.pending": "notify.approval.pending",
    "sentinel.blacklist_hit": "notify.sentinel.blacklist_hit",
    "sentinel.vip_detected": "notify.sentinel.vip_detected",
    "sentinel.poi_detected": "notify.sentinel.poi_detected",
    "sentinel.door_alarm": "notify.sentinel.door_alarm",
    "sentinel.emergency_muster": "notify.sentinel.emergency_muster",
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
        "eventKey": "attendance.late_arrival",
        "locale": "th",
        "channel": "line",
        "subject": "แจ้งเตือนเข้างานสาย",
        "bodyTemplate": "พนักงาน {employeeName} เข้างานสาย {lateMinutes} นาที ({shiftName}) เวลา {time}",
    },
    {
        "eventKey": "attendance.late_arrival",
        "locale": "en",
        "channel": "line",
        "subject": "Late Check-in Alert",
        "bodyTemplate": "{employeeName} checked in late by {lateMinutes} mins ({shiftName}) at {time}",
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
        "eventKey": "sentinel.blacklist_hit",
        "locale": "th",
        "channel": "line",
        "subject": "🚨 แจ้งเตือนพบบุคคลต้องห้าม (Blacklist)",
        "bodyTemplate": "ตรวจพบบุคคลต้องห้าม: {personName} ความแม่นยำ {similarity} ณ {zoneName} ({cameraName}) เวลา {time}",
    },
    {
        "eventKey": "sentinel.blacklist_hit",
        "locale": "en",
        "channel": "line",
        "subject": "🚨 Blacklist Individual Detected",
        "bodyTemplate": "Blacklist match: {personName} ({similarity}) at {zoneName} ({cameraName}) time {time}",
    },
    {
        "eventKey": "sentinel.vip_detected",
        "locale": "th",
        "channel": "line",
        "subject": "🌟 ต้อนรับแขก VIP",
        "bodyTemplate": "ต้อนรับแขก VIP: {personName} เดินทางถึง {zoneName} เวลา {time}",
    },
    {
        "eventKey": "sentinel.vip_detected",
        "locale": "en",
        "channel": "line",
        "subject": "🌟 VIP Guest Arrival",
        "bodyTemplate": "VIP Guest {personName} has arrived at {zoneName} ({time})",
    },
    {
        "eventKey": "sentinel.poi_detected",
        "locale": "th",
        "channel": "line",
        "subject": "⚠️ แจ้งเตือนบุคคลเฝ้าระวัง (POI)",
        "bodyTemplate": "พบบุคคลเฝ้าระวัง: {personName} ณ {zoneName} เวลา {time}",
    },
    {
        "eventKey": "sentinel.poi_detected",
        "locale": "en",
        "channel": "line",
        "subject": "⚠️ Person of Interest (POI) Detected",
        "bodyTemplate": "POI detected: {personName} at {zoneName} ({time})",
    },
    {
        "eventKey": "sentinel.door_alarm",
        "locale": "th",
        "channel": "line",
        "subject": "🚪 สัญญาณเตือนระบบประตู (Access Alarm)",
        "bodyTemplate": "แจ้งเตือนประตู: {doorName} สถานะ {alarmType} เวลา {time}",
    },
    {
        "eventKey": "sentinel.door_alarm",
        "locale": "en",
        "channel": "line",
        "subject": "🚪 Door Access Alarm",
        "bodyTemplate": "Access Alarm on {doorName}: {alarmType} at {time}",
    },
    {
        "eventKey": "sentinel.emergency_muster",
        "locale": "th",
        "channel": "line",
        "subject": "🦺 รายงานจุดรวมพลฉุกเฉิน (Muster Roll)",
        "bodyTemplate": "จุดรวมพล {zoneName}: อพยพแล้ว {evacuatedCount} คน / ยังไม่พบ {missingCount} คน ณ เวลา {time}",
    },
    {
        "eventKey": "sentinel.emergency_muster",
        "locale": "en",
        "channel": "line",
        "subject": "🦺 Emergency Muster Status",
        "bodyTemplate": "Muster Zone {zoneName}: Evacuated {evacuatedCount} / Unaccounted {missingCount} at {time}",
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

EVENT_SAMPLE_PAYLOADS: dict[str, dict[str, Any]] = {
    "attendance.checked_in": {
        "employeeName": "สมชาย ใจดี",
        "time": "08:45 น.",
        "location": "อาคาร 1 ประตูหน้า",
    },
    "attendance.checked_out": {
        "employeeName": "สมชาย ใจดี",
        "time": "17:30 น.",
    },
    "attendance.late_arrival": {
        "employeeName": "สมชาย ใจดี",
        "shiftName": "กะเช้า (08:30 - 17:30)",
        "lateMinutes": "25",
        "time": "08:55 น.",
    },
    "attendance.missing": {
        "missingCount": "5",
        "date": "21/11/2026",
    },
    "sentinel.blacklist_hit": {
        "personName": "นายบุญมี (Blacklist)",
        "zoneName": "Zone A - ทางเข้าหลัก",
        "cameraName": "CAM-01-ENTRANCE",
        "time": "13:45 น.",
        "similarity": "96.4%",
    },
    "sentinel.vip_detected": {
        "personName": "คุณวิชัย (VIP Guest)",
        "zoneName": "Lobby VIP Lounge",
        "time": "10:15 น.",
    },
    "sentinel.poi_detected": {
        "personName": "บุคคลเฝ้าระวัง #402",
        "zoneName": "ลานจอดรถชั้นใต้ดิน B1",
        "time": "14:20 น.",
    },
    "sentinel.door_alarm": {
        "doorName": "ประตูหนีไฟ ชั้น 3",
        "alarmType": "Door Forced Open (งัดแงะประตู)",
        "time": "02:15 น.",
    },
    "sentinel.emergency_muster": {
        "zoneName": "จุดรวมพล 1 (สนามฟุตบอล)",
        "evacuatedCount": "148",
        "missingCount": "3",
        "time": "11:00 น.",
    },
    "import.finished": {
        "jobId": "imp_9128",
        "ok": "150",
        "failed": "0",
    },
    "system.test": {},
}


def render_template(body_template: str, data: Optional[dict[str, Any]] = None) -> str:
    """Safe ``str.format_map`` — missing keys become empty string."""
    class _Safe(dict):
        def __missing__(self, key: str) -> str:  # noqa: D105
            return ""

    return (body_template or "").format_map(_Safe(data or {}))


def preview_template(
    body_template: str,
    event_key: str,
    custom_payload: Optional[dict[str, Any]] = None,
) -> str:
    """Render a template with sample payloads for instant preview in UI/API."""
    merged = dict(EVENT_SAMPLE_PAYLOADS.get(event_key, {}))
    if custom_payload:
        merged.update(custom_payload)
    return render_template(body_template, merged)


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
