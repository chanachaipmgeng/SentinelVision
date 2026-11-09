"""Tenant API key CRUD + Bearer ``sv_…`` verification."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.company_api_key import CompanyApiKey

API_KEY_PREFIX = "sv_"
VALID_SCOPES = frozenset({"cameras.read", "incidents.read"})
# sv_ + 8 hex prefix chars shown in UI; remainder is secret.
_PREFIX_HEX_LEN = 8
_SECRET_BYTES = 24


def hash_api_key(raw: str) -> str:
    return hashlib.sha256((raw or "").strip().encode("utf-8")).hexdigest()


def _normalize_scopes(raw: Any) -> list[str]:
    if not isinstance(raw, (list, tuple, set)):
        return []
    out: list[str] = []
    for item in raw:
        code = str(item or "").strip()
        if code in VALID_SCOPES and code not in out:
            out.append(code)
    return out


def _public(row: CompanyApiKey) -> dict[str, Any]:
    return {
        "apiKeyId": str(row.apiKeyId),
        "companyId": str(row.companyId),
        "name": row.name,
        "keyPrefix": row.keyPrefix,
        "scopes": list(row.scopes or []),
        "createdByMemberId": str(row.createdByMemberId) if row.createdByMemberId else None,
        "createdAt": row.createdAt,
        "lastUsedAt": row.lastUsedAt,
        "revokedAt": row.revokedAt,
        "notes": row.notes,
        "active": row.revokedAt is None,
    }


def mint_api_key_plaintext() -> tuple[str, str]:
    """Return (full_token, display_prefix)."""
    prefix_hex = secrets.token_hex(_PREFIX_HEX_LEN // 2)
    secret = secrets.token_urlsafe(_SECRET_BYTES)
    display_prefix = f"{API_KEY_PREFIX}{prefix_hex}"
    full = f"{display_prefix}_{secret}"
    return full, display_prefix


async def list_api_keys(
    db: AsyncSession, company_id: UUID, *, include_revoked: bool = True
) -> list[dict[str, Any]]:
    stmt = (
        select(CompanyApiKey)
        .where(CompanyApiKey.companyId == company_id)
        .order_by(CompanyApiKey.createdAt.desc())
    )
    if not include_revoked:
        stmt = stmt.where(CompanyApiKey.revokedAt.is_(None))
    rows = list((await db.execute(stmt)).scalars().all())
    return [_public(r) for r in rows]


async def create_api_key(
    db: AsyncSession,
    company_id: UUID,
    *,
    name: str,
    scopes: Any,
    created_by: Optional[UUID] = None,
    notes: Optional[str] = None,
) -> dict[str, Any]:
    clean_name = (name or "").strip()
    if not clean_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name is required")
    if len(clean_name) > 120:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name too long")
    clean_scopes = _normalize_scopes(scopes)
    if not clean_scopes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="scopes must include cameras.read and/or incidents.read",
        )
    plaintext, display_prefix = mint_api_key_plaintext()
    row = CompanyApiKey(
        companyId=company_id,
        name=clean_name,
        keyPrefix=display_prefix,
        keyHash=hash_api_key(plaintext),
        scopes=clean_scopes,
        createdByMemberId=created_by,
        notes=(notes or "").strip() or None,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    out = _public(row)
    # Plaintext returned once — never stored / never listed again.
    out["apiKey"] = plaintext
    return out


async def revoke_api_key(
    db: AsyncSession, company_id: UUID, api_key_id: UUID
) -> dict[str, Any]:
    row = await db.get(CompanyApiKey, api_key_id)
    if row is None or row.companyId != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    if row.revokedAt is None:
        row.revokedAt = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(row)
    return _public(row)


async def verify_bearer_api_key(
    db: AsyncSession, token: str
) -> Optional[CompanyApiKey]:
    """Look up an active key by sha256(token). Returns None when invalid/revoked."""
    raw = (token or "").strip()
    if not raw.startswith(API_KEY_PREFIX):
        return None
    digest = hash_api_key(raw)
    stmt = select(CompanyApiKey).where(
        CompanyApiKey.keyHash == digest,
        CompanyApiKey.revokedAt.is_(None),
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        return None
    # Soft lifecycle: refuse keys for suspended/offboarded tenants.
    from ..models.company import Company, LifecycleStatus

    company = await db.get(Company, row.companyId)
    if company is not None:
        life = (company.lifecycleStatus or LifecycleStatus.ACTIVE).upper()
        if life != LifecycleStatus.ACTIVE:
            return None
    row.lastUsedAt = datetime.now(timezone.utc)
    await db.commit()
    return row


def api_key_allows(scopes: list[str] | None, permission: str) -> bool:
    return permission in set(scopes or [])
