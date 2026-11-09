"""Phase 4A: camera analysisEnabled + lastAnalyzedAt for CCTV InsightFace worker.

Revision ID: 0021_camera_analysis
Revises: 0020_camera_cctv
Create Date: 2026-11-09
"""
from __future__ import annotations

from alembic import op

revision = "0021_camera_analysis"
down_revision = "0020_camera_cctv"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE camera
          ADD COLUMN IF NOT EXISTS analysis_enabled BOOLEAN NOT NULL DEFAULT FALSE
        """
    )
    op.execute(
        """
        ALTER TABLE camera
          ADD COLUMN IF NOT EXISTS last_analyzed_at TIMESTAMPTZ
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS camera_analysis_due_idx
          ON camera (analysis_enabled, is_active, last_analyzed_at)
          WHERE deleted_at IS NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS camera_analysis_due_idx")
    op.execute("ALTER TABLE camera DROP COLUMN IF EXISTS last_analyzed_at")
    op.execute("ALTER TABLE camera DROP COLUMN IF EXISTS analysis_enabled")
