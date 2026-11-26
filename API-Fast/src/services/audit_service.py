"""Append-only tamper-evident audit log with SHA-256 hash chaining."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import logging
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Index, String, Text, select, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from ..config.database import Base, async_session

logger = logging.getLogger("dpu.audit")

GENESIS_HASH = "GENESIS"


def compute_audit_hash(
    prev_hash: str,
    *,
    company_id: Optional[str],
    action: str,
    actor_member_id: Optional[str],
    entity_type: Optional[str],
    entity_id: Optional[str],
    path: Optional[str],
    status_code: Optional[str],
    detail_payload: Optional[dict[str, Any]],
    entry_id: Optional[str] = None,
    occurred_at: Optional[str] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_id: Optional[str] = None,
    algo: str = "sha256-v1",
) -> str:
    """Compute a deterministic SHA-256 link hash over the audit event fields."""
    clean_detail = {
        k: v for k, v in (detail_payload or {}).items() if k != "_integrity"
    }
    payload_obj: dict[str, Any] = {
        "prevHash": prev_hash,
        "companyId": company_id,
        "action": action,
        "actorMemberId": actor_member_id,
        "entityType": entity_type,
        "entityId": entity_id,
        "path": path,
        "statusCode": status_code,
        "detail": clean_detail,
    }
    if algo == "sha256-v2":
        payload_obj.update(
            {
                "id": entry_id,
                "occurredAt": occurred_at,
                "ip": ip,
                "userAgent": user_agent,
                "requestId": request_id,
            }
        )
    canonical = json.dumps(
        payload_obj,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _extract_integrity(detail: Any) -> tuple[Optional[str], Optional[str]]:
    if not isinstance(detail, dict):
        return None, None
    integ = detail.get("_integrity")
    if not isinstance(integ, dict):
        return None, None
    return integ.get("prevHash"), integ.get("hash")


def _extract_integrity_algo(detail: Any) -> str:
    if isinstance(detail, dict):
        integ = detail.get("_integrity")
        if isinstance(integ, dict) and integ.get("algo"):
            return str(integ["algo"])
    return "sha256-v1"


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    occurredAt = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    actorMemberId = Column(PGUUID(as_uuid=True), nullable=True)
    actorRole = Column(String, nullable=True)
    companyId = Column(PGUUID(as_uuid=True), nullable=True)
    action = Column(String, nullable=False)
    entityType = Column(String, nullable=True)
    entityId = Column(String, nullable=True)
    path = Column(String, nullable=True)
    statusCode = Column(String, nullable=True)
    ip = Column(String, nullable=True)
    userAgent = Column(Text, nullable=True)
    requestId = Column(String, nullable=True)
    detail = Column(JSONB, nullable=True)

    __table_args__ = (Index("audit_log_company_occurred_idx", "companyId", occurredAt.desc()),)


async def write_audit(
    *,
    actor=None,
    action: str,
    path: str = "",
    status_code: int = 0,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_id: Optional[str] = None,
    company_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    detail: Optional[dict[str, Any]] = None,
) -> None:
    role = None
    actor_id = None
    if actor is not None:
        actor_id = actor.memberId
        role_obj = getattr(actor, "role", None)
        role = getattr(role_obj, "name", str(role_obj) if role_obj is not None else None)
    cid_uuid = UUID(str(company_id)) if company_id else None
    cid_str = str(cid_uuid) if cid_uuid else None
    clean_path = path[:500] if path else None
    clean_status = str(status_code) if status_code else None
    detail_copy: dict[str, Any] = dict(detail) if isinstance(detail, dict) else {}

    row_id = uuid4()
    occurred_at = datetime.now(timezone.utc)
    clean_ua = (user_agent or "")[:500] or None

    async with async_session() as db:
        if db.bind is not None and getattr(db.bind.dialect, "name", "") == "postgresql":
            await db.execute(
                text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
                {"k": f"audit:{cid_str or 'global'}"},
            )
        prev_q: Any = (
            select(AuditLog.detail)
            .where(AuditLog.companyId == cid_uuid if cid_uuid else AuditLog.companyId.is_(None))
            .order_by(AuditLog.occurredAt.desc(), AuditLog.id.desc())
            .limit(1)
        )
        prev_detail = (await db.execute(prev_q)).scalar_one_or_none()
        _, prev_hash = _extract_integrity(prev_detail)
        prev_link = prev_hash or GENESIS_HASH
        entry_hash = compute_audit_hash(
            prev_link,
            company_id=cid_str,
            action=action,
            actor_member_id=str(actor_id) if actor_id else None,
            entity_type=entity_type,
            entity_id=entity_id,
            path=clean_path,
            status_code=clean_status,
            detail_payload=detail_copy,
            entry_id=str(row_id),
            occurred_at=occurred_at.isoformat(),
            ip=ip,
            user_agent=clean_ua,
            request_id=request_id,
            algo="sha256-v2",
        )
        detail_copy["_integrity"] = {
            "algo": "sha256-v2",
            "prevHash": prev_link,
            "hash": entry_hash,
        }
        row = AuditLog(
            id=row_id,
            occurredAt=occurred_at,
            actorMemberId=actor_id,
            actorRole=role,
            companyId=cid_uuid,
            action=action,
            entityType=entity_type,
            entityId=entity_id,
            path=clean_path,
            statusCode=clean_status,
            ip=ip,
            userAgent=clean_ua,
            requestId=request_id,
            detail=detail_copy,
        )
        db.add(row)
        await db.commit()


async def verify_audit_chain(
    db: AsyncSession,
    company_id: UUID,
    *,
    limit: int = 500,
) -> dict[str, Any]:
    """Verify SHA-256 hash-chain integrity over the newest ``limit`` company audit rows."""
    bounded = max(1, min(int(limit), 1000))
    rows = (
        await db.execute(
            select(AuditLog)
            .where(AuditLog.companyId == company_id)
            .order_by(AuditLog.occurredAt.desc(), AuditLog.id.desc())
            .limit(bounded)
        )
    ).scalars().all()
    ordered = list(reversed(rows))

    verified = 0
    legacy_unchained = 0
    broken_ids: list[str] = []
    expected_prev: Optional[str] = None

    for row in ordered:
        prev_hash, stored_hash = _extract_integrity(row.detail)
        if not stored_hash:
            legacy_unchained += 1
            expected_prev = None
            continue
        algo = _extract_integrity_algo(row.detail)
        raw_occ = getattr(row, "occurredAt", None)
        if raw_occ is None:
            occurred_iso = None
        elif getattr(raw_occ, "tzinfo", None) is not None:
            occurred_iso = raw_occ.astimezone(timezone.utc).isoformat()
        else:
            occurred_iso = raw_occ.replace(tzinfo=timezone.utc).isoformat()
        raw_ip = getattr(row, "ip", None)
        raw_ua = getattr(row, "userAgent", None)
        raw_rid = getattr(row, "requestId", None)
        recomputed = compute_audit_hash(
            prev_hash or GENESIS_HASH,
            company_id=str(row.companyId) if row.companyId is not None else None,
            action=str(row.action),
            actor_member_id=str(row.actorMemberId) if row.actorMemberId is not None else None,
            entity_type=str(row.entityType) if row.entityType is not None else None,
            entity_id=str(row.entityId) if row.entityId is not None else None,
            path=str(row.path) if row.path is not None else None,
            status_code=str(row.statusCode) if row.statusCode is not None else None,
            detail_payload=row.detail if isinstance(row.detail, dict) else None,
            entry_id=str(getattr(row, "id", "")),
            occurred_at=occurred_iso,
            ip=str(raw_ip) if raw_ip is not None else None,
            user_agent=str(raw_ua) if raw_ua is not None else None,
            request_id=str(raw_rid) if raw_rid is not None else None,
            algo=algo,
        )
        link_ok = expected_prev is None or prev_hash == expected_prev
        if recomputed != stored_hash or not link_ok:
            broken_ids.append(str(row.id))
        else:
            verified += 1
        expected_prev = stored_hash

    intact = len(broken_ids) == 0
    return {
        "companyId": str(company_id),
        "checked": len(ordered),
        "checkedCount": len(ordered),
        "verified": verified,
        "legacyUnchained": legacy_unchained,
        "brokenCount": len(broken_ids),
        "brokenIds": broken_ids[:20],
        "brokenAtId": broken_ids[0] if broken_ids else None,
        "intact": intact,
        "valid": intact,
    }
