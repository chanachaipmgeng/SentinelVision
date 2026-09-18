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
        "ALTER TABLE member ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN DEFAULT FALSE",
        "ALTER TABLE member ADD COLUMN IF NOT EXISTS failed_login_count INTEGER DEFAULT 0",
        "ALTER TABLE member ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ",
        "ALTER TABLE member ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ",
        "ALTER TABLE company ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ",
        "ALTER TABLE company_employee ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ",
        "ALTER TABLE department ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ",
        "ALTER TABLE position ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ",
        "ALTER TABLE company_location ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ",
        """
        CREATE INDEX IF NOT EXISTS employee_timestamp_company_ts_idx
        ON employee_timestamp ("companyId", "timestamp")
        """,
        """
        CREATE INDEX IF NOT EXISTS employee_timestamp_emp_ts_idx
        ON employee_timestamp ("company_employeeId", "timestamp")
        """,
        """
        CREATE INDEX IF NOT EXISTS face_encoding_member_idx
        ON face_encoding ("memberId")
        """,
        """
        DO $$ BEGIN
          CREATE UNIQUE INDEX uq_company_employee_member_company
          ON company_employee ("memberId", "companyId");
        EXCEPTION WHEN duplicate_table OR unique_violation THEN NULL;
        END $$;
        """,
        """
        DO $$ BEGIN
          CREATE UNIQUE INDEX uq_company_employee_code
          ON company_employee ("companyId", "employeeId")
          WHERE "employeeId" IS NOT NULL AND "employeeId" <> '';
        EXCEPTION WHEN duplicate_table OR unique_violation THEN NULL;
        END $$;
        """,
        """
        DO $$ BEGIN
          ALTER TABLE employee_timestamp
            ADD CONSTRAINT employee_timestamp_approved_by_fkey
            FOREIGN KEY (approved_by) REFERENCES member("memberId");
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """,
    ]
    for stmt in statements:
        await connection.execute(text(stmt))
