"""Fleet Health Aggregation Service for Edge Kiosks, CCTV Cameras, and AI Workers."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.camera import Camera
from ..models.hr_schedule import KioskDevice
from ..models.notification_platform import InAppNotification
from ..models.sentinel import SentinelAccessZone


async def get_fleet_health_overview(db: AsyncSession, company_id: UUID) -> dict[str, Any]:
    now = datetime.now(timezone.utc)

    # 1. Kiosk Fleet
    kiosk_stmt = select(KioskDevice).where(
        KioskDevice.companyId == company_id,
        KioskDevice.revokedAt.is_(None),
    ).order_by(KioskDevice.name.asc())
    kiosks = (await db.execute(kiosk_stmt)).scalars().all()

    kiosk_items = []
    kiosks_online = 0
    kiosks_stale = 0
    kiosks_offline = 0
    kiosk_modes: dict[str, int] = {}
    kiosk_versions: dict[str, int] = {}

    for k in kiosks:
        hb = k.heartbeatAt
        if hb is not None and hb.tzinfo is None:
            hb = hb.replace(tzinfo=timezone.utc)

        if hb is None:
            k_status = "OFFLINE"
            kiosks_offline += 1
            ago_sec = None
        else:
            diff = (now - hb).total_seconds()
            ago_sec = max(0, int(diff))
            if diff <= 120:
                k_status = "ONLINE"
                kiosks_online += 1
            elif diff <= 600:
                k_status = "STALE"
                kiosks_stale += 1
            else:
                k_status = "OFFLINE"
                kiosks_offline += 1

        mode = k.stationMode or "UNCONFIGURED"
        kiosk_modes[mode] = kiosk_modes.get(mode, 0) + 1

        ver = k.appVersion or "Unknown"
        kiosk_versions[ver] = kiosk_versions.get(ver, 0) + 1

        kiosk_items.append(
            {
                "deviceId": str(k.deviceId),
                "name": k.name,
                "locationLabel": k.locationLabel,
                "stationMode": k.stationMode,
                "appVersion": k.appVersion,
                "fingerprint": k.fingerprint,
                "healthStatus": k_status,
                "lastHeartbeatAt": hb.isoformat() if hb else None,
                "lastSeenAgoSeconds": ago_sec,
                "isPaired": bool(k.tokenHash and not k.revokedAt),
            }
        )

    # 2. Camera Fleet
    cam_stmt = select(Camera).where(
        Camera.companyId == company_id,
        Camera.deletedAt.is_(None),
    ).order_by(Camera.name.asc())
    cams = (await db.execute(cam_stmt)).scalars().all()

    cams_connected = 0
    cams_offline = 0
    cam_items = []
    for c in cams:
        # Check active state and ping
        is_conn = c.isActive and c.status in ("online", "active", "connected")
        if is_conn:
            cams_connected += 1
        else:
            cams_offline += 1

        cam_items.append(
            {
                "cameraId": str(c.cameraId),
                "name": c.name,
                "protocol": c.protocol,
                "recordMode": c.recordMode,
                "status": c.status,
                "isActive": c.isActive,
                "latencyMs": c.lastPingLatencyMs,
                "lastPingAt": c.lastPingAt.isoformat() if c.lastPingAt else None,
            }
        )

    # 3. Access Zones
    zones_stmt = select(SentinelAccessZone).where(
        SentinelAccessZone.companyId == company_id,
        SentinelAccessZone.deletedAt.is_(None),
    )
    zones = (await db.execute(zones_stmt)).scalars().all()
    active_zones = sum(1 for z in zones if z.isActive)

    # 4. In-App Alerts (last 24 hours)
    day_ago = now - timedelta(hours=24)
    unread_alerts = (
        await db.scalar(
            select(func.count(InAppNotification.notificationId)).where(
                InAppNotification.companyId == company_id,
                InAppNotification.readAt.is_(None),
                InAppNotification.createdAt >= day_ago,
            )
        )
        or 0
    )

    # 5. GPU & AI Queue Inference Stats
    try:
        from ..controllers.face_ws_controller import _face_core_queue_stats

        ai_queue = await _face_core_queue_stats(company_id)
    except Exception:
        ai_queue = {"pending": 0, "active": 0}

    # Health Score calculation
    total_endpoints = len(kiosks) + len(cams)
    healthy_endpoints = kiosks_online + cams_connected
    if total_endpoints > 0:
        health_score = round((healthy_endpoints / total_endpoints) * 100, 1)
    else:
        health_score = 100.0

    return {
        "generatedAt": now.isoformat(),
        "summary": {
            "healthScore": health_score,
            "kiosksTotal": len(kiosks),
            "kiosksOnline": kiosks_online,
            "kiosksStale": kiosks_stale,
            "kiosksOffline": kiosks_offline,
            "camerasTotal": len(cams),
            "camerasConnected": cams_connected,
            "camerasOffline": cams_offline,
            "zonesTotal": len(zones),
            "zonesActive": active_zones,
            "unreadAlerts": unread_alerts,
            "aiQueuePending": ai_queue.get("pending", 0),
            "aiQueueActive": ai_queue.get("active", 0),
        },
        "kiosks": {
            "items": kiosk_items,
            "byMode": kiosk_modes,
            "byVersion": kiosk_versions,
        },
        "cameras": {
            "items": cam_items,
        },
    }
