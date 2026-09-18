"""Append-only audit log."""
from __future__ import annotations

import logging
from uuid import uuid4

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.sql import func

from ..config.database import Base, async_session

logger = logging.getLogger("dpu.audit")


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
    row = AuditLog(
        actorMemberId=actor_id,
        actorRole=role,
        companyId=UUID(str(company_id)) if company_id else None,
        action=action,
        entityType=entity_type,
        entityId=entity_id,
        path=path[:500] if path else None,
        statusCode=str(status_code) if status_code else None,
        ip=ip,
        userAgent=(user_agent or "")[:500] or None,
        requestId=request_id,
        detail=detail,
    )
    async with async_session() as db:
        db.add(row)
        await db.commit()
