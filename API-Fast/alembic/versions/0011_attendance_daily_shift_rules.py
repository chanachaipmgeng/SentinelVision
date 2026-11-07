"""C1+C2: attendance_daily summary table and WorkShift rule columns.

Revision ID: 0011_attendance_daily_shift_rules
Revises: 0010_schema_drift
Create Date: 2026-11-07

* ``attendance_daily`` — one row per (company, employee, Asia/Bangkok work date)
* ``work_shift`` gains rounding / break / OT-threshold columns used by shift metrics

Also widens ``alembic_version.version_num`` to VARCHAR(64) so this 33-char revision id (and
future Phase C ids) fit; the column was created as VARCHAR(32) by Alembic's default.
"""
from __future__ import annotations

from alembic import op

revision = "0011_attendance_daily_shift_rules"
down_revision = "0010_schema_drift"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # revision id is 33 chars; stock alembic_version.version_num is VARCHAR(32)
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'alembic_version'
          ) THEN
            ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(64);
          END IF;
        END $$;
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS attendance_daily (
            id UUID PRIMARY KEY,
            "companyId" UUID NOT NULL REFERENCES company("companyId") ON DELETE CASCADE,
            "employeeId" UUID NOT NULL REFERENCES company_employee("company_employeeId") ON DELETE CASCADE,
            work_date DATE NOT NULL,
            first_in TIMESTAMPTZ,
            last_out TIMESTAMPTZ,
            work_minutes INTEGER NOT NULL DEFAULT 0,
            break_minutes INTEGER NOT NULL DEFAULT 0,
            late_minutes INTEGER NOT NULL DEFAULT 0,
            ot_minutes INTEGER NOT NULL DEFAULT 0,
            status VARCHAR(20) NOT NULL DEFAULT 'ABSENT',
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS attendance_daily_company_emp_date_uidx
        ON attendance_daily ("companyId", "employeeId", work_date)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS attendance_daily_company_date_idx
        ON attendance_daily ("companyId", work_date)
        """
    )

    op.execute(
        "ALTER TABLE work_shift ADD COLUMN IF NOT EXISTS rounding_minutes INTEGER NOT NULL DEFAULT 0"
    )
    op.execute(
        "ALTER TABLE work_shift ADD COLUMN IF NOT EXISTS break_minutes INTEGER NOT NULL DEFAULT 0"
    )
    op.execute(
        "ALTER TABLE work_shift ADD COLUMN IF NOT EXISTS break_windows JSONB NOT NULL DEFAULT '[]'::jsonb"
    )
    op.execute(
        "ALTER TABLE work_shift ADD COLUMN IF NOT EXISTS ot_threshold_minutes INTEGER NOT NULL DEFAULT 0"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE work_shift DROP COLUMN IF EXISTS ot_threshold_minutes")
    op.execute("ALTER TABLE work_shift DROP COLUMN IF EXISTS break_windows")
    op.execute("ALTER TABLE work_shift DROP COLUMN IF EXISTS break_minutes")
    op.execute("ALTER TABLE work_shift DROP COLUMN IF EXISTS rounding_minutes")
    op.execute("DROP INDEX IF EXISTS attendance_daily_company_date_idx")
    op.execute("DROP INDEX IF EXISTS attendance_daily_company_emp_date_uidx")
    op.execute("DROP TABLE IF EXISTS attendance_daily")
