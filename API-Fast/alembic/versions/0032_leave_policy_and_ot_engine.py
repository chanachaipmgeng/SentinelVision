"""BL-08: Leave Policy (seniority, carry-over, hourly/half-day, medical cert) and OT Rate Engine (1.0x/1.5x/2.0x/3.0x).

Revision ID: 0032_leave_policy_and_ot_engine
Revises: 0031_rbac_scope_and_approvals
Create Date: 2026-11-15
"""
from __future__ import annotations

from alembic import op

revision = "0032_leave_policy_and_ot_engine"
down_revision = "0031_rbac_scope_and_approvals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE leave_request
            ADD COLUMN IF NOT EXISTS leave_unit VARCHAR(20) NOT NULL DEFAULT 'FULL_DAY',
            ADD COLUMN IF NOT EXISTS leave_hours DOUBLE PRECISION,
            ADD COLUMN IF NOT EXISTS attachment_url VARCHAR(500);

        CREATE TABLE IF NOT EXISTS leave_policy (
            policy_id UUID PRIMARY KEY,
            "companyId" UUID NOT NULL REFERENCES company("companyId") ON DELETE CASCADE,
            leave_type VARCHAR(30) NOT NULL,
            display_name VARCHAR(100) NOT NULL DEFAULT '',
            annual_quota_days DOUBLE PRECISION NOT NULL DEFAULT 6.0,
            seniority_tiers JSONB NOT NULL DEFAULT '[]'::jsonb,
            allow_carry_over BOOLEAN NOT NULL DEFAULT false,
            max_carry_over_days DOUBLE PRECISION NOT NULL DEFAULT 0,
            allow_half_day BOOLEAN NOT NULL DEFAULT true,
            allow_hourly BOOLEAN NOT NULL DEFAULT true,
            require_medical_cert BOOLEAN NOT NULL DEFAULT false,
            medical_cert_min_days DOUBLE PRECISION NOT NULL DEFAULT 3,
            is_active BOOLEAN NOT NULL DEFAULT true,
            "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
            "updatedAt" TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uq_leave_policy_company_type
            ON leave_policy ("companyId", leave_type);

        CREATE TABLE IF NOT EXISTS ot_rate_policy (
            policy_id UUID PRIMARY KEY,
            "companyId" UUID NOT NULL UNIQUE REFERENCES company("companyId") ON DELETE CASCADE,
            normal_ot_rate DOUBLE PRECISION NOT NULL DEFAULT 1.0,
            workday_ot_rate DOUBLE PRECISION NOT NULL DEFAULT 1.5,
            holiday_work_rate DOUBLE PRECISION NOT NULL DEFAULT 2.0,
            holiday_ot_rate DOUBLE PRECISION NOT NULL DEFAULT 3.0,
            daily_work_minutes INTEGER NOT NULL DEFAULT 480,
            rounding_minutes INTEGER NOT NULL DEFAULT 15,
            "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
            "updatedAt" TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ot_rate_policy")
    op.execute("DROP TABLE IF EXISTS leave_policy")
    op.execute(
        """
        ALTER TABLE leave_request
            DROP COLUMN IF EXISTS attachment_url,
            DROP COLUMN IF EXISTS leave_hours,
            DROP COLUMN IF EXISTS leave_unit;
        """
    )