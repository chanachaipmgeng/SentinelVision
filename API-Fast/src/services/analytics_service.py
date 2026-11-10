"""Phase 6C — Postgres-first heatmap / occupancy / dwell / camera-health analytics.

Data sources (documented for handoff):
- Heatmap hour×weekday: ``sentinel_incident_log.occurred_at`` (face/CCTV events)
  plus optional ``employee_timestamp.timestamp`` (check-in density).
- Occupancy series: distinct subjects per hour from incidents (memberId / identityId).
- Dwell: session clustering (≤5 min gap) of consecutive incidents per camera/zone.
- Camera health: ``camera`` registry (status, lastPing*, lastAnalyzedAt) + incident
  counts joined via ``camera_id`` / ``video_clip``.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.camera import Camera
from ..models.employee_timestamp import EmployeeTimestamp
from ..models.sentinel import SentinelIncidentLog
from ..models.video_clip import VideoClip

BANGKOK_TZ = "Asia/Bangkok"
SESSION_GAP = timedelta(minutes=5)
STALE_PING = timedelta(minutes=15)


def _bangkok_tz():
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(BANGKOK_TZ)
    except Exception:
        return timezone(timedelta(hours=7))


def _parse_dt(raw: Optional[str], *, default: datetime) -> datetime:
    if not raw:
        return default
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return default
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _default_range(days: int = 7) -> tuple[datetime, datetime]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    return start, end


def resolve_range(
    start: Optional[str],
    end: Optional[str],
    *,
    default_days: int = 7,
) -> tuple[datetime, datetime]:
    default_start, default_end = _default_range(default_days)
    start_dt = _parse_dt(start, default=default_start)
    end_dt = _parse_dt(end, default=default_end)
    if end_dt < start_dt:
        start_dt, end_dt = end_dt, start_dt
    # Cap to 90 days to keep Postgres-first aggregation cheap.
    if (end_dt - start_dt) > timedelta(days=90):
        start_dt = end_dt - timedelta(days=90)
    return start_dt, end_dt


async def get_hour_day_heatmap(
    db: AsyncSession,
    company_id: UUID,
    *,
    start: datetime,
    end: datetime,
    source: str = "incidents",
) -> dict[str, Any]:
    """Aggregate events into weekday (0=Mon … 6=Sun) × hour (0–23) in Asia/Bangkok."""
    src = (source or "incidents").strip().lower()
    if src not in ("incidents", "attendance", "both"):
        src = "incidents"

    cells: dict[tuple[int, int], int] = {}

    async def _add_from_ts_expr(ts_col, where_clause) -> None:
        # ISODOW: Mon=1 … Sun=7 → weekday 0–6
        local_ts = func.timezone(BANGKOK_TZ, ts_col)
        weekday_expr = (func.extract("isodow", local_ts) - 1).label("weekday")
        hour_expr = func.extract("hour", local_ts).label("hour")
        stmt = (
            select(
                weekday_expr,
                hour_expr,
                func.count().label("cnt"),
            )
            .where(where_clause)
            .group_by(weekday_expr, hour_expr)
        )
        rows = (await db.execute(stmt)).all()
        for r in rows:
            key = (int(r.weekday), int(r.hour))
            cells[key] = cells.get(key, 0) + int(r.cnt or 0)

    if src in ("incidents", "both"):
        await _add_from_ts_expr(
            SentinelIncidentLog.occurredAt,
            and_(
                SentinelIncidentLog.companyId == company_id,
                SentinelIncidentLog.occurredAt >= start,
                SentinelIncidentLog.occurredAt <= end,
            ),
        )

    if src in ("attendance", "both"):
        await _add_from_ts_expr(
            EmployeeTimestamp.timestamp,
            and_(
                EmployeeTimestamp.companyId == company_id,
                EmployeeTimestamp.timestamp >= start,
                EmployeeTimestamp.timestamp <= end,
            ),
        )

    out_cells = [
        {"weekday": wd, "hour": hr, "count": cnt}
        for (wd, hr), cnt in sorted(cells.items(), key=lambda x: (x[0][0], x[0][1]))
    ]
    max_count = max((c["count"] for c in out_cells), default=0)
    return {
        "companyId": str(company_id),
        "timezone": BANGKOK_TZ,
        "source": src,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "grid": {"weekdays": 7, "hours": 24},
        "cells": out_cells,
        "maxCount": max_count,
        "totalEvents": sum(c["count"] for c in out_cells),
    }


async def get_occupancy_series(
    db: AsyncSession,
    company_id: UUID,
    *,
    start: datetime,
    end: datetime,
) -> dict[str, Any]:
    """Hourly occupancy = distinct subjects (member or identity) per Bangkok hour bucket."""
    # Use SQL text for distinct-count to avoid dialect quirks with coalesce UUID/text.
    stmt = text(
        """
        SELECT date_trunc(
                 'hour',
                 timezone(:tz, occurred_at)
               ) AS bucket,
               COUNT(DISTINCT COALESCE(
                 member_id::text,
                 identity_id::text,
                 NULLIF(subject_name, ''),
                 'unknown'
               )) AS subjects,
               COUNT(*) AS events
        FROM sentinel_incident_log
        WHERE "companyId" = :cid
          AND occurred_at >= :start
          AND occurred_at <= :end
        GROUP BY 1
        ORDER BY 1
        """
    )
    rows = (
        await db.execute(
            stmt,
            {
                "tz": BANGKOK_TZ,
                "cid": str(company_id),
                "start": start,
                "end": end,
            },
        )
    ).all()
    points = [
        {
            "bucket": r.bucket.isoformat() if hasattr(r.bucket, "isoformat") else str(r.bucket),
            "subjects": int(r.subjects or 0),
            "events": int(r.events or 0),
        }
        for r in rows
    ]
    peak = max((p["subjects"] for p in points), default=0)
    return {
        "companyId": str(company_id),
        "timezone": BANGKOK_TZ,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "source": "sentinel_incident_log",
        "points": points,
        "peakOccupancy": peak,
        "totalEvents": sum(p["events"] for p in points),
    }


async def get_dwell_series(
    db: AsyncSession,
    company_id: UUID,
    *,
    start: datetime,
    end: datetime,
) -> dict[str, Any]:
    """Estimate dwell per camera/zone from consecutive incident timestamps (5-min gap)."""
    stmt = (
        select(
            SentinelIncidentLog.cameraId,
            SentinelIncidentLog.zoneId,
            SentinelIncidentLog.zoneName,
            SentinelIncidentLog.memberId,
            SentinelIncidentLog.identityId,
            SentinelIncidentLog.occurredAt,
        )
        .where(
            and_(
                SentinelIncidentLog.companyId == company_id,
                SentinelIncidentLog.occurredAt >= start,
                SentinelIncidentLog.occurredAt <= end,
            )
        )
        .order_by(
            SentinelIncidentLog.cameraId.nulls_last(),
            SentinelIncidentLog.zoneId.nulls_last(),
            SentinelIncidentLog.memberId.nulls_last(),
            SentinelIncidentLog.identityId.nulls_last(),
            SentinelIncidentLog.occurredAt,
        )
    )
    rows = (await db.execute(stmt)).all()

    # Load camera names for labels
    cam_ids = {r.cameraId for r in rows if r.cameraId}
    cam_names: dict[UUID, str] = {}
    if cam_ids:
        cam_rows = (
            await db.execute(
                select(Camera.cameraId, Camera.name).where(
                    and_(Camera.companyId == company_id, Camera.cameraId.in_(cam_ids))
                )
            )
        ).all()
        cam_names = {r.cameraId: r.name for r in cam_rows}

    stats: dict[str, dict[str, Any]] = {}
    prev_key: Optional[tuple] = None
    session_start: Optional[datetime] = None
    prev_time: Optional[datetime] = None

    def _flush(key: tuple, start_t: datetime, end_t: datetime) -> None:
        dur = (end_t - start_t).total_seconds()
        if dur < 1:
            return
        sk = key[0]  # group key string
        if sk not in stats:
            stats[sk] = {
                "key": sk,
                "cameraId": key[1],
                "cameraName": key[2],
                "zoneId": key[3],
                "zoneName": key[4],
                "totalDwellSeconds": 0.0,
                "sessions": 0,
            }
        stats[sk]["totalDwellSeconds"] += dur
        stats[sk]["sessions"] += 1

    for r in rows:
        cam_id = str(r.cameraId) if r.cameraId else None
        zone_id = str(r.zoneId) if r.zoneId else None
        subject = str(r.memberId or r.identityId or "anon")
        group = cam_id or zone_id or "unknown"
        cam_name = cam_names.get(r.cameraId, "") if r.cameraId else ""
        zone_name = r.zoneName or ""
        key = (f"{group}|{subject}", cam_id, cam_name, zone_id, zone_name)
        ts = r.occurredAt
        if ts is None:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        if prev_key is None or key[0] != prev_key[0]:
            if prev_key is not None and session_start is not None and prev_time is not None:
                _flush(prev_key, session_start, prev_time)
            session_start = ts
            prev_time = ts
            prev_key = key
            continue

        gap = ts - prev_time if prev_time else timedelta(0)
        if gap > SESSION_GAP:
            if session_start is not None and prev_time is not None:
                _flush(key, session_start, prev_time)
            session_start = ts
        prev_time = ts

    if prev_key is not None and session_start is not None and prev_time is not None:
        _flush(prev_key, session_start, prev_time)

    # Roll up to camera/zone (drop subject dimension)
    rolled: dict[str, dict[str, Any]] = {}
    for s in stats.values():
        rk = s["cameraId"] or s["zoneId"] or "unknown"
        if rk not in rolled:
            rolled[rk] = {
                "cameraId": s["cameraId"],
                "cameraName": s["cameraName"] or None,
                "zoneId": s["zoneId"],
                "zoneName": s["zoneName"] or None,
                "totalDwellSeconds": 0.0,
                "sessions": 0,
            }
        rolled[rk]["totalDwellSeconds"] += s["totalDwellSeconds"]
        rolled[rk]["sessions"] += s["sessions"]

    cameras = []
    for item in sorted(rolled.values(), key=lambda x: x["totalDwellSeconds"], reverse=True):
        sessions = int(item["sessions"])
        total = float(item["totalDwellSeconds"])
        cameras.append(
            {
                "cameraId": item["cameraId"],
                "cameraName": item["cameraName"],
                "zoneId": item["zoneId"],
                "zoneName": item["zoneName"],
                "avgDwellSeconds": round(total / sessions, 1) if sessions else 0.0,
                "totalDwellSeconds": round(total, 1),
                "sessions": sessions,
            }
        )

    return {
        "companyId": str(company_id),
        "timezone": BANGKOK_TZ,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "source": "sentinel_incident_log",
        "sessionGapMinutes": int(SESSION_GAP.total_seconds() // 60),
        "cameras": cameras,
    }


async def get_camera_health(
    db: AsyncSession,
    company_id: UUID,
    *,
    start: datetime,
    end: datetime,
) -> dict[str, Any]:
    """Per-camera health from MediaMTX-backed camera registry + recent incident volume."""
    cams = (
        await db.execute(
            select(Camera).where(
                and_(
                    Camera.companyId == company_id,
                    Camera.deletedAt.is_(None),
                )
            )
        )
    ).scalars().all()

    # Incident counts by camera in range
    inc_counts: dict[UUID, int] = {}
    inc_rows = (
        await db.execute(
            select(
                SentinelIncidentLog.cameraId,
                func.count().label("cnt"),
            )
            .where(
                and_(
                    SentinelIncidentLog.companyId == company_id,
                    SentinelIncidentLog.cameraId.is_not(None),
                    SentinelIncidentLog.occurredAt >= start,
                    SentinelIncidentLog.occurredAt <= end,
                )
            )
            .group_by(SentinelIncidentLog.cameraId)
        )
    ).all()
    for r in inc_rows:
        if r.cameraId:
            inc_counts[r.cameraId] = int(r.cnt or 0)

    # Fallback: clip-linked incidents for cameras without cameraId on the log
    clip_rows = (
        await db.execute(
            select(
                VideoClip.cameraId,
                func.count(func.distinct(VideoClip.incidentId)).label("cnt"),
            )
            .where(
                and_(
                    VideoClip.companyId == company_id,
                    VideoClip.incidentId.is_not(None),
                    VideoClip.startedAt >= start,
                    VideoClip.startedAt <= end,
                )
            )
            .group_by(VideoClip.cameraId)
        )
    ).all()
    clip_counts = {r.cameraId: int(r.cnt or 0) for r in clip_rows if r.cameraId}

    now = datetime.now(timezone.utc)
    items = []
    online = offline = unknown = stale = 0
    for cam in cams:
        ping_at = cam.lastPingAt
        if ping_at is not None and ping_at.tzinfo is None:
            ping_at = ping_at.replace(tzinfo=timezone.utc)
        is_stale = bool(ping_at and (now - ping_at) > STALE_PING)
        status = (cam.status or "unknown").lower()
        if not cam.isActive:
            health = "inactive"
        elif status == "online" and not is_stale:
            health = "healthy"
            online += 1
        elif status == "offline" or is_stale:
            health = "degraded" if status == "online" and is_stale else "offline"
            if health == "offline":
                offline += 1
            else:
                stale += 1
        else:
            health = "unknown"
            unknown += 1

        events = inc_counts.get(cam.cameraId, 0) or clip_counts.get(cam.cameraId, 0)
        items.append(
            {
                "cameraId": str(cam.cameraId),
                "name": cam.name,
                "status": cam.status,
                "health": health,
                "isActive": bool(cam.isActive),
                "analysisEnabled": bool(getattr(cam, "analysisEnabled", False)),
                "lastPingAt": ping_at.isoformat() if ping_at else None,
                "lastPingLatencyMs": cam.lastPingLatencyMs,
                "lastAnalyzedAt": cam.lastAnalyzedAt.isoformat()
                if cam.lastAnalyzedAt
                else None,
                "recordMode": cam.recordMode,
                "eventsInRange": events,
                "stalePing": is_stale,
            }
        )

    items.sort(key=lambda x: (0 if x["health"] == "healthy" else 1, x["name"] or ""))
    return {
        "companyId": str(company_id),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "summary": {
            "total": len(items),
            "online": online,
            "offline": offline,
            "unknown": unknown,
            "stale": stale,
            "active": sum(1 for i in items if i["isActive"]),
            "analysisEnabled": sum(1 for i in items if i["analysisEnabled"]),
        },
        "cameras": items,
    }


async def get_analytics_summary(
    db: AsyncSession,
    company_id: UUID,
    *,
    start: datetime,
    end: datetime,
    source: str = "both",
) -> dict[str, Any]:
    """Bundle KPIs used by the face-monitor page and PDF export."""
    heatmap = await get_hour_day_heatmap(
        db, company_id, start=start, end=end, source=source
    )
    occupancy = await get_occupancy_series(db, company_id, start=start, end=end)
    dwell = await get_dwell_series(db, company_id, start=start, end=end)
    health = await get_camera_health(db, company_id, start=start, end=end)

    # Top 3 busy hours from heatmap
    top_cells = sorted(heatmap["cells"], key=lambda c: c["count"], reverse=True)[:3]
    weekday_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    busy_slots = [
        {
            "label": f"{weekday_labels[c['weekday']]} {c['hour']:02d}:00",
            "count": c["count"],
        }
        for c in top_cells
    ]

    return {
        "companyId": str(company_id),
        "timezone": BANGKOK_TZ,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "kpis": {
            "totalEvents": heatmap["totalEvents"],
            "peakOccupancy": occupancy["peakOccupancy"],
            "camerasTotal": health["summary"]["total"],
            "camerasOnline": health["summary"]["online"],
            "camerasOffline": health["summary"]["offline"],
            "avgDwellSeconds": (
                round(
                    sum(c["avgDwellSeconds"] for c in dwell["cameras"])
                    / len(dwell["cameras"]),
                    1,
                )
                if dwell["cameras"]
                else 0.0
            ),
            "busySlots": busy_slots,
        },
        "heatmap": heatmap,
        "occupancy": occupancy,
        "dwell": dwell,
        "cameraHealth": health,
    }
