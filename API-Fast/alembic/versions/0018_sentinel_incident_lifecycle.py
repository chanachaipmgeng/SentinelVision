"""F1 sentinel incident lifecycle + dedupe columns.

Revision ID: 0018_sentinel_incident_lifecycle
Revises: 0017_face_assurance
Create Date: 2026-11-08

Owned by branch ``feat/phase-f-router-lifecycle``. Idempotent ADD COLUMN so a
legacy create_all DB can upgrade cleanly.
"""
from __future__ import annotations

from alembic import op

revision = "0018_sentinel_incident_lifecycle"
down_revision = "0017_face_assurance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE sentinel_incident_log
        ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'OPEN'
        """
    )
    op.execute(
        """
        ALTER TABLE sentinel_incident_log
        ADD COLUMN IF NOT EXISTS assigned_to UUID
        """
    )
    op.execute(
        """
        ALTER TABLE sentinel_incident_log
        ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMPTZ
        """
    )
    op.execute(
        """
        ALTER TABLE sentinel_incident_log
        ADD COLUMN IF NOT EXISTS closed_by UUID
        """
    )
    op.execute(
        """
        ALTER TABLE sentinel_incident_log
        ADD COLUMN IF NOT EXISTS closed_at TIMESTAMPTZ
        """
    )
    op.execute(
        """
        ALTER TABLE sentinel_incident_log
        ADD COLUMN IF NOT EXISTS dedupe_key VARCHAR(180)
        """
    )
    op.execute(
        """
        UPDATE sentinel_incident_log
        SET status = 'ACKNOWLEDGED'
        WHERE acknowledged_at IS NOT NULL
          AND (status IS NULL OR status = 'OPEN')
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS sentinel_incident_dedupe_open_idx
        ON sentinel_incident_log ("companyId", dedupe_key, status, occurred_at DESC)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS sentinel_incident_dedupe_open_idx")
    op.execute("ALTER TABLE sentinel_incident_log DROP COLUMN IF EXISTS dedupe_key")
    op.execute("ALTER TABLE sentinel_incident_log DROP COLUMN IF EXISTS closed_at")
    op.execute("ALTER TABLE sentinel_incident_log DROP COLUMN IF EXISTS closed_by")
    op.execute("ALTER TABLE sentinel_incident_log DROP COLUMN IF EXISTS assigned_at")
    op.execute("ALTER TABLE sentinel_incident_log DROP COLUMN IF EXISTS assigned_to")
    op.execute("ALTER TABLE sentinel_incident_log DROP COLUMN IF EXISTS status")
