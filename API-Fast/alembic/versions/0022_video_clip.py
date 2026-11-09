"""Phase 4B: video_clip table for event clips + continuous refs.

Revision ID: 0022_video_clip
Revises: 0021_camera_analysis
Create Date: 2026-11-09
"""
from __future__ import annotations

from alembic import op

revision = "0022_video_clip"
down_revision = "0021_camera_analysis"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS video_clip (
            "clipId" UUID PRIMARY KEY,
            "companyId" UUID NOT NULL REFERENCES company("companyId") ON DELETE CASCADE,
            "cameraId" UUID NOT NULL REFERENCES camera("cameraId") ON DELETE CASCADE,
            "incidentId" UUID REFERENCES sentinel_incident_log("incidentId") ON DELETE SET NULL,
            started_at TIMESTAMPTZ NOT NULL,
            ended_at TIMESTAMPTZ NOT NULL,
            storage_key VARCHAR(512) NOT NULL,
            duration_ms BIGINT NOT NULL DEFAULT 0,
            kind VARCHAR(32) NOT NULL DEFAULT 'event',
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
        """
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS video_clip_company_started_idx '
        'ON video_clip ("companyId", started_at)'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS video_clip_company_camera_idx '
        'ON video_clip ("companyId", "cameraId")'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS video_clip_company_incident_idx '
        'ON video_clip ("companyId", "incidentId")'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS video_clip_company_kind_idx '
        'ON video_clip ("companyId", kind)'
    )
    op.execute(
        'CREATE UNIQUE INDEX IF NOT EXISTS video_clip_storage_key_uidx '
        'ON video_clip ("companyId", storage_key)'
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS video_clip")
