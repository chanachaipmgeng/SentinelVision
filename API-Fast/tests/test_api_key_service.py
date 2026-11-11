"""Tenant API key mint / hash / scope helpers."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.services import api_key_service as aks  # noqa: E402

COMPANY_ID = uuid4()


def test_mint_prefix_and_hash():
    plain, prefix = aks.mint_api_key_plaintext()
    assert plain.startswith("sv_")
    assert prefix.startswith("sv_")
    assert plain.startswith(prefix)
    assert "_" in plain[len(prefix) :]
    digest = aks.hash_api_key(plain)
    assert len(digest) == 64
    assert digest == aks.hash_api_key(plain)
    assert digest != aks.hash_api_key(plain + "x")


def test_normalize_scopes():
    assert aks._normalize_scopes(["cameras.read", "incidents.read", "cameras.read", "x"]) == [
        "cameras.read",
        "incidents.read",
    ]
    assert aks._normalize_scopes(None) == []
    assert aks._normalize_scopes(["nope"]) == []


@pytest.mark.asyncio
async def test_create_requires_scopes():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    with pytest.raises(HTTPException) as exc:
        await aks.create_api_key(db, COMPANY_ID, name="ops", scopes=[])
    assert getattr(exc.value, "status_code", None) == 400


@pytest.mark.asyncio
async def test_create_returns_plaintext_once():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    async def _refresh(row):
        row.apiKeyId = uuid4()
        row.createdAt = None
        row.lastUsedAt = None
        row.revokedAt = None

    db.refresh = AsyncMock(side_effect=_refresh)
    out = await aks.create_api_key(
        db,
        COMPANY_ID,
        name="reader",
        scopes=["cameras.read"],
        created_by=uuid4(),
    )
    assert out["apiKey"].startswith("sv_")
    assert out["keyPrefix"].startswith("sv_")
    assert out["scopes"] == ["cameras.read"]
    assert out["active"] is True
    assert db.add.called
    added = db.add.call_args[0][0]
    assert added.keyHash == aks.hash_api_key(out["apiKey"])
    assert "apiKey" not in aks._public(added)


@pytest.mark.asyncio
async def test_revoke_sets_timestamp():
    db = AsyncMock()
    row = MagicMock()
    row.companyId = COMPANY_ID
    row.revokedAt = None
    row.apiKeyId = uuid4()
    row.name = "x"
    row.keyPrefix = "sv_abcd"
    row.scopes = ["incidents.read"]
    row.createdByMemberId = None
    row.createdAt = None
    row.lastUsedAt = None
    row.notes = None
    db.get = AsyncMock(return_value=row)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    out = await aks.revoke_api_key(db, COMPANY_ID, row.apiKeyId)
    assert row.revokedAt is not None
    assert out["active"] is False


def test_api_key_allows():
    assert aks.api_key_allows(["cameras.read"], "cameras.read")
    assert not aks.api_key_allows(["cameras.read"], "incidents.read")
