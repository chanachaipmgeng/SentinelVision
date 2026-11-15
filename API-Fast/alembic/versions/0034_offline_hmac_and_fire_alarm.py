"""BL-12 / BL-13: Offline kiosk HMAC sync columns and access zone/incident direction.

Revision ID: 0034_offline_hmac_and_fire_alarm
Revises: 0033_roster_swap_and_gps_integrity
Create Date: 2026-11-15
"""
from __future__ import annotations

from alembic import op

revision = "0034_offline_hmac_and_fire_alarm"
down_revision = "0033_roster_swap_and_gps_integrity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE employee_timestamp
            ADD COLUMN IF NOT EXISTS client_event_id VARCHAR(80),
            ADD COLUMN IF NOT EXISTS is_offline_sync BOOLEAN NOT NULL DEFAULT false;

        CREATE UNIQUE INDEX IF NOT EXISTS uq_emp_ts_company_client_event
            ON employee_timestamp ("companyId", client_event_id)
            WHERE client_event_id IS NOT NULL;

        ALTER TABLE sentinel_access_zone
            ADD COLUMN IF NOT EXISTS direction VARCHAR(20) NOT NULL DEFAULT 'BIDIRECTIONAL';

        ALTER TABLE sentinel_incident_log
            ADD COLUMN IF NOT EXISTS direction VARCHAR(20);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE sentinel_incident_log DROP COLUMN IF EXISTS direction;
        ALTER TABLE sentinel_access_zone DROP COLUMN IF EXISTS direction;
        DROP INDEX IF EXISTS uq_emp_ts_company_client_event;
        ALTER TABLE employee_timestamp
            DROP COLUMN IF EXISTS is_offline_sync,
            DROP COLUMN IF EXISTS client_event_id;
        """
    )
