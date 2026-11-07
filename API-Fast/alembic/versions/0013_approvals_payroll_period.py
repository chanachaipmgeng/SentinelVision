"""C4+C5: leave balance, regularization, OT approval, payroll period lock.

Revision ID: 0013_approvals_payroll_period
Revises: 0012_punch_break_holiday
Create Date: 2026-11-07

Idempotent DDL (IF NOT EXISTS) so a legacy ``create_all`` DB stamped at 0008 can
upgrade through this revision without DuplicateTable errors.
"""
from __future__ import annotations

from alembic import op

revision = "0013_approvals_payroll_period"
down_revision = "0012_punch_break_holiday"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS leave_balance (
            "balanceId" UUID PRIMARY KEY,
            "companyId" UUID NOT NULL REFERENCES company("companyId") ON DELETE CASCADE,
            "company_employeeId" UUID NOT NULL REFERENCES company_employee("company_employeeId") ON DELETE CASCADE,
            "leaveType" VARCHAR(30) NOT NULL DEFAULT 'ANNUAL',
            year INTEGER NOT NULL,
            "entitledDays" FLOAT NOT NULL DEFAULT 0,
            "usedDays" FLOAT NOT NULL DEFAULT 0,
            "createdAt" TIMESTAMPTZ DEFAULT now(),
            "updatedAt" TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS leave_balance_company_emp_idx
        ON leave_balance ("companyId", "company_employeeId")
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_leave_balance_emp_type_year
        ON leave_balance ("companyId", "company_employeeId", "leaveType", year)
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS regularization_request (
            "requestId" UUID PRIMARY KEY,
            "companyId" UUID NOT NULL REFERENCES company("companyId") ON DELETE CASCADE,
            "company_employeeId" UUID NOT NULL REFERENCES company_employee("company_employeeId") ON DELETE CASCADE,
            "workDate" DATE NOT NULL,
            "requestedTimestamp" TIMESTAMPTZ NOT NULL,
            "requestedType" INTEGER NOT NULL DEFAULT 1,
            reason TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
            "originalTimestampId" UUID,
            "approvedBy" UUID,
            "approvedAt" TIMESTAMPTZ,
            "rejectReason" VARCHAR,
            "createdAt" TIMESTAMPTZ DEFAULT now(),
            "updatedAt" TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS regularization_company_status_idx
        ON regularization_request ("companyId", status)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS regularization_company_emp_date_idx
        ON regularization_request ("companyId", "company_employeeId", "workDate")
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ot_approval_request (
            "requestId" UUID PRIMARY KEY,
            "companyId" UUID NOT NULL REFERENCES company("companyId") ON DELETE CASCADE,
            "company_employeeId" UUID NOT NULL REFERENCES company_employee("company_employeeId") ON DELETE CASCADE,
            "workDate" DATE NOT NULL,
            "otMinutes" INTEGER NOT NULL DEFAULT 0,
            "thresholdMinutes" INTEGER,
            reason TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
            "requiresApproval" BOOLEAN NOT NULL DEFAULT true,
            "approvedBy" UUID,
            "approvedAt" TIMESTAMPTZ,
            "rejectReason" VARCHAR,
            "createdAt" TIMESTAMPTZ DEFAULT now(),
            "updatedAt" TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ot_approval_company_status_idx
        ON ot_approval_request ("companyId", status)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ot_approval_company_emp_date_idx
        ON ot_approval_request ("companyId", "company_employeeId", "workDate")
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS payroll_period (
            "periodId" UUID PRIMARY KEY,
            "companyId" UUID NOT NULL REFERENCES company("companyId") ON DELETE CASCADE,
            name VARCHAR(120),
            "startDate" DATE NOT NULL,
            "endDate" DATE NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
            "lockedAt" TIMESTAMPTZ,
            "lockedBy" UUID,
            "createdAt" TIMESTAMPTZ DEFAULT now(),
            "updatedAt" TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_payroll_period_range
        ON payroll_period ("companyId", "startDate", "endDate")
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS payroll_period_company_status_idx
        ON payroll_period ("companyId", status)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS payroll_period_company_status_idx")
    # Constraint form may exist if an earlier attempt used ADD CONSTRAINT.
    op.execute("ALTER TABLE payroll_period DROP CONSTRAINT IF EXISTS uq_payroll_period_range")
    op.execute("DROP INDEX IF EXISTS uq_payroll_period_range")
    op.execute("DROP TABLE IF EXISTS payroll_period")

    op.execute("DROP INDEX IF EXISTS ot_approval_company_emp_date_idx")
    op.execute("DROP INDEX IF EXISTS ot_approval_company_status_idx")
    op.execute("DROP TABLE IF EXISTS ot_approval_request")

    op.execute("DROP INDEX IF EXISTS regularization_company_emp_date_idx")
    op.execute("DROP INDEX IF EXISTS regularization_company_status_idx")
    op.execute("DROP TABLE IF EXISTS regularization_request")

    op.execute("ALTER TABLE leave_balance DROP CONSTRAINT IF EXISTS uq_leave_balance_emp_type_year")
    op.execute("DROP INDEX IF EXISTS uq_leave_balance_emp_type_year")
    op.execute("DROP INDEX IF EXISTS leave_balance_company_emp_idx")
    op.execute("DROP TABLE IF EXISTS leave_balance")
