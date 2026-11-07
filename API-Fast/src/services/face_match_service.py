"""1:N face match against pgvector."""
from __future__ import annotations

import time
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.settings import settings
from ..models.company_employee import CompanyEmployee
from ..models.face_encoding import FaceEncoding
from ..models.member import Member, StatusType
from .observability import observe_histogram


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
        observe_histogram("dpu_pgvector_search_ms", (time.perf_counter() - t0) * 1000.0)
