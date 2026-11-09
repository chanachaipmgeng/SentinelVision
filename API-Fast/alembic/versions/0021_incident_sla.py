"""Add sla_due_at on sentinel_incident_log for Phase 4/6B ops.

Revision ID: 0021_incident_sla
Revises: 0020_camera_cctv
Create Date: 2026-11-09

Owned by branch ``feat/phase4-event-ops-6b``. Idempotent ADD COLUMN.
"""
from __future__ import annotations

from alembic import op

revision = "0021_incident_sla"
down_revision = "0020_camera_cctv"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE sentinel_incident_log
        ADD COLUMN IF NOT EXISTS sla_due_at TIMESTAMPTZ
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS sentinel_incident_sla_due_idx
        ON sentinel_incident_log ("companyId", status, sla_due_at)
        WHERE sla_due_at IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS sentinel_incident_sla_due_idx")
    op.execute("ALTER TABLE sentinel_incident_log DROP COLUMN IF EXISTS sla_due_at")
