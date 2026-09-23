"""Per-process check-in dedupe cache to skip repeated Postgres lookups.

Sticky WebSocket connections keep a kiosk on one API process, so an in-memory
TTL cache avoids re-querying EmployeeTimestamp on every duplicate check-in
during rush (loadtests show most check-ins are duplicates within 5 minutes).
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Tuple
from uuid import UUID


@dataclass(frozen=True)
class CachedCheckIn:
    timestamp_id: str
    timestamp: datetime
    timestamp_type: Any
    location_name: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    photo_timestamp: Optional[str]
    approval_status: Any
    note: Optional[str]
    stored_at_mono: float


_lock = threading.Lock()
_items: Dict[Tuple[str, str], CachedCheckIn] = {}
_MAX_ITEMS = 50_000


def _key(company_id: UUID, company_employee_id: UUID) -> Tuple[str, str]:
    return (str(company_id), str(company_employee_id))


def get_cached_check_in(
    company_id: UUID,
    company_employee_id: UUID,
    *,
    ttl_s: float,
) -> Optional[CachedCheckIn]:
    if ttl_s <= 0:
        return None
    key = _key(company_id, company_employee_id)
    now = time.monotonic()
    with _lock:
        item = _items.get(key)
        if item is None:
            return None
        if now - item.stored_at_mono > ttl_s:
            _items.pop(key, None)
            return None
        return item


def put_cached_check_in(
    company_id: UUID,
    company_employee_id: UUID,
    *,
    timestamp_id: str,
    timestamp: datetime,
    timestamp_type: Any,
    location_name: Optional[str],
    latitude: Optional[float],
    longitude: Optional[float],
    photo_timestamp: Optional[str],
    approval_status: Any,
    note: Optional[str],
) -> None:
    key = _key(company_id, company_employee_id)
    entry = CachedCheckIn(
        timestamp_id=str(timestamp_id),
        timestamp=timestamp,
        timestamp_type=timestamp_type,
        location_name=location_name,
        latitude=latitude,
        longitude=longitude,
        photo_timestamp=photo_timestamp,
        approval_status=approval_status,
        note=note,
        stored_at_mono=time.monotonic(),
    )
    with _lock:
        if len(_items) >= _MAX_ITEMS and key not in _items:
            # Drop arbitrary oldest-ish: clear half when full (rare).
            for drop_key in list(_items.keys())[: _MAX_ITEMS // 2]:
                _items.pop(drop_key, None)
        _items[key] = entry


def clear_cached_check_ins() -> None:
    with _lock:
        _items.clear()
