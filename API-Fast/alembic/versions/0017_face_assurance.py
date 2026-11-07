"""D8 face assurance: FaceEncoding.modelVersion.

Revision ID: 0017_face_assurance
Revises: 0016_notify_pdpa
Create Date: 2026-11-07

Owned by branch ``feat/phase-d-api-ratelimit-face``. Idempotent ADD COLUMN so a
legacy create_all DB can upgrade cleanly.
"""
from __future__ import annotations

from alembic import op

revision = "0017_face_assurance"
down_revision = "0016_notify_pdpa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE face_encoding
        ADD COLUMN IF NOT EXISTS "modelVersion" VARCHAR(64)
        """
    )
    op.execute(
        """
        UPDATE face_encoding
        SET "modelVersion" = 'buffalo_l'
        WHERE "modelVersion" IS NULL
        """
    )


def downgrade() -> None:
    op.execute('ALTER TABLE face_encoding DROP COLUMN IF EXISTS "modelVersion"')
