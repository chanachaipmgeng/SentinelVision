"""B7: import_job hand-off columns for the background worker.

Revision ID: 0009_import_job_worker
Revises: 0008_revocation_kiosk_pairing
Create Date: 2026-11-07
"""
from alembic import op

revision = "0009_import_job_worker"
down_revision = "0008_revocation_kiosk_pairing"
branch_labels = None
depends_on = None

_COLUMNS = (
    '"requestedBy" UUID',
    '"fileName" VARCHAR',
    '"photosFileName" VARCHAR',
    '"payloadDir" VARCHAR',
    '"progress" JSONB',
    '"attempts" INTEGER NOT NULL DEFAULT 0',
    '"lockedBy" VARCHAR',
    '"startedAt" TIMESTAMPTZ',
    '"heartbeatAt" TIMESTAMPTZ',
)


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS import_job (
            id UUID PRIMARY KEY,
            "companyId" UUID NOT NULL,
            status VARCHAR NOT NULL DEFAULT 'pending',
            result JSONB,
            error VARCHAR,
            "createdAt" TIMESTAMPTZ DEFAULT now(),
            "finishedAt" TIMESTAMPTZ
        )
        """
    )
    for col in _COLUMNS:
        op.execute(f"ALTER TABLE import_job ADD COLUMN IF NOT EXISTS {col}")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS import_job_status_created_idx
        ON import_job (status, "createdAt")
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS import_job_status_created_idx")
    for col in _COLUMNS:
        name = col.split(" ", 1)[0]
        op.execute(f"ALTER TABLE import_job DROP COLUMN IF EXISTS {name}")
