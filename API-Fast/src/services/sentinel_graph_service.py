"""Security Investigation Graph builder for SentinelVision (company-scoped)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.camera import Camera
from ..models.sentinel import (
    SentinelAccessZone,
    SentinelIdentity,
    SentinelIncidentLog,
)


async def build_sentinel_investigation_graph(
    db: AsyncSession,
    company_id: UUID,
    *,
    days: int = 7,
    limit_incidents: int = 40,
) -> dict[str, Any]:
    """Build an ECharts-compatible 2D relationship graph for Sentinel Center."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, min(days, 90)))
    max_inc = max(5, min(limit_incidents, 100))

    zones = (
        await db.execute(
            select(SentinelAccessZone)
            .where(
                SentinelAccessZone.companyId == company_id,
                SentinelAccessZone.deletedAt.is_(None),
            )
            .limit(80)
        )
    ).scalars().all()

    cameras = (
        await db.execute(
            select(Camera)
            .where(
                Camera.companyId == company_id,
                Camera.deletedAt.is_(None),
            )
            .limit(80)
        )
    ).scalars().all()

    identities = (
        await db.execute(
            select(SentinelIdentity)
            .where(
                SentinelIdentity.companyId == company_id,
                SentinelIdentity.deletedAt.is_(None),
            )
            .limit(120)
        )
    ).scalars().all()

    incidents = (
        await db.execute(
            select(SentinelIncidentLog)
            .where(
                SentinelIncidentLog.companyId == company_id,
                SentinelIncidentLog.occurredAt >= cutoff,
            )
            .order_by(SentinelIncidentLog.occurredAt.desc())
            .limit(max_inc)
        )
    ).scalars().all()

    nodes: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []
    seen_nodes: set[str] = set()
    seen_links: set[tuple[str, str, str]] = set()

    def add_node(
        node_id: str,
        name: str,
        category: int,
        symbol_size: int,
        meta: dict[str, Any],
    ) -> None:
        if node_id in seen_nodes:
            return
        seen_nodes.add(node_id)
        nodes.append(
            {
                "id": node_id,
                "name": name,
                "category": category,
                "symbolSize": symbol_size,
                "meta": meta,
            }
        )

    def add_link(source: str, target: str, relation: str) -> None:
        if source not in seen_nodes or target not in seen_nodes:
            return
        key = (source, target, relation)
        if key in seen_links:
            return
        seen_links.add(key)
        links.append({"source": source, "target": target, "relation": relation})

    # Categories: 0=Zone, 1=Camera, 2=Identity, 3=Incident
    for z in zones:
        zid = f"zone:{z.zoneId}"
        add_node(
            zid,
            z.name or z.code,
            0,
            34,
            {
                "kind": "zone",
                "zoneId": str(z.zoneId),
                "code": z.code,
                "stationMode": z.stationMode,
                "isActive": bool(z.isActive),
            },
        )

    for c in cameras:
        cid = f"cam:{c.cameraId}"
        add_node(
            cid,
            c.name,
            1,
            26,
            {
                "kind": "camera",
                "cameraId": str(c.cameraId),
                "status": c.status,
                "stationMode": c.stationMode,
            },
        )
        if c.zoneId:
            add_link(cid, f"zone:{c.zoneId}", "MONITORS_ZONE")

    for ident in identities:
        iid = f"ident:{ident.identityId}"
        is_alert = ident.identityType in ("BLACKLIST", "POI")
        add_node(
            iid,
            ident.fullName,
            2,
            30 if is_alert else 22,
            {
                "kind": "identity",
                "identityId": str(ident.identityId),
                "identityType": ident.identityType,
                "severity": ident.severity,
                "status": ident.status,
            },
        )
        for zid_raw in ident.allowedZoneIds or []:
            add_link(iid, f"zone:{zid_raw}", "ALLOWED_IN")

    for inc in incidents:
        inc_id = f"inc:{inc.incidentId}"
        label = f"{inc.eventType}"
        if inc.subjectName:
            label = f"{inc.eventType}: {inc.subjectName}"
        add_node(
            inc_id,
            label,
            3,
            28 if inc.severity in ("CRITICAL", "HIGH") else 20,
            {
                "kind": "incident",
                "incidentId": str(inc.incidentId),
                "eventType": inc.eventType,
                "severity": inc.severity,
                "status": inc.status,
                "subjectName": inc.subjectName,
                "snapshotUrl": inc.snapshotUrl,
                "occurredAt": inc.occurredAt.isoformat() if inc.occurredAt else None,
            },
        )
        if inc.identityId:
            add_link(f"ident:{inc.identityId}", inc_id, "TRIGGERED")
        if inc.zoneId:
            add_link(inc_id, f"zone:{inc.zoneId}", "AT_ZONE")
        if inc.cameraId:
            add_link(inc_id, f"cam:{inc.cameraId}", "CAPTURED_BY")

    return {
        "categories": [
            {"name": "Zone"},
            {"name": "Camera"},
            {"name": "Identity"},
            {"name": "Incident"},
        ],
        "nodes": nodes,
        "links": links,
        "stats": {
            "zones": len(zones),
            "cameras": len(cameras),
            "identities": len(identities),
            "incidents": len(incidents),
            "totalNodes": len(nodes),
            "totalLinks": len(links),
        },
    }
