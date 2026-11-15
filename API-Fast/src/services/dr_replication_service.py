"""Multi-Region DR Active-Active topology, signed replication & cache invalidation."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import json
import logging
from typing import Any, Optional
from uuid import UUID, uuid4

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.settings import settings
from .cache_service import cache_delete, kiosk_scan_debounce_check

logger = logging.getLogger(__name__)


def _dr_secret() -> bytes:
    secret = (settings.DR_REPLICATION_SECRET or settings.SECRET_KEY or "").strip()
    return secret.encode("utf-8")


def parse_peer_region_urls() -> list[str]:
    raw = (settings.PEER_REGION_URLS or "").strip()
    if not raw:
        return []
    return [u.strip().rstrip("/") for u in raw.split(",") if u.strip()]


def sign_replication_payload(raw_body: bytes) -> str:
    return hmac.new(_dr_secret(), raw_body, hashlib.sha256).hexdigest()


def verify_replication_signature(raw_body: bytes, signature: Optional[str]) -> bool:
    if not signature:
        return False
    expected = sign_replication_payload(raw_body)
    return hmac.compare_digest(expected, signature.strip())


def build_replication_envelope(
    *,
    entity_type: str,
    company_id: UUID,
    action: str,
    payload: Optional[dict[str, Any]] = None,
    event_id: Optional[str] = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "eventId": event_id or str(uuid4()),
        "originRegion": settings.REGION_ID,
        "entityType": entity_type.strip().upper(),
        "companyId": str(company_id),
        "action": action.strip().upper(),
        "timestampMs": int(now.timestamp() * 1000),
        "occurredAt": now.isoformat(),
        "payload": payload or {},
    }


async def fanout_replication_event(envelope: dict[str, Any]) -> dict[str, Any]:
    """Best-effort async fan-out of signed Active-Active state change to peer regions."""
    peers = parse_peer_region_urls()
    if not peers:
        return {"sent": 0, "peers": []}

    raw_body = json.dumps(envelope, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sig = sign_replication_payload(raw_body)
    headers = {
        "Content-Type": "application/json",
        "X-Sentinel-Region": settings.REGION_ID,
        "X-Sentinel-DR-Sig": sig,
    }

    results: list[dict[str, Any]] = []
    sent = 0
    async with httpx.AsyncClient(timeout=3.0) as client:
        for base_url in peers:
            target = f"{base_url}/sentinel/dr/replicate"
            try:
                resp = await client.post(target, content=raw_body, headers=headers)
                ok = 200 <= resp.status_code < 300
                if ok:
                    sent += 1
                results.append({"peer": base_url, "ok": ok, "statusCode": resp.status_code})
            except Exception as exc:
                logger.warning("DR replication fan-out failed for %s: %s", base_url, exc)
                results.append({"peer": base_url, "ok": False, "error": str(exc)})
    return {"sent": sent, "peers": results}


async def apply_incoming_replication_event(envelope: dict[str, Any]) -> dict[str, Any]:
    """Idempotently process an incoming peer-region replication event and refresh local caches."""
    event_id = str(envelope.get("eventId") or "").strip()
    company_id = str(envelope.get("companyId") or "").strip()
    entity_type = str(envelope.get("entityType") or "").strip().upper()
    origin_region = str(envelope.get("originRegion") or "").strip()

    if not event_id or not company_id or not entity_type:
        return {"applied": False, "reason": "INVALID_ENVELOPE"}

    if origin_region == settings.REGION_ID:
        return {"applied": False, "duplicate": True, "reason": "SELF_ORIGIN"}

    is_new = await kiosk_scan_debounce_check("dr", event_id, ttl_seconds=86400)
    if not is_new:
        return {"applied": False, "duplicate": True, "eventId": event_id}

    invalidated: list[str] = []
    if entity_type in {"MODULE_CONFIG", "COMPANY", "ALL"}:
        key = f"sv:modcfg:{company_id}"
        await cache_delete(key)
        invalidated.append(key)
    if entity_type in {"ACCESS_ZONE", "ZONE", "ALL"}:
        key = f"sv:zones:{company_id}"
        await cache_delete(key)
        invalidated.append(key)

    return {
        "applied": True,
        "duplicate": False,
        "eventId": event_id,
        "originRegion": origin_region,
        "localRegion": settings.REGION_ID,
        "invalidatedCaches": invalidated,
    }


async def get_region_topology(db: AsyncSession) -> dict[str, Any]:
    """Inspect local PostgreSQL replication role/lag and peer Active-Active region config."""
    in_recovery = False
    wal_lsn: Optional[str] = None
    replica_count = 0
    db_mode = "PRIMARY_RW"

    try:
        rec_res = await db.execute(text("SELECT pg_is_in_recovery()"))
        val = rec_res.scalar()
        in_recovery = bool(val)
        db_mode = "REPLICA_RO" if in_recovery else "PRIMARY_RW"
    except Exception:
        db_mode = "UNKNOWN"

    if not in_recovery and db_mode == "PRIMARY_RW":
        try:
            lsn_res = await db.execute(text("SELECT pg_current_wal_lsn()::text"))
            wal_lsn = str(lsn_res.scalar() or "") or None
        except Exception:
            wal_lsn = None
        try:
            rep_res = await db.execute(text("SELECT count(*) FROM pg_stat_replication"))
            replica_count = int(rep_res.scalar() or 0)
        except Exception:
            replica_count = 0

    return {
        "regionId": settings.REGION_ID,
        "dbMode": db_mode,
        "inRecovery": in_recovery,
        "walLsn": wal_lsn,
        "connectedReplicas": replica_count,
        "maxLagSecondsSla": int(settings.DR_MAX_LAG_SECONDS),
        "peerRegions": parse_peer_region_urls(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
