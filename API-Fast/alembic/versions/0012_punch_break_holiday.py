"""C3+C6 placeholder: punch break types + holiday import hooks.

Revision ID: 0012_punch_break_holiday
Revises: 0011_attendance_daily_shift_rules
Create Date: 2026-11-07

Owned by branch ``phase-c/punch-holidays``. Chain stub — replace with the sibling's
identical revision when pushed. BREAK_OUT / BREAK_IN enum expansion is C3's concern;
this stub is intentionally a no-op DDL so C4/C5 can upgrade past it.
"""
from __future__ import annotations

from alembic import op

revision = "0012_punch_break_holiday"
down_revision = "0011_attendance_daily_shift_rules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Intentionally empty until sibling C3/C6 lands the real punch/holiday DDL.
    op.execute("SELECT 1")


def downgrade() -> None:
    op.execute("SELECT 1")
