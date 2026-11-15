"""Multi-Session Breakout Rooms & Capacity Enforcement for Smart Events."""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.sentinel import SentinelEvent
from .redis_client import get_redis
from .sentinel_incident_service import record_incident


def _room_key(event_id: UUID, room_code: str) -> str:
    clean_room = room_code.strip().upper().replace(" ", "_")[:40]
    return f"sv:evroom:{event_id}:{clean_room}"


async def get_breakout_room_occupancy(event_id: UUID, room_code: str) -> int:
    redis = get_redis()
    if redis is None:
        return 0
    try:
        raw = await redis.get(_room_key(event_id, room_code))
        return max(0, int(raw)) if raw is not None else 0
    except Exception:
        return 0


async def check_in_breakout_room(
    db: AsyncSession,
    *,
    company_id: UUID,
    event_id: UUID,
    room_code: str,
    capacity: int,
    subject_name: str = "Attendee",
    identity_id: Optional[UUID] = None,
) -> dict[str, Any]:
    """Enforce breakout room capacity atomically via Redis and log event check-in."""
    ev = await db.get(SentinelEvent, event_id)
    if not ev or ev.companyId != company_id or ev.deletedAt is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    clean_room = room_code.strip()
    if not clean_room:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="roomCode is required")
    max_cap = max(1, int(capacity))

    redis = get_redis()
    occupancy = 0
    if redis is not None:
        key = _room_key(event_id, clean_room)
        new_count = int(await redis.incr(key))
        await redis.expire(key, 86400)
        if new_count > max_cap:
            await redis.decr(key)
            await record_incident(
                db,
                company_id=company_id,
                event_type="EVENT_ROOM_FULL",
                severity="WARNING",
                identity_id=identity_id,
                subject_name=subject_name,
                identity_type="EVENT",
                action_taken=f"Breakout room '{clean_room}' at capacity ({max_cap}/{max_cap})",
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "EVENT_ROOM_FULL",
                    "message": f"Breakout room '{clean_room}' has reached capacity ({max_cap})",
                    "roomCode": clean_room,
                    "occupancy": max_cap,
                    "capacity": max_cap,
                },
            )
        occupancy = new_count

    await record_incident(
        db,
        company_id=company_id,
        event_type="EVENT_SESSION_CHECKIN",
        severity="INFO",
        identity_id=identity_id,
        subject_name=subject_name,
        identity_type="EVENT",
        action_taken=f"Checked into breakout room '{clean_room}' ({occupancy}/{max_cap})",
    )
    return {
        "checkedIn": True,
        "eventId": str(event_id),
        "eventName": ev.name,
        "roomCode": clean_room,
        "occupancy": occupancy,
        "capacity": max_cap,
    }
