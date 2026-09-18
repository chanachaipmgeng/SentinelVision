"""Columns and indexes that create_all does not add to an existing database.

Equivalent to utils/schema_migrate.py. Stamp this revision on databases that
already ran schema_migrate: `alembic stamp 0002_schema_migrate`.
"""

from alembic import op

revision = "0002_schema_migrate"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None

STATEMENTS = [
    "ALTER TABLE member ADD COLUMN IF NOT EXISTS birth_date DATE",
    "ALTER TABLE member ADD COLUMN IF NOT EXISTS address TEXT",
    "ALTER TABLE member ADD COLUMN IF NOT EXISTS emergency_contact_name VARCHAR",
    "ALTER TABLE member ADD COLUMN IF NOT EXISTS emergency_contact_phone VARCHAR",
    "ALTER TABLE member ADD COLUMN IF NOT EXISTS attachment_urls TEXT",
    "ALTER TABLE employee_timestamp ADD COLUMN IF NOT EXISTS note TEXT",
    "ALTER TABLE employee_timestamp ADD COLUMN IF NOT EXISTS approval_status VARCHAR(20) DEFAULT 'NONE'",
    "ALTER TABLE employee_timestamp ADD COLUMN IF NOT EXISTS approved_by UUID",
    "ALTER TABLE employee_timestamp ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ",
    "ALTER TABLE employee_timestamp ADD COLUMN IF NOT EXISTS reject_reason VARCHAR",
    "ALTER TABLE member ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN DEFAULT FALSE",
    "ALTER TABLE member ADD COLUMN IF NOT EXISTS failed_login_count INTEGER DEFAULT 0",
    "ALTER TABLE member ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ",
    "ALTER TABLE member ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ",
    "ALTER TABLE company ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ",
    "ALTER TABLE company_employee ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ",
    "ALTER TABLE department ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ",
    "ALTER TABLE position ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ",
    "ALTER TABLE company_location ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ",
    'CREATE INDEX IF NOT EXISTS employee_timestamp_company_ts_idx ON employee_timestamp ("companyId", "timestamp")',
    'CREATE INDEX IF NOT EXISTS employee_timestamp_emp_ts_idx ON employee_timestamp ("company_employeeId", "timestamp")',
    'CREATE INDEX IF NOT EXISTS face_encoding_member_idx ON face_encoding ("memberId")',
]


def upgrade() -> None:
    for stmt in STATEMENTS:
        op.execute(stmt)


def downgrade() -> None:
    pass
