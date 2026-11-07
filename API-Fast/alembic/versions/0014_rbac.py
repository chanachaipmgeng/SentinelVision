"""D1 RBAC: roles, permissions, member_role_assignment + seed + ADMIN_COMPANY backfill.

Revision ID: 0014_rbac
Revises: 0013_approvals_payroll_period
Create Date: 2026-11-07

Idempotent DDL (IF NOT EXISTS) so a legacy create_all DB stamped earlier can upgrade.
"""
from __future__ import annotations

from alembic import op

revision = "0014_rbac"
down_revision = "0013_approvals_payroll_period"
branch_labels = None
depends_on = None

_PERMISSIONS = [
    ("company.read", "View company profile"),
    ("company.settings", "Edit company settings"),
    ("employees.read", "List / view employees"),
    ("employees.write", "Create / update employees"),
    ("departments.read", "List / view departments"),
    ("departments.write", "Create / update departments"),
    ("positions.read", "List / view positions"),
    ("positions.write", "Create / update positions"),
    ("attendance.read", "View attendance / punches"),
    ("attendance.write", "Create / adjust punches"),
    ("attendance.approve", "Approve / reject punches"),
    ("attendance.export", "Export attendance reports"),
    ("hr.shifts", "Manage work shifts"),
    ("hr.leaves", "Manage leave requests"),
    ("hr.holidays", "Manage company holidays"),
    ("hr.approve", "Approve leave / OT / regularization"),
    ("devices.manage", "Manage kiosk devices"),
    ("notifications.manage", "Manage notification settings / outbox"),
    ("audit.read", "View audit log"),
    ("payroll.export", "Export payroll / lock periods"),
    ("sentinel.manage", "Manage SentinelVision modules"),
    ("system.admin", "Platform system administration"),
]

_ROLES = [
    ("SYSTEM_ADMIN", "Platform system administrator"),
    ("HR_ADMIN", "Company HR administrator (maps from ADMIN_COMPANY)"),
    ("MANAGER", "Department manager"),
    ("APPROVER", "Attendance / leave approver"),
    ("AUDITOR", "Read-only auditor"),
    ("DEVICE_OPERATOR", "Kiosk / device operator"),
]

# role → permission codes (must match rbac_service.ROLE_PERMISSIONS)
_ROLE_PERMS: dict[str, tuple[str, ...]] = {
    "SYSTEM_ADMIN": tuple(p[0] for p in _PERMISSIONS),
    "HR_ADMIN": tuple(p[0] for p in _PERMISSIONS if p[0] != "system.admin"),
    "MANAGER": (
        "company.read",
        "employees.read",
        "departments.read",
        "attendance.read",
        "attendance.approve",
        "hr.leaves",
        "hr.approve",
    ),
    "APPROVER": (
        "company.read",
        "attendance.read",
        "attendance.approve",
        "hr.approve",
    ),
    "AUDITOR": (
        "company.read",
        "employees.read",
        "departments.read",
        "positions.read",
        "attendance.read",
        "attendance.export",
        "hr.shifts",
        "hr.leaves",
        "hr.holidays",
        "audit.read",
        "payroll.export",
    ),
    "DEVICE_OPERATOR": (
        "company.read",
        "devices.manage",
        "attendance.read",
    ),
}


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS rbac_permission (
            code VARCHAR(64) PRIMARY KEY,
            description TEXT,
            "createdAt" TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS rbac_role (
            code VARCHAR(32) PRIMARY KEY,
            description TEXT,
            "createdAt" TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS rbac_role_permission (
            role_code VARCHAR(32) NOT NULL REFERENCES rbac_role(code) ON DELETE CASCADE,
            permission_code VARCHAR(64) NOT NULL REFERENCES rbac_permission(code) ON DELETE CASCADE,
            PRIMARY KEY (role_code, permission_code)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS member_role_assignment (
            assignment_id UUID PRIMARY KEY,
            "memberId" UUID NOT NULL REFERENCES member("memberId") ON DELETE CASCADE,
            "companyId" UUID REFERENCES company("companyId") ON DELETE CASCADE,
            role_code VARCHAR(32) NOT NULL REFERENCES rbac_role(code) ON DELETE CASCADE,
            "departmentId" UUID REFERENCES department("departmentId") ON DELETE CASCADE,
            "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
            "updatedAt" TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'uq_member_role_scope'
            ) THEN
                ALTER TABLE member_role_assignment
                ADD CONSTRAINT uq_member_role_scope
                UNIQUE ("memberId", "companyId", role_code, "departmentId");
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS member_role_member_company_idx
        ON member_role_assignment ("memberId", "companyId")
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS member_role_company_role_idx
        ON member_role_assignment ("companyId", role_code)
        """
    )

    for code, desc in _PERMISSIONS:
        op.execute(
            f"""
            INSERT INTO rbac_permission (code, description)
            VALUES ('{code}', '{desc}')
            ON CONFLICT (code) DO NOTHING
            """
        )
    for code, desc in _ROLES:
        op.execute(
            f"""
            INSERT INTO rbac_role (code, description)
            VALUES ('{code}', '{desc}')
            ON CONFLICT (code) DO NOTHING
            """
        )
    for role, perms in _ROLE_PERMS.items():
        for perm in perms:
            op.execute(
                f"""
                INSERT INTO rbac_role_permission (role_code, permission_code)
                VALUES ('{role}', '{perm}')
                ON CONFLICT DO NOTHING
                """
            )

    # Map existing company admins → HR_ADMIN (company-wide, no department scope).
    op.execute(
        """
        INSERT INTO member_role_assignment (
            assignment_id, "memberId", "companyId", role_code, "departmentId", "createdAt"
        )
        SELECT
            gen_random_uuid(),
            ce."memberId",
            ce."companyId",
            'HR_ADMIN',
            NULL,
            now()
        FROM company_employee ce
        WHERE ce.deleted_at IS NULL
          AND ce."companyRoleType"::text = 'ADMIN_COMPANY'
          AND NOT EXISTS (
            SELECT 1 FROM member_role_assignment mra
            WHERE mra."memberId" = ce."memberId"
              AND mra."companyId" = ce."companyId"
              AND mra.role_code = 'HR_ADMIN'
              AND mra."departmentId" IS NULL
          )
        """
    )

    # Map platform system admins → SYSTEM_ADMIN (no company scope).
    op.execute(
        """
        INSERT INTO member_role_assignment (
            assignment_id, "memberId", "companyId", role_code, "departmentId", "createdAt"
        )
        SELECT
            gen_random_uuid(),
            m."memberId",
            NULL,
            'SYSTEM_ADMIN',
            NULL,
            now()
        FROM member m
        WHERE m.deleted_at IS NULL
          AND m.role::text = 'ADMIN_SYSTEM'
          AND NOT EXISTS (
            SELECT 1 FROM member_role_assignment mra
            WHERE mra."memberId" = m."memberId"
              AND mra.role_code = 'SYSTEM_ADMIN'
              AND mra."companyId" IS NULL
          )
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS member_role_company_role_idx")
    op.execute("DROP INDEX IF EXISTS member_role_member_company_idx")
    op.execute(
        "ALTER TABLE member_role_assignment DROP CONSTRAINT IF EXISTS uq_member_role_scope"
    )
    op.execute("DROP TABLE IF EXISTS member_role_assignment")
    op.execute("DROP TABLE IF EXISTS rbac_role_permission")
    op.execute("DROP TABLE IF EXISTS rbac_role")
    op.execute("DROP TABLE IF EXISTS rbac_permission")
