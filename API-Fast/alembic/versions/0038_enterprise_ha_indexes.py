"""Wave 2 Enterprise HA schema additions: outbox leases/backoff, camera worker leases, and event indexes.

Revision ID: 0038_enterprise_ha_indexes
Revises: 0037_vehicle_parking_rfid
Create Date: 2026-11-27
"""
from __future__ import annotations

from alembic import op

revision = "0038_enterprise_ha_indexes"
down_revision = "0037_vehicle_parking_rfid"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE notification_outbox
            ADD COLUMN IF NOT EXISTS next_attempt_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS lease_until TIMESTAMPTZ;

        CREATE INDEX IF NOT EXISTS notification_outbox_pending_due_idx
            ON notification_outbox(status, next_attempt_at, lease_until);

        ALTER TABLE camera
            ADD COLUMN IF NOT EXISTS analysis_lease_until TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS people_lease_until TIMESTAMPTZ;

        CREATE INDEX IF NOT EXISTS sentinel_identity_company_event_idx
            ON sentinel_identity("companyId", event_id)
            WHERE event_id IS NOT NULL;

        CREATE INDEX IF NOT EXISTS sentinel_incident_company_event_idx
            ON sentinel_incident_log("companyId", event_id, event_type)
            WHERE event_id IS NOT NULL;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS sentinel_incident_company_event_idx;
        DROP INDEX IF EXISTS sentinel_identity_company_event_idx;
        ALTER TABLE camera
            DROP COLUMN IF EXISTS people_lease_until,
            DROP COLUMN IF EXISTS analysis_lease_until;
        DROP INDEX IF EXISTS notification_outbox_pending_due_idx;
        ALTER TABLE notification_outbox
            DROP COLUMN IF EXISTS lease_until,
            DROP COLUMN IF EXISTS next_attempt_at;
        """
    )
