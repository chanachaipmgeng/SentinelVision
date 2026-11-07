"""Phase 3: Multi-shift, leave requests, and company holidays."""
from alembic import op

revision = "0004_shifts_leaves_holidays"
down_revision = "0003_enterprise_shift_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE company_employee ADD COLUMN IF NOT EXISTS shift_id UUID")
    op.execute("ALTER TABLE department ADD COLUMN IF NOT EXISTS shift_id UUID")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS work_shift (
            "shiftId" UUID PRIMARY KEY,
            "companyId" UUID NOT NULL REFERENCES company("companyId") ON DELETE CASCADE,
            name VARCHAR(100) NOT NULL,
            start_time VARCHAR(10) NOT NULL DEFAULT '09:00',
            end_time VARCHAR(10) NOT NULL DEFAULT '18:00',
            grace_minutes INTEGER NOT NULL DEFAULT 15,
            is_cross_midnight BOOLEAN NOT NULL DEFAULT FALSE,
            is_default BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ,
            deleted_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS company_holiday (
            "holidayId" UUID PRIMARY KEY,
            "companyId" UUID NOT NULL REFERENCES company("companyId") ON DELETE CASCADE,
            holiday_date DATE NOT NULL,
            name VARCHAR(150) NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now(),
            deleted_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS leave_request (
            "leaveId" UUID PRIMARY KEY,
            "companyId" UUID NOT NULL REFERENCES company("companyId") ON DELETE CASCADE,
            "company_employeeId" UUID NOT NULL REFERENCES company_employee("company_employeeId") ON DELETE CASCADE,
            leave_type VARCHAR(30) NOT NULL DEFAULT 'ANNUAL',
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            reason TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
            approved_by UUID,
            approved_at TIMESTAMPTZ,
            reject_reason VARCHAR,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS work_shift_company_idx
        ON work_shift ("companyId")
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS company_holiday_company_date_idx
        ON company_holiday ("companyId", holiday_date)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS leave_request_company_dates_idx
        ON leave_request ("companyId", start_date, end_date, status)
        """
    )


def downgrade() -> None:
    pass
