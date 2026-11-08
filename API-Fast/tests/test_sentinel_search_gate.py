"""F3: stationMode search gate — ATTENDANCE skips sentinel; WATCHLIST calls it."""
from __future__ import annotations

import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

_mock_insight = MagicMock()
sys.modules["insightface"] = _mock_insight
sys.modules["insightface.app"] = _mock_insight.app
sys.modules["cv2"] = MagicMock()
sys.modules["onnxruntime"] = MagicMock()

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.controllers.face_controller import (  # noqa: E402
    _resolve_match_response,
    should_run_sentinel_search,
)
from src.routes import sentinel_routes  # noqa: E402

COMPANY_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
ENCODING = [0.01] * 512


def test_should_run_sentinel_search_matrix():
    assert should_run_sentinel_search(None) is False
    assert should_run_sentinel_search("") is False
    assert should_run_sentinel_search("ATTENDANCE") is False
    assert should_run_sentinel_search("UNIFIED_HYBRID") is False
    assert should_run_sentinel_search("WATCHLIST") is True
    assert should_run_sentinel_search("WATCHLIST_MONITOR") is True
    assert should_run_sentinel_search("ACCESS_CONTROL") is True
    assert should_run_sentinel_search("VISITOR") is True
    assert should_run_sentinel_search("VISITOR_CHECKIN") is True
    assert should_run_sentinel_search("EVENTS") is True
    assert should_run_sentinel_search("EVENT_CHECKIN") is True
    assert should_run_sentinel_search("COMMAND") is True
    assert should_run_sentinel_search("watchlist_monitor") is True


@pytest.mark.asyncio
async def test_attendance_skips_evaluate_kiosk_sentinel_match():
    member_id = uuid.uuid4()
    member = MagicMock()
    member.memberId = member_id
    member.username = "emp1"
    member.email = "e@t.local"
    member.firstName = "Emp"
    member.lastName = "One"
    member.phoneNumber = None
    member.picture = None
    member.deletedAt = None
    member.status = 1

    db = AsyncMock()
    db.get = AsyncMock(return_value=member)
    evaluate = AsyncMock(return_value={"accessGranted": True, "identityType": "VIP"})

    with (
        patch(
            "src.controllers.face_controller._search_face_pgvector",
            AsyncMock(return_value=(uuid.uuid4(), member_id, 0.2)),
        ),
        patch.object(sentinel_routes, "evaluate_kiosk_sentinel_match", evaluate),
    ):
        out = await _resolve_match_response(
            db,
            ENCODING,
            liveness_passed=True,
            companyId=COMPANY_ID,
            stationMode="ATTENDANCE",
        )

    evaluate.assert_not_awaited()
    assert out["matched"] is True
    assert out.get("sentinelMatch") is None


@pytest.mark.asyncio
async def test_missing_station_mode_treated_as_attendance_skip():
    from fastapi import HTTPException

    evaluate = AsyncMock()
    db = AsyncMock()
    with (
        patch(
            "src.controllers.face_controller._search_face_pgvector",
            AsyncMock(return_value=None),
        ),
        patch.object(sentinel_routes, "evaluate_kiosk_sentinel_match", evaluate),
        pytest.raises(HTTPException) as exc,
    ):
        await _resolve_match_response(
            db, ENCODING, liveness_passed=False, companyId=COMPANY_ID
        )
    evaluate.assert_not_awaited()
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_watchlist_calls_evaluate_kiosk_sentinel_match():
    meta = {
        "identityId": str(uuid.uuid4()),
        "identityType": "VIP",
        "fullName": "VIP Guest",
        "severity": "INFO",
        "alertNote": None,
        "seatNumber": None,
        "pictureUrl": None,
        "distance": 0.15,
        "confidencePercent": 85.0,
        "accessGranted": True,
    }
    evaluate = AsyncMock(return_value=meta)
    db = AsyncMock()
    with (
        patch(
            "src.controllers.face_controller._search_face_pgvector",
            AsyncMock(return_value=None),
        ),
        patch.object(sentinel_routes, "evaluate_kiosk_sentinel_match", evaluate),
    ):
        out = await _resolve_match_response(
            db,
            ENCODING,
            liveness_passed=False,
            companyId=COMPANY_ID,
            stationMode="WATCHLIST",
        )

    evaluate.assert_awaited_once()
    assert out["sentinelMatch"]["identityType"] == "VIP"
    assert out["matched"] is True
