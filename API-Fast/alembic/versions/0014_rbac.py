"""D1 RBAC placeholder — owned by feat/phase-d-rbac.

Revision ID: 0014_rbac
Revises: 0013_approvals_payroll_period
Create Date: 2026-11-07

This file is a **placeholder** so ``0015_devices_tenant`` can chain
``down_revision = "0014_rbac"`` while D1 is still in flight.

When ``feat/phase-d-rbac`` appears on origin, **replace this file with the
identical ``0014_rbac.py`` from that branch** (do not invent a parallel DDL).
Until then upgrade is a no-op so local/CI heads can advance past 0013.
"""
from __future__ import annotations

revision = "0014_rbac"
down_revision = "0013_approvals_payroll_period"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No-op placeholder. Real RBAC DDL lands from feat/phase-d-rbac.
    return


def downgrade() -> None:
    return
