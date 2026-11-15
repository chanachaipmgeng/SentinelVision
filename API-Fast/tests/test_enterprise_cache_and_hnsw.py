"""Unit tests for Enterprise P0 Quick Wins: Redis hot-path cache & pgvector HNSW tuning."""
from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import DBAPIError

from src.services import audit_service, cache_service, company_module_service, face_match_service


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str):
        return self.store.get(key)

    async def set(self, key: str, value: str, *, nx: bool = False, ex: int | None = None):
        if nx and key in self.store:
            return False
        self.store[key] = value
        return True

    async def delete(self, key: str):
        return 1 if self.store.pop(key, None) is not None else 0


@pytest.mark.asyncio
async def test_cache_service_fallback_when_redis_unavailable(monkeypatch):
    monkeypatch.setattr(cache_service, "get_redis", lambda: None)
    assert await cache_service.cache_get_json("k1") is None
    assert await cache_service.cache_set_json("k1", {"a": 1}) is False
    assert await cache_service.cache_delete("k1") is False
    assert await cache_service.kiosk_scan_debounce_check("c1", "m1", ttl_seconds=5) is True


@pytest.mark.asyncio
async def test_cache_service_roundtrip_and_debounce(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(cache_service, "get_redis", lambda: fake)

    assert await cache_service.cache_set_json("sv:test", {"enabled": True}, ttl_seconds=60) is True
    assert await cache_service.cache_get_json("sv:test") == {"enabled": True}
    assert await cache_service.cache_delete("sv:test") is True
    assert await cache_service.cache_get_json("sv:test") is None

    assert await cache_service.kiosk_scan_debounce_check("c1", "m1", ttl_seconds=5) is True
    assert await cache_service.kiosk_scan_debounce_check("c1", "m1", ttl_seconds=5) is False


@pytest.mark.asyncio
async def test_company_module_config_uses_cache_and_invalidates(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(cache_service, "get_redis", lambda: fake)
    cid = uuid4()

    db = MagicMock()
    db.get = AsyncMock(return_value=None)
    db.add = MagicMock()
    db.commit = AsyncMock()

    first = await company_module_service.get_company_module_config(db, cid)
    assert "ATTENDANCE" in first["enabledModules"]
    assert db.get.await_count == 1

    # Second read hits Redis cache without querying DB
    second = await company_module_service.get_company_module_config(db, cid)
    assert second == first
    assert db.get.await_count == 1

    # Saving invalidates the cached key
    await company_module_service.save_company_module_config(
        db,
        cid,
        {"enabledModules": ["ATTENDANCE"], "defaultStationMode": "ATTENDANCE"},
    )
    assert company_module_service._modules_cache_key(cid) not in fake.store


@pytest.mark.asyncio
async def test_hnsw_session_params_fallback_on_older_pgvector(monkeypatch):
    executed: list[str] = []

    class _FakeDb:
        @asynccontextmanager
        async def begin_nested(self):
            yield

        async def execute(self, stmt):
            sql = str(stmt)
            executed.append(sql)
            if "hnsw.iterative_scan" in sql:
                raise DBAPIError(sql, {}, Exception("unrecognized configuration parameter"))

    monkeypatch.setattr(face_match_service.settings, "HNSW_EF_SEARCH", 64)
    monkeypatch.setattr(face_match_service.settings, "HNSW_ITERATIVE_SCAN", "relaxed_order")

    await face_match_service._apply_hnsw_session_params(_FakeDb())  # type: ignore[arg-type]
    assert any("hnsw.ef_search = 64" in s for s in executed)
    assert any("hnsw.iterative_scan = relaxed_order" in s for s in executed)


@pytest.mark.asyncio
async def test_audit_chain_verification_detects_tampering():
    cid = uuid4()
    actor_id = uuid4()

    h1 = audit_service.compute_audit_hash(
        audit_service.GENESIS_HASH,
        company_id=str(cid),
        action="LOGIN",
        actor_member_id=str(actor_id),
        entity_type="member",
        entity_id=str(actor_id),
        path="/auth/login",
        status_code="200",
        detail_payload={"method": "password"},
    )
    h2 = audit_service.compute_audit_hash(
        h1,
        company_id=str(cid),
        action="UPDATE_ZONE",
        actor_member_id=str(actor_id),
        entity_type="zone",
        entity_id="z1",
        path="/sentinel/zones/z1",
        status_code="200",
        detail_payload={"name": "Lobby"},
    )

    row1 = audit_service.AuditLog(
        id=uuid4(),
        companyId=cid,
        actorMemberId=actor_id,
        action="LOGIN",
        entityType="member",
        entityId=str(actor_id),
        path="/auth/login",
        statusCode="200",
        detail={"method": "password", "_integrity": {"algo": "sha256-v1", "prevHash": audit_service.GENESIS_HASH, "hash": h1}},
    )
    row2 = audit_service.AuditLog(
        id=uuid4(),
        companyId=cid,
        actorMemberId=actor_id,
        action="UPDATE_ZONE",
        entityType="zone",
        entityId="z1",
        path="/sentinel/zones/z1",
        statusCode="200",
        detail={"name": "Lobby", "_integrity": {"algo": "sha256-v1", "prevHash": h1, "hash": h2}},
    )

    # DB returns newest first; verify_audit_chain reverses to oldest->newest
    db = MagicMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[row2, row1]))))
    )
    ok_res = await audit_service.verify_audit_chain(db, cid)
    assert ok_res["intact"] is True
    assert ok_res["verified"] == 2
    assert ok_res["brokenCount"] == 0

    # Tamper with row1 action
    row1.action = "TAMPERED_ACTION"
    bad_res = await audit_service.verify_audit_chain(db, cid)
    assert bad_res["intact"] is False
    assert bad_res["brokenCount"] == 1
    assert str(row1.id) in bad_res["brokenIds"]

