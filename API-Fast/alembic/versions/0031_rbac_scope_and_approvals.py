"""BL-06 / BL-07: RBAC branch/location scoping, SECURITY_GUARD & EMPLOYEE roles, multi-level approval & delegation.

Revision ID: 0031_rbac_scope_and_approvals
Revises: 0030_person_presence
Create Date: 2026-11-15
"""
from __future__ import annotations

from alembic import op

revision = "0031_rbac_scope_and_approvals"
down_revision = "0030_person_presence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO rbac_role (code, description) VALUES
            ('SECURITY_GUARD', 'Security guard (Access / Watchlist / CCTV)'),
            ('EMPLOYEE', 'Standard employee self-service')
        ON CONFLICT (code) DO NOTHING
        """
    )

    op.execute(
        """
        INSERT INTO rbac_role_permission (role_code, permission_code)
        SELECT v.role_code, v.permission_code
        FROM (VALUES
            ('SECURITY_GUARD', 'company.read'),
            ('SECURITY_GUARD', 'sentinel.manage'),
            ('SECURITY_GUARD', 'cameras.read'),
            ('SECURITY_GUARD', 'attendance.read'),
            ('EMPLOYEE', 'company.read')
        ) AS v(role_code, permission_code)
        WHERE EXISTS (SELECT 1 FROM rbac_permission p WHERE p.code = v.permission_code)
        ON CONFLICT DO NOTHING
        """
    )

    op.execute(
        """
        ALTER TABLE member_role_assignment
            ADD COLUMN IF NOT EXISTS location_id UUID REFERENCES company_location("locationId") ON DELETE SET NULL;
        ALTER TABLE company_employee
            ADD COLUMN IF NOT EXISTS location_id UUID REFERENCES company_location("locationId") ON DELETE SET NULL;
        """
    )

    op.execute(
        """
        ALTER TABLE leave_request
            ADD COLUMN IF NOT EXISTS approval_level INTEGER NOT NULL DEFAULT 1,
            ADD COLUMN IF NOT EXISTS max_approval_level INTEGER NOT NULL DEFAULT 1,
            ADD COLUMN IF NOT EXISTS approval_history JSONB NOT NULL DEFAULT '[]'::jsonb;

        ALTER TABLE regularization_request
            ADD COLUMN IF NOT EXISTS approval_level INTEGER NOT NULL DEFAULT 1,
            ADD COLUMN IF NOT EXISTS max_approval_level INTEGER NOT NULL DEFAULT 1,
            ADD COLUMN IF NOT EXISTS approval_history JSONB NOT NULL DEFAULT '[]'::jsonb;

        ALTER TABLE ot_approval_request
            ADD COLUMN IF NOT EXISTS approval_level INTEGER NOT NULL DEFAULT 1,
            ADD COLUMN IF NOT EXISTS max_approval_level INTEGER NOT NULL DEFAULT 1,
            ADD COLUMN IF NOT EXISTS approval_history JSONB NOT NULL DEFAULT '[]'::jsonb;
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS approval_policy (
            policy_id UUID PRIMARY KEY,
            "companyId" UUID NOT NULL REFERENCES company("companyId") ON DELETE CASCADE,
            request_type VARCHAR(30) NOT NULL DEFAULT 'ALL',
            levels JSONB NOT NULL DEFAULT '[]'::jsonb,
            is_active BOOLEAN NOT NULL DEFAULT true,
            "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
            "updatedAt" TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uq_approval_policy_company_type
            ON approval_policy ("companyId", request_type);

        CREATE TABLE IF NOT EXISTS approval_delegation (
            delegation_id UUID PRIMARY KEY,
            "companyId" UUID NOT NULL REFERENCES company("companyId") ON DELETE CASCADE,
            delegator_member_id UUID NOT NULL REFERENCES member("memberId") ON DELETE CASCADE,
            delegate_member_id UUID NOT NULL REFERENCES member("memberId") ON DELETE CASCADE,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            reason TEXT,
            is_active BOOLEAN NOT NULL DEFAULT true,
            "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
            "updatedAt" TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS approval_delegation_company_delegate_idx
            ON approval_delegation ("companyId", delegate_member_id, is_active);
        CREATE INDEX IF NOT EXISTS approval_delegation_company_delegator_idx
            ON approval_delegation ("companyId", delegator_member_id, is_active);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS approval_delegation")
    op.execute("DROP TABLE IF EXISTS approval_policy")
    op.execute(
        """
        ALTER TABLE ot_approval_request
            DROP COLUMN IF EXISTS approval_history,
            DROP COLUMN IF EXISTS max_approval_level,
            DROP COLUMN IF EXISTS approval_level;
        ALTER TABLE regularization_request
            DROP COLUMN IF EXISTS approval_history,
            DROP COLUMN IF EXISTS max_approval_level,
            DROP COLUMN IF EXISTS approval_level;
        ALTER TABLE leave_request
            DROP COLUMN IF EXISTS approval_history,
            DROP COLUMN IF EXISTS max_approval_level,
            DROP COLUMN IF EXISTS approval_level;
        ALTER TABLE company_employee DROP COLUMN IF EXISTS location_id;
        ALTER TABLE member_role_assignment DROP COLUMN IF EXISTS location_id;
        """
    )
    op.execute("DELETE FROM rbac_role WHERE code IN ('SECURITY_GUARD', 'EMPLOYEE')")
