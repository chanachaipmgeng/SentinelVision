"""Enterprise shift tracking columns and audit/outbox indexes."""

from alembic import op

revision = "0003_enterprise_shifts_and_indexes"
down_revision = "0002_schema_migrate"
branch_labels = None
depends_on = None

STATEMENTS = [
    "ALTER TABLE employee_timestamp ADD COLUMN IF NOT EXISTS is_late BOOLEAN DEFAULT FALSE",
    "ALTER TABLE employee_timestamp ADD COLUMN IF NOT EXISTS late_minutes INTEGER DEFAULT 0",
    "ALTER TABLE employee_timestamp ADD COLUMN IF NOT EXISTS overtime_minutes INTEGER DEFAULT 0",
    "ALTER TABLE employee_timestamp ADD COLUMN IF NOT EXISTS shift_name VARCHAR(100)",
    "ALTER TABLE member ADD COLUMN IF NOT EXISTS biometric_consent_at TIMESTAMPTZ",
    'CREATE INDEX IF NOT EXISTS audit_log_company_occurred_idx ON audit_log ("companyId", "occurredAt" DESC)',
    'CREATE INDEX IF NOT EXISTS notification_outbox_status_created_idx ON notification_outbox ("status", "createdAt")',
]


def upgrade() -> None:
    for stmt in STATEMENTS:
        op.execute(stmt)


def downgrade() -> None:
    pass
