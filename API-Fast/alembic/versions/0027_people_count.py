"""Phase 6D: camera.ai_config JSONB + people_count_bucket.

Revision ID: 0027_people_count
Revises: 0026_incident_camera
Create Date: 2026-11-10

Owned by branch ``cursor/phase6d-people-counting-0b6b``.
"""
from __future__ import annotations

from alembic import op

revision = "0027_people_count"
down_revision = "0026_incident_camera"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE camera
        ADD COLUMN IF NOT EXISTS ai_config JSONB
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS people_count_bucket (
            "bucketId" UUID PRIMARY KEY,
            "companyId" UUID NOT NULL
                REFERENCES company("companyId") ON DELETE CASCADE,
            "cameraId" UUID NOT NULL
                REFERENCES camera("cameraId") ON DELETE CASCADE,
            bucket_start TIMESTAMPTZ NOT NULL,
            in_count INTEGER NOT NULL DEFAULT 0,
            out_count INTEGER NOT NULL DEFAULT 0,
            zone_occupancy INTEGER NOT NULL DEFAULT 0,
            crossing_count INTEGER NOT NULL DEFAULT 0,
            detections INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ,
            CONSTRAINT people_count_bucket_cam_start_uq UNIQUE ("cameraId", bucket_start)
        )
        """
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS people_count_bucket_company_start_idx '
        'ON people_count_bucket ("companyId", bucket_start)'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS people_count_bucket_camera_start_idx '
        'ON people_count_bucket ("cameraId", bucket_start)'
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS people_count_bucket_camera_start_idx")
    op.execute("DROP INDEX IF EXISTS people_count_bucket_company_start_idx")
    op.execute("DROP TABLE IF EXISTS people_count_bucket")
    op.execute("ALTER TABLE camera DROP COLUMN IF EXISTS ai_config")
