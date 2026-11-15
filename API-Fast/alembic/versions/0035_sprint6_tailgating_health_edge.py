"""BL-14 / BL-15 / BL-17: Tailgating anti-passback, door held-open health, and Wiegand/OSDP edge bridge columns.

Revision ID: 0035_sprint6_tailgating_health_edge
Revises: 0034_offline_hmac_and_fire_alarm
Create Date: 2026-11-15
"""
from __future__ import annotations

from alembic import op

revision = "0035_sprint6_tailgating_health_edge"
down_revision = "0034_offline_hmac_and_fire_alarm"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE sentinel_access_zone
            ADD COLUMN IF NOT EXISTS anti_passback_enabled BOOLEAN NOT NULL DEFAULT false,
            ADD COLUMN IF NOT EXISTS anti_passback_minutes INTEGER NOT NULL DEFAULT 15,
            ADD COLUMN IF NOT EXISTS door_held_max_seconds INTEGER NOT NULL DEFAULT 30,
            ADD COLUMN IF NOT EXISTS door_open_since TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS edge_protocol VARCHAR(20) NOT NULL DEFAULT 'WEBHOOK',
            ADD COLUMN IF NOT EXISTS edge_bridge_url VARCHAR(255),
            ADD COLUMN IF NOT EXISTS osdp_address INTEGER NOT NULL DEFAULT 0;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE sentinel_access_zone
            DROP COLUMN IF EXISTS osdp_address,
            DROP COLUMN IF EXISTS edge_bridge_url,
            DROP COLUMN IF EXISTS edge_protocol,
            DROP COLUMN IF EXISTS door_open_since,
            DROP COLUMN IF EXISTS door_held_max_seconds,
            DROP COLUMN IF EXISTS anti_passback_minutes,
            DROP COLUMN IF EXISTS anti_passback_enabled;
        """
    )
