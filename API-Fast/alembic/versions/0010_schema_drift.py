"""B1: capture drift between the legacy startup DDL and the models.

Revision ID: 0010_schema_drift
Revises: 0009_import_job_worker
Create Date: 2026-11-07

Databases created by the old ``create_all`` + ``utils/schema_migrate.py`` startup path differ from
the ORM models in two ways:

* columns that ``schema_migrate`` bolted on with ``ADD COLUMN IF NOT EXISTS`` are nullable while the
  models declare them ``NOT NULL`` (backfilled to their defaults here, then tightened);
* objects that only the startup code created (face_encoding HNSW index, company_employee unique
  indexes, ``employee_timestamp.approved_by`` FK) are now declared on the models.

Everything is idempotent, so running it on a database that already matches the models is a no-op.
After this revision ``alembic check`` must report no drift.
"""
from __future__ import annotations

from alembic import op

revision = "0010_schema_drift"
down_revision = "0009_import_job_worker"
branch_labels = None
depends_on = None

# (table, column, SQL default used for the backfill)
NOT_NULL_COLUMNS = (
    ("member", "must_change_password", "false"),
    ("member", "failed_login_count", "0"),
    ("member", "totp_enabled", "false"),
    ("employee_timestamp", "approval_status", "'NONE'"),
    ("employee_timestamp", "is_late", "false"),
    ("employee_timestamp", "late_minutes", "0"),
    ("employee_timestamp", "overtime_minutes", "0"),
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    for table, column, default in NOT_NULL_COLUMNS:
        op.execute(f"UPDATE {table} SET {column} = {default} WHERE {column} IS NULL")
        op.execute(f"ALTER TABLE {table} ALTER COLUMN {column} SET DEFAULT {default}")
        op.execute(f"ALTER TABLE {table} ALTER COLUMN {column} SET NOT NULL")

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS face_encoding_embedding_hnsw_idx
        ON face_encoding USING hnsw (embedding vector_cosine_ops)
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_company_employee_member_company
        ON company_employee ("memberId", "companyId")
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_company_employee_code
        ON company_employee ("companyId", "employeeId")
        WHERE "employeeId" IS NOT NULL AND "employeeId" <> ''
        """
    )
    op.execute(
        """
        DO $$ BEGIN
          ALTER TABLE employee_timestamp
            ADD CONSTRAINT employee_timestamp_approved_by_fkey
            FOREIGN KEY (approved_by) REFERENCES member("memberId");
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE employee_timestamp DROP CONSTRAINT IF EXISTS employee_timestamp_approved_by_fkey")
    op.execute("DROP INDEX IF EXISTS uq_company_employee_code")
    op.execute("DROP INDEX IF EXISTS uq_company_employee_member_company")
    op.execute("DROP INDEX IF EXISTS face_encoding_embedding_hnsw_idx")
    for table, column, _default in NOT_NULL_COLUMNS:
        op.execute(f"ALTER TABLE {table} ALTER COLUMN {column} DROP NOT NULL")
