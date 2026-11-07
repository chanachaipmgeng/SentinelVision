"""D1 RBAC placeholder — owned by feat/phase-d-rbac.

Revision ID: 0014_rbac
Revises: 0013_approvals_payroll_period
Create Date: 2026-11-07

Sibling branch not yet on origin when this file was added to
``feat/phase-d-api-ratelimit-face``. Empty no-op so the 0014→0017 chain resolves;
replace with a **byte-identical** copy from ``feat/phase-d-rbac`` at integration.
"""
from __future__ import annotations

revision = "0014_rbac"
down_revision = "0013_approvals_payroll_period"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Placeholder — real DDL lands from feat/phase-d-rbac.
    pass


def downgrade() -> None:
    pass
