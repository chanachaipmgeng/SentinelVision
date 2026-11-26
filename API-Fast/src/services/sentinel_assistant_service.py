"""Company-scoped Security & HR AI Copilot (SSE streaming)."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, AsyncIterator
from uuid import UUID
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.settings import settings
from ..models.attendance_daily import AttendanceDaily, AttendanceDailyStatus
from ..models.camera import Camera
from ..models.sentinel import (
    SentinelAccessZone,
    SentinelIdentity,
    SentinelIncidentLog,
)

BANGKOK_TZ = ZoneInfo("Asia/Bangkok")


def _sse(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def collect_company_snapshot(db: AsyncSession, company_id: UUID) -> dict[str, Any]:
    """Gather real-time company-scoped operational metrics for grounding."""
    today = datetime.now(BANGKOK_TZ).date()

    present_count = (
        await db.execute(
            select(func.count())
            .select_from(AttendanceDaily)
            .where(
                AttendanceDaily.companyId == company_id,
                AttendanceDaily.workDate == today,
                AttendanceDaily.status == AttendanceDailyStatus.PRESENT,
            )
        )
    ).scalar_one()

    open_incidents = (
        await db.execute(
            select(func.count())
            .select_from(SentinelIncidentLog)
            .where(
                SentinelIncidentLog.companyId == company_id,
                SentinelIncidentLog.status == "OPEN",
            )
        )
    ).scalar_one()

    recent_incidents = (
        await db.execute(
            select(SentinelIncidentLog)
            .where(SentinelIncidentLog.companyId == company_id)
            .order_by(SentinelIncidentLog.occurredAt.desc())
            .limit(5)
        )
    ).scalars().all()

    cam_rows = (
        await db.execute(
            select(Camera.status, func.count())
            .where(Camera.companyId == company_id, Camera.deletedAt.is_(None))
            .group_by(Camera.status)
        )
    ).all()
    camera_stats = {str(status): int(cnt) for status, cnt in cam_rows}

    active_zones = (
        await db.execute(
            select(func.count())
            .select_from(SentinelAccessZone)
            .where(
                SentinelAccessZone.companyId == company_id,
                SentinelAccessZone.deletedAt.is_(None),
                SentinelAccessZone.isActive.is_(True),
            )
        )
    ).scalar_one()

    watchlist_count = (
        await db.execute(
            select(func.count())
            .select_from(SentinelIdentity)
            .where(
                SentinelIdentity.companyId == company_id,
                SentinelIdentity.deletedAt.is_(None),
                SentinelIdentity.status == "ACTIVE",
                SentinelIdentity.identityType.in_(["BLACKLIST", "POI"]),
            )
        )
    ).scalar_one()

    return {
        "workDate": today.isoformat(),
        "presentToday": int(present_count or 0),
        "openIncidents": int(open_incidents or 0),
        "activeZones": int(active_zones or 0),
        "activeWatchlist": int(watchlist_count or 0),
        "camerasByStatus": camera_stats,
        "recentIncidents": [
            {
                "eventType": inc.eventType,
                "severity": inc.severity,
                "status": inc.status,
                "subject": inc.subjectName or "-",
                "zone": inc.zoneName or "-",
                "occurredAt": inc.occurredAt.astimezone(BANGKOK_TZ).strftime("%Y-%m-%d %H:%M"),
            }
            for inc in recent_incidents
        ],
    }


def _fallback_answer(question: str, snap: dict[str, Any]) -> str:
    cams = snap["camerasByStatus"]
    online = cams.get("online", 0)
    total_cams = sum(cams.values())
    lines = [
        f"สรุปสถานะองค์กรประจำวันที่ {snap['workDate']} (Asia/Bangkok):",
        f"• พนักงานลงเวลาเข้างานวันนี้ (PRESENT): {snap['presentToday']} คน",
        f"• เหตุการณ์ที่ยังเปิดอยู่ (Open Incidents): {snap['openIncidents']} รายการ",
        f"• โซน Access Control ที่เปิดใช้งาน: {snap['activeZones']} โซน | Watchlist/Blacklist: {snap['activeWatchlist']} รายการ",
        f"• กล้อง CCTV: ออนไลน์ {online}/{total_cams} ตัว",
    ]
    if snap["recentIncidents"]:
        lines.append("\nเหตุการณ์ล่าสุด:")
        for inc in snap["recentIncidents"][:3]:
            lines.append(
                f"- [{inc['severity']}] {inc['eventType']} ({inc['subject']}) @ {inc['zone']} เวลา {inc['occurredAt']}"
            )
    if question.strip():
        lines.append("\n(หมายเหตุ: ระบบทำงานในโหมดสรุปข้อมูลสดจากฐานข้อมูล — ตั้งค่า GOOGLE_API_KEY เพื่อเปิดใช้ Gemini Flash เต็มรูปแบบ)")
    return "\n".join(lines)


async def stream_assistant_chat(
    db: AsyncSession | None,
    company_id: UUID,
    question: str,
    history: list[dict[str, str]] | None = None,
    *,
    snapshot: dict[str, Any] | None = None,
) -> AsyncIterator[str]:
    """Yield SSE frames: status -> token* -> done."""
    if snapshot is not None:
        snap = snapshot
    else:
        yield _sse("status", {"stage": "retrieving", "label": "กำลังดึงข้อมูลองค์กรแบบเรียลไทม์..."})
        assert db is not None
        snap = await collect_company_snapshot(db, company_id)

    api_key = (settings.GOOGLE_API_KEY or "").strip()
    if not api_key:
        yield _sse("status", {"stage": "answering", "label": "กำลังสรุปข้อมูลจากฐานข้อมูล..."})
        answer = _fallback_answer(question, snap)
        for chunk in [answer[i : i + 64] for i in range(0, len(answer), 64)]:
            yield _sse("token", {"text": chunk})
        yield _sse("done", {"provider": "db-snapshot", "snapshot": snap})
        return

    yield _sse("status", {"stage": "answering", "label": "กำลังวิเคราะห์ด้วย Gemini Flash..."})
    system_prompt = (
        "You are SentinelVision AI Copilot for an enterprise biometric attendance, "
        "access control, and security command center. Answer concisely in the user's language (Thai or English), "
        "grounded ONLY in the live company snapshot below. Never invent numbers.\n\n"
        f"LIVE_COMPANY_SNAPSHOT:\n{json.dumps(snap, ensure_ascii=False)}"
    )

    contents: list[dict[str, Any]] = []
    for turn in (history or [])[-6:]:
        role = "model" if turn.get("role") == "assistant" else "user"
        text = (turn.get("content") or "").strip()
        if text:
            contents.append({"role": role, "parts": [{"text": text}]})
    contents.append({"role": "user", "parts": [{"text": question}]})

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.GEMINI_MODEL}:streamGenerateContent?alt=sse&key={api_key}"
    )
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 768},
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("POST", url, json=payload) as resp:
                if resp.status_code != 200:
                    fallback = _fallback_answer(question, snap)
                    yield _sse("token", {"text": fallback})
                    yield _sse("done", {"provider": "db-fallback", "status": resp.status_code})
                    return
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    raw = line[6:].strip()
                    if not raw or raw == "[DONE]":
                        continue
                    try:
                        data = json.loads(raw)
                        parts = (
                            data.get("candidates", [{}])[0]
                            .get("content", {})
                            .get("parts", [])
                        )
                        for p in parts:
                            txt = p.get("text")
                            if txt:
                                yield _sse("token", {"text": txt})
                    except Exception:
                        continue
        yield _sse("done", {"provider": settings.GEMINI_MODEL})
    except Exception:
        fallback = _fallback_answer(question, snap)
        yield _sse("token", {"text": fallback})
        yield _sse("done", {"provider": "db-fallback"})
