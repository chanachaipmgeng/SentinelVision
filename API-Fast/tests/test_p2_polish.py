"""Tests for Phase 10 P2 Enterprise Polish: TensorRT EP, Breakout Rooms, Privacy Masks, Audit Chain Aliases."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from fastapi import HTTPException
import numpy as np
import pytest

from src.services.audit_service import GENESIS_HASH, compute_audit_hash, verify_audit_chain
from src.services.event_session_service import check_in_breakout_room
from src.services.privacy_mask_service import apply_privacy_masks_to_bgr, validate_privacy_masks
from src.utils.face_engine import _resolve_providers_and_ctx


def test_tensorrt_provider_resolution() -> None:
    fake_ort = SimpleNamespace(
        get_available_providers=lambda: [
            "TensorrtExecutionProvider",
            "CUDAExecutionProvider",
            "CPUExecutionProvider",
        ]
    )
    with (
        patch("src.utils.face_engine._cuda_runtime_usable", return_value=True),
        patch.dict("sys.modules", {"onnxruntime": fake_ort}),
        patch("src.utils.face_engine.settings.FACE_TENSORRT_ENABLED", True),
    ):
        providers, ctx_id = _resolve_providers_and_ctx("cuda:0")
        assert providers[0] == "TensorrtExecutionProvider"
        assert ctx_id == 0

    with (
        patch("src.utils.face_engine._cuda_runtime_usable", return_value=True),
        patch("src.utils.face_engine.settings.FACE_TENSORRT_ENABLED", False),
    ):
        providers, ctx_id = _resolve_providers_and_ctx("cuda:0")
        assert providers == ["CUDAExecutionProvider", "CPUExecutionProvider"]
        assert ctx_id == 0


@pytest.mark.asyncio
async def test_breakout_room_capacity_enforcement() -> None:
    company_id = uuid.uuid4()
    event_id = uuid.uuid4()
    ev = SimpleNamespace(eventId=event_id, companyId=company_id, name="Summit", deletedAt=None)

    db = MagicMock()
    db.get = AsyncMock(return_value=ev)

    fake_redis = MagicMock()
    fake_redis.incr = AsyncMock(side_effect=[1, 2])
    fake_redis.expire = AsyncMock(return_value=True)
    fake_redis.decr = AsyncMock(return_value=1)

    with (
        patch("src.services.event_session_service.get_redis", return_value=fake_redis),
        patch("src.services.event_session_service.record_incident", new_callable=AsyncMock) as rec_mock,
    ):
        ok = await check_in_breakout_room(
            db,
            company_id=company_id,
            event_id=event_id,
            room_code="ROOM-A",
            capacity=1,
            subject_name="Alice",
        )
        assert ok["checkedIn"] is True
        assert ok["occupancy"] == 1
        assert rec_mock.call_args.kwargs["event_type"] == "EVENT_SESSION_CHECKIN"

        with pytest.raises(HTTPException) as exc_info:
            await check_in_breakout_room(
                db,
                company_id=company_id,
                event_id=event_id,
                room_code="ROOM-A",
                capacity=1,
                subject_name="Bob",
            )
        assert exc_info.value.status_code == 409
        assert exc_info.value.detail["code"] == "EVENT_ROOM_FULL"


def test_privacy_mask_validation_and_blur() -> None:
    cleaned = validate_privacy_masks([
        {"x": -0.2, "y": 0.1, "w": 0.5, "h": 0.5},
        {"x": 0.1, "y": 0.1, "w": 0.001, "h": 0.001},
    ])
    assert len(cleaned) == 1
    assert cleaned[0]["x"] == 0.0

    # Create 100x100 checkerboard frame; top-left 50x50 masked should blur, bottom-right unchanged
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    frame[::2, ::2] = 255
    masked = apply_privacy_masks_to_bgr(frame, [{"x": 0.0, "y": 0.0, "w": 0.5, "h": 0.5}])
    assert not np.array_equal(masked[:50, :50], frame[:50, :50])
    assert np.array_equal(masked[60:, 60:], frame[60:, 60:])


@pytest.mark.asyncio
async def test_verify_audit_chain_legacy_rows_and_valid_alias() -> None:
    cid = uuid.uuid4()
    legacy_row = SimpleNamespace(
        id=uuid.uuid4(),
        companyId=cid,
        action="LEGACY_OP",
        actorMemberId=None,
        entityType="member",
        entityId=None,
        path="/old",
        statusCode="200",
        detail={"legacy": True},
    )
    h1 = compute_audit_hash(
        GENESIS_HASH,
        company_id=str(cid),
        action="NEW_OP",
        actor_member_id=None,
        entity_type="zone",
        entity_id=None,
        path="/new",
        status_code="200",
        detail_payload={"ok": True},
    )
    chained_row = SimpleNamespace(
        id=uuid.uuid4(),
        companyId=cid,
        action="NEW_OP",
        actorMemberId=None,
        entityType="zone",
        entity_id=None,
        entityId=None,
        path="/new",
        statusCode="200",
        detail={"ok": True, "_integrity": {"algo": "sha256-v1", "prevHash": GENESIS_HASH, "hash": h1}},
    )

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [chained_row, legacy_row]  # DESC order before reversed()
    exec_res = MagicMock()
    exec_res.scalars.return_value = scalars_mock

    db = MagicMock()
    db.execute = AsyncMock(return_value=exec_res)

    res = await verify_audit_chain(db, cid, limit=100)
    assert res["intact"] is True
    assert res["valid"] is True
    assert res["checkedCount"] == 2
    assert res["legacyUnchained"] == 1
    assert res["verified"] == 1
