"""Phase 6C: cameraId on incidents + analytics support indexes.

Revision ID: 0026_incident_camera
Revises: 0025_company_api_key
Create Date: 2026-11-10

Owned by branch ``cursor/phase6c-heatmap-analytics-ac3c``.
"""
from __future__ import annotations

from alembic import op

revision = "0026_incident_camera"
down_revision = "0025_company_api_key"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE sentinel_incident_log
        ADD COLUMN IF NOT EXISTS camera_id UUID
            REFERENCES camera("cameraId") ON DELETE SET NULL
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS sentinel_incident_company_camera_idx "
        'ON sentinel_incident_log ("companyId", camera_id, occurred_at DESC)'
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS sentinel_incident_company_hour_idx "
        'ON sentinel_incident_log ("companyId", occurred_at)'
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS sentinel_incident_company_hour_idx")
    op.execute("DROP INDEX IF EXISTS sentinel_incident_company_camera_idx")
    op.execute(
        "ALTER TABLE sentinel_incident_log DROP COLUMN IF EXISTS camera_id"
    )
