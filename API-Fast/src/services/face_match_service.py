"""1:N face match against pgvector (Employees & SentinelVision Identities)."""
from __future__ import annotations

from datetime import datetime, timezone
import time
from typing import List, Optional
from uuid import UUID

from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.settings import settings
from ..models.company_employee import CompanyEmployee
from ..models.face_encoding import FaceEncoding
from ..models.member import Member, StatusType
from ..models.sentinel import SentinelIdentity
from .observability import observe_face_match


async def search_face_pgvector(
    db: AsyncSession,
    target_encoding: List[float],
    threshold: float,
    *,
    companyId: Optional[UUID] = None,
):
    t0 = time.perf_counter()
    try:
        distance_expr = FaceEncoding.embedding.cosine_distance(target_encoding)
        await db.execute(text(f"SET LOCAL hnsw.ef_search = {int(settings.HNSW_EF_SEARCH)}"))
        stmt = (
            select(
                FaceEncoding.faceEncodingId,
                FaceEncoding.memberId,
                distance_expr.label("distance"),
            )
            .join(Member, Member.memberId == FaceEncoding.memberId)
            .where(
                Member.deletedAt.is_(None),
                Member.status == StatusType.ENABLE,
            )
        )
        if companyId is not None:
            stmt = stmt.join(
                CompanyEmployee, CompanyEmployee.memberId == FaceEncoding.memberId
            ).where(
                CompanyEmployee.companyId == companyId,
                CompanyEmployee.deletedAt.is_(None),
            )
        stmt = stmt.order_by(distance_expr).limit(1)
        row = (await db.execute(stmt)).first()
        if row is None:
            return None
        face_encoding_id, member_id, distance = row
        if distance is None or float(distance) >= threshold:
            return None
        return face_encoding_id, member_id, float(distance)
    finally:
        observe_face_match("pgvector_member", time.perf_counter() - t0)


async def search_sentinel_identity_pgvector(
    db: AsyncSession,
    target_encoding: List[float],
    threshold: float,
    *,
    companyId: UUID,
    identity_types: Optional[List[str]] = None,
    event_id: Optional[UUID] = None,
):
    """1:N search against SentinelIdentity (BLACKLIST, POI, VIP, VISITOR, EVENT_ATTENDEE) within company."""
    t0 = time.perf_counter()
    try:
        now = datetime.now(timezone.utc)
        distance_expr = SentinelIdentity.embedding.cosine_distance(target_encoding)
        await db.execute(text(f"SET LOCAL hnsw.ef_search = {int(settings.HNSW_EF_SEARCH)}"))
        stmt = select(
            SentinelIdentity,
            distance_expr.label("distance"),
        ).where(
            SentinelIdentity.companyId == companyId,
            SentinelIdentity.deletedAt.is_(None),
            SentinelIdentity.status == "ACTIVE",
            SentinelIdentity.embedding.is_not(None),
            or_(SentinelIdentity.validFrom.is_(None), SentinelIdentity.validFrom <= now),
            or_(SentinelIdentity.expiresAt.is_(None), SentinelIdentity.expiresAt >= now),
        )
        if identity_types:
            stmt = stmt.where(SentinelIdentity.identityType.in_(identity_types))
        if event_id is not None:
            stmt = stmt.where(SentinelIdentity.eventId == event_id)
        stmt = stmt.order_by(distance_expr).limit(1)
        row = (await db.execute(stmt)).first()
        if row is None:
            return None
        identity_obj, distance = row
        if distance is None or float(distance) >= threshold:
            return None
        return identity_obj, float(distance)
    finally:
        observe_face_match("pgvector_sentinel", time.perf_counter() - t0)
