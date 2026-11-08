"""A7: a BLACKLIST/POI watchlist hit must never leak identity to the public kiosk.

The kiosk (HTTP identify / check-in and the WS kiosk path, which share
``_resolve_match_response``) gets a generic Thai refusal; the full alert goes to
``sentinel_incident_log`` + ``notification_outbox`` only.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Avoid InsightFace/onnx at import time
_mock_insight = MagicMock()
sys.modules["insightface"] = _mock_insight
sys.modules["insightface.app"] = _mock_insight.app
sys.modules["cv2"] = MagicMock()
sys.modules["onnxruntime"] = MagicMock()

import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.controllers.face_controller import (  # noqa: E402
    KIOSK_ACCESS_DENIED_MESSAGE,
    _resolve_match_response,
)
from src.models.sentinel import SentinelIdentity, SentinelIncidentLog  # noqa: E402
from src.routes import sentinel_routes  # noqa: E402
from src.services.notification_service import NotificationOutbox  # noqa: E402

COMPANY_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
IDENTITY_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
TARGET_NAME = "Somchai Blacklisted"
SNAPSHOT_URL = "/images/sentinel/target.jpg"
ENCODING = [0.01] * 512

SENSITIVE_TOKENS = (TARGET_NAME, "Somchai", str(IDENTITY_ID), "BLACKLIST", "Watchlist", SNAPSHOT_URL)


def _blacklist_meta() -> dict:
    return {
        "identityId": str(IDENTITY_ID),
        "identityType": "BLACKLIST",
        "fullName": TARGET_NAME,
        "severity": "CRITICAL",
        "alertNote": "Do not admit",
        "seatNumber": None,
        "pictureUrl": SNAPSHOT_URL,
        "distance": 0.11,
        "confidencePercent": 89.0,
        "accessGranted": False,
    }


def _fake_member(member_id: uuid.UUID) -> MagicMock:
    m = MagicMock()
    m.memberId = member_id
    m.username = "emp1"
    m.email = "emp1@test.local"
    m.firstName = "Emp"
    m.lastName = "One"
    m.phoneNumber = None
    m.picture = None
    m.deletedAt = None
    return m


def _assert_generic_denial(exc: HTTPException) -> None:
    assert exc.status_code == 403
    assert exc.detail == KIOSK_ACCESS_DENIED_MESSAGE
    assert isinstance(exc.detail, str)
    for token in SENSITIVE_TOKENS:
        assert token not in exc.detail
    # No side-channel fields on the exception either (WS forwards detail/status only).
    assert not exc.headers


@pytest.mark.asyncio
async def test_blacklist_hit_without_employee_match_returns_generic_denial():
    db = AsyncMock()
    with (
        patch("src.controllers.face_controller._search_face_pgvector", AsyncMock(return_value=None)),
        patch.object(sentinel_routes, "evaluate_kiosk_sentinel_match", AsyncMock(return_value=_blacklist_meta())),
    ):
        with pytest.raises(HTTPException) as exc:
            await _resolve_match_response(
                db,
                ENCODING,
                liveness_passed=False,
                companyId=COMPANY_ID,
                stationMode="WATCHLIST",
            )
    _assert_generic_denial(exc.value)


@pytest.mark.asyncio
async def test_blacklist_hit_overrides_employee_match_and_leaks_nothing():
    member_id = uuid.uuid4()
    db = AsyncMock()
    db.get = AsyncMock(return_value=_fake_member(member_id))
    with (
        patch(
            "src.controllers.face_controller._search_face_pgvector",
            AsyncMock(return_value=(uuid.uuid4(), member_id, 0.2)),
        ),
        patch.object(sentinel_routes, "evaluate_kiosk_sentinel_match", AsyncMock(return_value=_blacklist_meta())),
    ):
        with pytest.raises(HTTPException) as exc:
            await _resolve_match_response(
                db,
                ENCODING,
                liveness_passed=True,
                companyId=COMPANY_ID,
                stationMode="WATCHLIST",
            )
    _assert_generic_denial(exc.value)
    assert str(member_id) not in exc.value.detail


@pytest.mark.asyncio
async def test_vip_hit_still_returns_sentinel_match_payload():
    meta = {**_blacklist_meta(), "identityType": "VIP", "severity": "INFO", "accessGranted": True}
    db = AsyncMock()
    with (
        patch("src.controllers.face_controller._search_face_pgvector", AsyncMock(return_value=None)),
        patch.object(sentinel_routes, "evaluate_kiosk_sentinel_match", AsyncMock(return_value=meta)),
    ):
        out = await _resolve_match_response(
            db,
            ENCODING,
            liveness_passed=False,
            companyId=COMPANY_ID,
            stationMode="ACCESS_CONTROL",
        )
    assert out["matched"] is True
    assert out["sentinelMatch"]["identityType"] == "VIP"


@pytest.mark.asyncio
async def test_blacklist_hit_enqueues_incident_and_notification_outbox():
    ident = SentinelIdentity(
        identityId=IDENTITY_ID,
        companyId=COMPANY_ID,
        identityType="BLACKLIST",
        fullName=TARGET_NAME,
        severity="CRITICAL",
        alertNote="Do not admit",
        pictureUrl=SNAPSHOT_URL,
        allowedZoneIds=[],
        status="ACTIVE",
    )
    db = AsyncMock()
    db.add = MagicMock()
    # record_incident queries for an open dedupe match before insert.
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )
    with patch(
        "src.services.sentinel_incident_service.search_sentinel_identity_pgvector",
        AsyncMock(return_value=(ident, 0.11)),
    ):
        meta = await sentinel_routes.evaluate_kiosk_sentinel_match(db, COMPANY_ID, ENCODING, 0.4)

    assert meta["accessGranted"] is False

    added = [call.args[0] for call in db.add.call_args_list]
    incidents = [o for o in added if isinstance(o, SentinelIncidentLog)]
    outbox = [o for o in added if isinstance(o, NotificationOutbox)]
    assert len(incidents) == 1 and len(outbox) == 1
    db.commit.assert_awaited_once()

    inc = incidents[0]
    assert inc.eventType == "BLACKLIST_ALERT"
    assert inc.severity == "CRITICAL"
    assert inc.subjectName == TARGET_NAME
    assert inc.zoneName == "Live Face Kiosk"
    assert inc.snapshotUrl == SNAPSHOT_URL

    ob = outbox[0]
    assert ob.event == "sentinel.blacklist_detected"
    assert ob.channel == "webhook"
    assert ob.companyId == COMPANY_ID
    # Staff channel carries who / where / when / snapshot that the kiosk never sees.
    assert ob.payload["subjectName"] == TARGET_NAME
    assert ob.payload["identityId"] == str(IDENTITY_ID)
    assert ob.payload["identityType"] == "BLACKLIST"
    assert ob.payload["zoneName"] == "Live Face Kiosk"
    assert ob.payload["snapshotUrl"] == SNAPSHOT_URL
    assert ob.payload["detectedAt"]
