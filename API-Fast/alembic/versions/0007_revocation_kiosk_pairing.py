"""A5: JWT revocation deny-list + one-time kiosk pairing codes.

Revision ID: 0007_revocation_kiosk_pairing
Revises: 0006_sentinel_vision_core
Create Date: 2026-11-07
"""
from alembic import op

revision = "0007_revocation_kiosk_pairing"
down_revision = "0006_sentinel_vision_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS revoked_token (
            jti VARCHAR(96) PRIMARY KEY,
            family_id VARCHAR(64),
            scope VARCHAR(10) NOT NULL DEFAULT 'token',
            exp TIMESTAMPTZ NOT NULL,
            reason VARCHAR(40),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS revoked_token_family_idx
        ON revoked_token (family_id, scope)
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS revoked_token_exp_idx ON revoked_token (exp)")
    op.execute("ALTER TABLE kiosk_device ALTER COLUMN token_hash DROP NOT NULL")
    op.execute("ALTER TABLE kiosk_device ADD COLUMN IF NOT EXISTS token_family VARCHAR(64)")
    op.execute("ALTER TABLE kiosk_device ADD COLUMN IF NOT EXISTS pairing_code_hash VARCHAR(128)")
    op.execute("ALTER TABLE kiosk_device ADD COLUMN IF NOT EXISTS pairing_expires_at TIMESTAMPTZ")
    op.execute("ALTER TABLE kiosk_device ADD COLUMN IF NOT EXISTS paired_at TIMESTAMPTZ")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS kiosk_device_pairing_code_idx
        ON kiosk_device (pairing_code_hash)
        WHERE pairing_code_hash IS NOT NULL
        """
    )


def downgrade() -> None:
    pass
