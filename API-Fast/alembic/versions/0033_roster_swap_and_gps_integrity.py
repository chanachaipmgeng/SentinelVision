"""BL-10 / BL-11: Shift roster entries, shift swap requests, and anti-mock GPS / Wi-Fi integrity columns.

Revision ID: 0033_roster_swap_and_gps_integrity
Revises: 0032_leave_policy_and_ot_engine
Create Date: 2026-11-15
"""
from __future__ import annotations

from alembic import op

revision = "0033_roster_swap_and_gps_integrity"
down_revision = "0032_leave_policy_and_ot_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS shift_roster_entry (
            roster_id UUID PRIMARY KEY,
            "companyId" UUID NOT NULL REFERENCES company("companyId") ON DELETE CASCADE,
            "company_employeeId" UUID NOT NULL REFERENCES company_employee("company_employeeId") ON DELETE CASCADE,
            work_date DATE NOT NULL,
            shift_id UUID REFERENCES work_shift("shiftId") ON DELETE SET NULL,
            is_day_off BOOLEAN NOT NULL DEFAULT false,
            is_flexible BOOLEAN NOT NULL DEFAULT false,
            note TEXT,
            "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
            "updatedAt" TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uq_shift_roster_company_emp_date
            ON shift_roster_entry ("companyId", "company_employeeId", work_date);

        CREATE TABLE IF NOT EXISTS shift_swap_request (
            swap_id UUID PRIMARY KEY,
            "companyId" UUID NOT NULL REFERENCES company("companyId") ON DELETE CASCADE,
            requester_employee_id UUID NOT NULL REFERENCES company_employee("company_employeeId") ON DELETE CASCADE,
            target_employee_id UUID NOT NULL REFERENCES company_employee("company_employeeId") ON DELETE CASCADE,
            work_date DATE NOT NULL,
            requester_shift_id UUID,
            target_shift_id UUID,
            reason TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
            "approvedBy" UUID,
            "approvedAt" TIMESTAMPTZ,
            "rejectReason" VARCHAR,
            "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
            "updatedAt" TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS shift_swap_company_status_idx
            ON shift_swap_request ("companyId", status);

        ALTER TABLE employee_timestamp
            ADD COLUMN IF NOT EXISTS gps_accuracy DOUBLE PRECISION,
            ADD COLUMN IF NOT EXISTS is_mock_gps BOOLEAN NOT NULL DEFAULT false,
            ADD COLUMN IF NOT EXISTS gps_integrity_flag VARCHAR(64),
            ADD COLUMN IF NOT EXISTS wifi_ssid VARCHAR(128),
            ADD COLUMN IF NOT EXISTS wifi_bssid VARCHAR(64);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE employee_timestamp
            DROP COLUMN IF EXISTS wifi_bssid,
            DROP COLUMN IF EXISTS wifi_ssid,
            DROP COLUMN IF EXISTS gps_integrity_flag,
            DROP COLUMN IF EXISTS is_mock_gps,
            DROP COLUMN IF EXISTS gps_accuracy;
        DROP TABLE IF EXISTS shift_swap_request;
        DROP TABLE IF EXISTS shift_roster_entry;
        """
    )