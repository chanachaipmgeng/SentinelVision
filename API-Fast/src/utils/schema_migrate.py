"""Ensure new columns exist on already-created tables (create_all does not ALTER)."""
from sqlalchemy import text


async def ensure_profile_and_approval_columns(connection) -> None:
    statements = [
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
    ]
    for stmt in statements:
        await connection.execute(text(stmt))
