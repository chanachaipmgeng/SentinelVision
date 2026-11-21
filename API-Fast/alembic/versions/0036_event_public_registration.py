"""P2: Public Event Registration and Self-Service Portal.

Revision ID: 0036_event_public_registration
Revises: 0035_sprint6_tailgating_health_edge
Create Date: 2026-11-21
"""
from __future__ import annotations

from alembic import op

revision = "0036_event_public_registration"
down_revision = "0035_sprint6_tailgating_health_edge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE sentinel_event
            ADD COLUMN IF NOT EXISTS public_slug VARCHAR(100),
            ADD COLUMN IF NOT EXISTS registration_open BOOLEAN NOT NULL DEFAULT false,
            ADD COLUMN IF NOT EXISTS registration_deadline TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS description TEXT;

        CREATE UNIQUE INDEX IF NOT EXISTS ix_sentinel_event_public_slug
            ON sentinel_event(public_slug);

        CREATE TABLE IF NOT EXISTS sentinel_event_registration (
            "registrationId" UUID PRIMARY KEY,
            "eventId" UUID NOT NULL REFERENCES sentinel_event("eventId") ON DELETE CASCADE,
            "companyId" UUID NOT NULL REFERENCES company("companyId") ON DELETE CASCADE,
            identity_id UUID REFERENCES sentinel_identity("identityId") ON DELETE SET NULL,
            full_name VARCHAR(160) NOT NULL,
            email VARCHAR(160) NOT NULL,
            phone_number VARCHAR(50),
            organization VARCHAR(160),
            status VARCHAR(30) NOT NULL DEFAULT 'REGISTERED',
            consent_at TIMESTAMPTZ NOT NULL,
            check_in_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMPTZ
        );

        CREATE INDEX IF NOT EXISTS sentinel_event_reg_event_idx
            ON sentinel_event_registration("eventId", status);

        CREATE INDEX IF NOT EXISTS sentinel_event_reg_company_idx
            ON sentinel_event_registration("companyId", email);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS sentinel_event_registration;
        DROP INDEX IF EXISTS ix_sentinel_event_public_slug;
        ALTER TABLE sentinel_event
            DROP COLUMN IF EXISTS description,
            DROP COLUMN IF EXISTS registration_deadline,
            DROP COLUMN IF EXISTS registration_open,
            DROP COLUMN IF EXISTS public_slug;
        """
    )
