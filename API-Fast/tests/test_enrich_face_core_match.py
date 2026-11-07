"""Contract tests for Face Core BFF enrich (mocked DB, no Face Core HTTP)."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# InsightFace / ONNX are stubbed by tests/conftest.py when the GPU stack is not installed;
# cv2 is always the real module (other tests exercise OpenCV-based anti-spoofing).
from src.controllers.face_controller import _enrich_face_core_match  # noqa: E402
from src.models.member import StatusType  # noqa: E402


def _fake_member(member_id: uuid.UUID) -> MagicMock:
    m = MagicMock()
    m.memberId = member_id
    m.username = "emp1"
    m.email = "emp1@test.local"
    m.firstName = "Emp"
    m.lastName = "One"
    m.phoneNumber = None
    m.picture = None
    # An active member: MagicMock attributes are truthy, so these must be set explicitly
    # (``deletedAt`` would otherwise read as "soft-deleted" → 404).
    m.deletedAt = None
    m.status = StatusType.ENABLE
    return m


@pytest.mark.asyncio
async def test_enrich_face_core_match_maps_member_and_proxy_url():
    company_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    member_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4")
    face_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

    member = _fake_member(member_id)
    db = AsyncMock()
    db.get = AsyncMock(return_value=member)

    emp_result = MagicMock()
    emp_result.first.return_value = (uuid.uuid4(),)
    db.execute = AsyncMock(return_value=emp_result)

    fc = {
        "matched": True,
        "subjectId": str(member_id),
        "faceId": face_id,
        "distance": 0.12,
        "threshold": 0.4,
        "confidence": 0.88,
        "confidencePercent": 88.0,
        "matchMargin": 0.7,
        "matchQuality": "high",
        "livenessPassed": False,
    }

    out = await _enrich_face_core_match(db, company_id, fc)

    assert out["matched"] is True
    assert out["memberId"] == str(member_id)
    assert out["faceEncodingId"] == face_id
    assert out["member"]["fullName"] == "Emp One"
    assert out["enrolledImageUrl"] == (
        f"/face/enrolled-images/{face_id}?companyId={company_id}"
    )


@pytest.mark.asyncio
async def test_enrich_rejects_member_not_in_company():
    company_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    member_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4")

    db = AsyncMock()
    db.get = AsyncMock(return_value=_fake_member(member_id))
    emp_result = MagicMock()
    emp_result.first.return_value = None
    db.execute = AsyncMock(return_value=emp_result)

    fc = {"matched": True, "subjectId": str(member_id), "faceId": "f1"}

    with pytest.raises(HTTPException) as exc:
        await _enrich_face_core_match(db, company_id, fc)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_enrich_rejects_unmatched_payload():
    db = AsyncMock()
    with pytest.raises(HTTPException) as exc:
        await _enrich_face_core_match(
            db, uuid.uuid4(), {"matched": False, "subjectId": "x"}
        )
    assert exc.value.status_code == 401
