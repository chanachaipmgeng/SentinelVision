"""Placeholder for feat/phase-d-rbac (D1).

Revision ID: 0014_rbac
Revises: 0013_approvals_payroll_period
Create Date: 2026-11-07

Owned by branch ``feat/phase-d-rbac``. This no-op file keeps the Phase D alembic
chain linear (see ``internal/phase-d-contract.md``) until that sibling pushes;
replace this file wholesale by copying from that branch.
"""
from __future__ import annotations

revision = "0014_rbac"
down_revision = "0013_approvals_payroll_period"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
