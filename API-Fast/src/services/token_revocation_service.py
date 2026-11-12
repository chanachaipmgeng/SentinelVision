"""JWT revocation: ``revoked_token`` deny-list + small in-process cache.

Tokens are revoked by ``jti`` (single token) or by ``fam`` (whole session family: the access +
refresh pair and every pair produced by rotating that refresh token). Lookups are cached
positively until the token expires and negatively for ``AUTH_REVOCATION_CACHE_SECONDS`` so the
hot path (every authenticated request) rarely hits the database. With several API replicas a
revocation becomes visible everywhere within that negative-cache window.
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.settings import settings
from ..models.revoked_token import SCOPE_FAMILY, SCOPE_TOKEN, RevokedToken
from ..security.jwt import token_exp_datetime

logger = logging.getLogger("dpu.revocation")

REASON_LOGOUT = "logout"
REASON_ROTATED = "rotated"
REASON_REUSE = "reuse_detected"
REASON_ADMIN = "admin_revoke"
REASON_DEVICE_REVOKED = "device_revoked"
REASON_REPAIR = "device_repair"

_NEGATIVE_CACHE_MAX = 20_000

_revoked_jti: dict[str, float] = {}
_revoked_family: dict[str, float] = {}
_clean_checked_at: dict[str, float] = {}


def family_key(family_id: str) -> str:
    return f"fam:{family_id}"


def reset_cache() -> None:
    _revoked_jti.clear()
    _revoked_family.clear()
    _clean_checked_at.clear()


def _remember_revoked(jti: Optional[str], family: Optional[str], scope: str, exp: datetime) -> None:
    exp_ts = exp.timestamp()
    if scope == SCOPE_FAMILY and family:
        _revoked_family[family] = exp_ts
    elif jti:
        _revoked_jti[jti] = exp_ts
    if jti:
        _clean_checked_at.pop(jti, None)


def _prune_caches(now: float) -> None:
    for store in (_revoked_jti, _revoked_family):
        for key in [k for k, exp in store.items() if exp <= now]:
            store.pop(key, None)
    if len(_clean_checked_at) > _NEGATIVE_CACHE_MAX:
        ttl = max(1, int(settings.AUTH_REVOCATION_CACHE_SECONDS))
        for key in [k for k, at in _clean_checked_at.items() if now - at >= ttl]:
            _clean_checked_at.pop(key, None)
        if len(_clean_checked_at) > _NEGATIVE_CACHE_MAX:
            _clean_checked_at.clear()


async def _upsert(db: AsyncSession, *, jti: str, family: Optional[str], scope: str, exp: datetime, reason: str) -> None:
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    values = {"jti": jti, "familyId": family, "scope": scope, "exp": exp, "reason": reason[:40]}
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        stmt = pg_insert(RevokedToken).values(**values).on_conflict_do_nothing(index_elements=["jti"])
        await db.execute(stmt)
    else:
        existing = await db.get(RevokedToken, jti)
        if existing is None:
            db.add(RevokedToken(**values))
    _remember_revoked(jti if scope == SCOPE_TOKEN else None, family, scope, exp)


async def revoke_jti(
    db: AsyncSession,
    jti: str,
    exp: datetime,
    *,
    reason: str,
    family: Optional[str] = None,
) -> None:
    """Deny a single token until ``exp``. Caller commits."""
    if not jti:
        return
    await _upsert(db, jti=jti, family=family, scope=SCOPE_TOKEN, exp=exp, reason=reason)


async def revoke_family(db: AsyncSession, family: str, exp: datetime, *, reason: str) -> None:
    """Deny every token sharing ``fam`` (access + refresh + rotated descendants). Caller commits."""
    if not family:
        return
    await _upsert(db, jti=family_key(family), family=family, scope=SCOPE_FAMILY, exp=exp, reason=reason)


async def revoke_token_payload(db: AsyncSession, payload: dict[str, Any], *, reason: str) -> None:
    await revoke_jti(db, payload.get("jti") or "", token_exp_datetime(payload), reason=reason, family=payload.get("fam"))


def family_expiry_for(payload: dict[str, Any], *, refresh_ttl: timedelta) -> datetime:
    """Latest moment any token in this family can still be alive: refresh token lifetime from now,
    or the refresh token's own ``exp`` when we hold it."""
    exp = token_exp_datetime(payload)
    floor = datetime.now(timezone.utc) + refresh_ttl
    return max(exp, floor)


async def lookup_revocation(
    db: AsyncSession, jti: Optional[str], family: Optional[str]
) -> Optional[dict[str, Any]]:
    """Return the matching deny-list row (as a dict) or None. Always hits the database."""
    conditions = []
    if jti:
        conditions.append(RevokedToken.jti == jti)
    if family:
        conditions.append(and_(RevokedToken.scope == SCOPE_FAMILY, RevokedToken.familyId == family))
    if not conditions:
        return None
    rows = (await db.execute(select(RevokedToken).where(or_(*conditions)))).scalars().all()
    now = datetime.now(timezone.utc)
    hit = None
    for row in rows:
        exp = row.exp if row.exp.tzinfo else row.exp.replace(tzinfo=timezone.utc)
        if exp <= now:
            continue
        _remember_revoked(row.jti, row.familyId, row.scope, exp)
        # a family revocation outranks a single-token one for reporting purposes
        if hit is None or row.scope == SCOPE_FAMILY:
            hit = {"jti": row.jti, "scope": row.scope, "reason": row.reason, "familyId": row.familyId}
    return hit


async def is_token_revoked(payload: dict[str, Any], *, db_factory=None) -> bool:
    """Hot-path check used by the auth middleware; consults the in-memory cache first."""
    jti = payload.get("jti")
    family = payload.get("fam")
    if not jti and not family:
        # Legacy token issued before jti/fam existed: cannot be revoked, expires naturally.
        return False
    now = time.time()
    if jti and _revoked_jti.get(jti, 0) > now:
        return True
    if family and _revoked_family.get(family, 0) > now:
        return True
    ttl = max(1, int(settings.AUTH_REVOCATION_CACHE_SECONDS))
    checked = _clean_checked_at.get(jti or family_key(family or ""))
    if checked is not None and now - checked < ttl:
        return False
    if db_factory is None:
        from ..config.database import async_session as db_factory  # noqa: PLC0415
    try:
        async with db_factory() as db:
            hit = await lookup_revocation(db, jti, family)
    except Exception:
        logger.exception("revocation lookup failed; failing open for this request")
        return False
    _prune_caches(now)
    if hit is not None:
        return True
    _clean_checked_at[jti or family_key(family or "")] = now
    return False


async def purge_expired(db: AsyncSession) -> int:
    now = datetime.now(timezone.utc)
    result = await db.execute(delete(RevokedToken).where(RevokedToken.exp <= now))
    await db.commit()
    _prune_caches(time.time())
    return int(getattr(result, "rowcount", 0) or 0)


async def revocation_purge_loop() -> None:
    from ..config.database import async_session

    while True:
        try:
            async with async_session() as db:
                removed = await purge_expired(db)
            if removed:
                logger.info("revocation purge removed=%s", removed)
        except Exception:
            logger.exception("revocation purge failed")
        await asyncio.sleep(max(60, int(settings.AUTH_REVOCATION_PURGE_SECONDS)))
