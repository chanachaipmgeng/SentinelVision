"""Placeholder for feat/phase-d-devices-tenant (D2+D5).

Revision ID: 0015_devices_tenant
Revises: 0014_rbac
Create Date: 2026-11-07

Owned by branch ``feat/phase-d-devices-tenant``. This no-op file keeps the Phase D
alembic chain linear (see ``internal/phase-d-contract.md``) until that sibling
pushes; replace this file wholesale by copying from that branch.
"""
from __future__ import annotations

revision = "0015_devices_tenant"
down_revision = "0014_rbac"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
