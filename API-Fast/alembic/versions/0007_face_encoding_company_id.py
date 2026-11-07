"""A6 tenant isolation: face_encoding.companyId (backfilled from company_employee) + index.

Revision ID: 0007_face_encoding_company_id
Revises: 0006_sentinel_vision_core
Create Date: 2026-11-07
"""
from alembic import op

revision = "0007_face_encoding_company_id"
down_revision = "0006_sentinel_vision_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE face_encoding
        ADD COLUMN IF NOT EXISTS "companyId" UUID REFERENCES company("companyId")
        """
    )
    # Backfill: the member's oldest active employment owns the legacy encoding.
    # Members without any active company_employee row keep NULL (authz then falls
    # back to the member→company check in security/deps.py).
    op.execute(
        """
        UPDATE face_encoding fe
        SET "companyId" = (
            SELECT ce."companyId"
            FROM company_employee ce
            WHERE ce."memberId" = fe."memberId" AND ce.deleted_at IS NULL
            ORDER BY ce."createdAt" NULLS LAST, ce."company_employeeId"
            LIMIT 1
        )
        WHERE fe."companyId" IS NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS face_encoding_company_member_idx
        ON face_encoding ("companyId", "memberId")
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS face_encoding_company_member_idx")
    op.execute('ALTER TABLE face_encoding DROP COLUMN IF EXISTS "companyId"')
