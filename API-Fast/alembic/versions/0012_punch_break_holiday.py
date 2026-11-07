"""C3+C6: BREAK_OUT/BREAK_IN punch types + holiday import source column.

Revision ID: 0012_punch_break_holiday
Revises: 0011_attendance_daily_shift_rules
Create Date: 2026-11-07

Owned by branch ``phase-c/punch-holidays``.
"""
from __future__ import annotations

from alembic import op

revision = "0012_punch_break_holiday"
down_revision = "0011_attendance_daily_shift_rules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Native PG enum — ADD VALUE is not transactional on some versions; guard duplicates.
    op.execute(
        """
        DO $$ BEGIN
          ALTER TYPE timestamptype ADD VALUE 'BREAK_OUT';
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
          ALTER TYPE timestamptype ADD VALUE 'BREAK_IN';
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        ALTER TABLE company_holiday
          ADD COLUMN IF NOT EXISTS source VARCHAR(30) NOT NULL DEFAULT 'MANUAL'
        """
    )


def downgrade() -> None:
    # Enum values cannot be removed safely on PostgreSQL; only drop the source column.
    op.execute("ALTER TABLE company_holiday DROP COLUMN IF EXISTS source")
