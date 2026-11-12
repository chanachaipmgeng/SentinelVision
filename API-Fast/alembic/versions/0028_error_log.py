"""System-admin error_log for API + client HTTP failures.

Revision ID: 0028_error_log
Revises: 0027_people_count
Create Date: 2026-11-12
"""
from __future__ import annotations

from alembic import op

revision = "0028_error_log"
down_revision = "0027_people_count"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS error_log (
            id UUID PRIMARY KEY,
            "occurredAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
            "lastSeenAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
            "hitCount" INTEGER NOT NULL DEFAULT 1,
            source VARCHAR(16) NOT NULL,
            "statusCode" INTEGER NOT NULL,
            method VARCHAR(16),
            path VARCHAR(500),
            "errorCode" VARCHAR(64),
            message TEXT NOT NULL,
            "exceptionType" VARCHAR(128),
            stack TEXT,
            "requestId" VARCHAR(64),
            "traceId" VARCHAR(64),
            "companyId" UUID,
            "actorMemberId" UUID,
            "pageUrl" VARCHAR(1000),
            "userAgent" TEXT,
            ip VARCHAR(64),
            fingerprint VARCHAR(64) NOT NULL,
            detail JSONB,
            "resolvedAt" TIMESTAMPTZ,
            "resolvedBy" UUID
        )
        """
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS error_log_occurred_idx '
        'ON error_log ("occurredAt" DESC)'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS error_log_fingerprint_seen_idx '
        'ON error_log (fingerprint, "lastSeenAt" DESC)'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS error_log_source_status_idx '
        'ON error_log (source, "statusCode")'
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS error_log_source_status_idx")
    op.execute("DROP INDEX IF EXISTS error_log_fingerprint_seen_idx")
    op.execute("DROP INDEX IF EXISTS error_log_occurred_idx")
    op.execute("DROP TABLE IF EXISTS error_log")
