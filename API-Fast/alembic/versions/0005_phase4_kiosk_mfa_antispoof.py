"""Phase 4: Kiosk Device Provisioning & Member TOTP 2FA columns.

Revision ID: 0005_phase4_kiosk_mfa_antispoof
Revises: 0004_shifts_leaves_holidays
Create Date: 2026-11-07
"""
from alembic import op

revision = "0005_phase4_kiosk_mfa_antispoof"
down_revision = "0004_shifts_leaves_holidays"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE member ADD COLUMN IF NOT EXISTS totp_secret VARCHAR(128)")
    op.execute("ALTER TABLE member ADD COLUMN IF NOT EXISTS totp_enabled BOOLEAN DEFAULT FALSE")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS kiosk_device (
            "deviceId" UUID PRIMARY KEY,
            "companyId" UUID NOT NULL REFERENCES company("companyId") ON DELETE CASCADE,
            location_id UUID,
            name VARCHAR(120) NOT NULL,
            token_hash VARCHAR(128) NOT NULL,
            last_seen_at TIMESTAMPTZ,
            revoked_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS kiosk_device_company_idx
        ON kiosk_device ("companyId", revoked_at)
        """
    )


def downgrade() -> None:
    pass
