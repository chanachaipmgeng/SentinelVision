"""Phase 5: tenant company_api_key table for Bearer sv_… keys.

Revision ID: 0025_company_api_key
Revises: 0024_site_floor
Create Date: 2026-11-09

Owned by branch ``feat/phase5-settings-ai-keys``.
"""
from __future__ import annotations

from alembic import op

revision = "0025_company_api_key"
down_revision = "0024_site_floor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS company_api_key (
            "apiKeyId" UUID PRIMARY KEY,
            "companyId" UUID NOT NULL REFERENCES company("companyId") ON DELETE CASCADE,
            name VARCHAR(120) NOT NULL,
            key_prefix VARCHAR(24) NOT NULL,
            key_hash VARCHAR(64) NOT NULL UNIQUE,
            scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
            created_by_member_id UUID REFERENCES member("memberId") ON DELETE SET NULL,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            last_used_at TIMESTAMPTZ,
            revoked_at TIMESTAMPTZ,
            notes TEXT
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS company_api_key_company_idx "
        'ON company_api_key ("companyId")'
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS company_api_key_prefix_idx "
        "ON company_api_key (key_prefix)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS company_api_key_prefix_idx")
    op.execute("DROP INDEX IF EXISTS company_api_key_company_idx")
    op.execute("DROP TABLE IF EXISTS company_api_key")
