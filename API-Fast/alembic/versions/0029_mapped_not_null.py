"""Align NOT NULL with Mapped[] models after Column→Mapped conversion.

Revision ID: 0029_mapped_not_null
Revises: 0028_error_log
Create Date: 2026-11-12

Mapped[T] columns default to nullable=False. Legacy migrations created several
timestamp / text columns as nullable; alembic check then reports modify_nullable
drift. Backfill NULLs then SET NOT NULL so models and the database agree.
"""
from __future__ import annotations

from alembic import op

revision = "0029_mapped_not_null"
down_revision = "0028_error_log"
branch_labels = None
depends_on = None

# (table, column, backfill SQL expression)
_NOT_NULL_COLUMNS: list[tuple[str, str, str]] = [
    ("attendance_daily", "created_at", "now()"),
    ("attendance_daily", "updated_at", "now()"),
    ("camera", "created_at", "now()"),
    ("camera", "updated_at", "now()"),
    ("company", "ownerName", "''"),
    ("company", "contact", "''"),
    ("company_api_key", "created_at", "now()"),
    ("company_employee", "startDate", "now()"),
    ("company_employee", "createdAt", "now()"),
    ("company_employee", "updatedAt", "now()"),
    ("company_holiday", "created_at", "now()"),
    ("company_location", "startDate", "now()"),
    ("company_location", "endDate", "now()"),
    ("company_location", "createdAt", "now()"),
    ("company_location", "updatedAt", "now()"),
    ("department", "createdAt", "now()"),
    ("department", "updatedAt", "now()"),
    ("employee_timestamp", "timestamp", "now()"),
    ("employee_timestamp", "createdAt", "now()"),
    ("employee_timestamp", "updatedAt", "now()"),
    ("import_job", "createdAt", "now()"),
    ("in_app_notification", "createdAt", "now()"),
    ("kiosk_device", "created_at", "now()"),
    ("leave_balance", "createdAt", "now()"),
    ("leave_balance", "updatedAt", "now()"),
    ("leave_request", "created_at", "now()"),
    ("leave_request", "updated_at", "now()"),
    ("member_role_assignment", "updatedAt", "now()"),
    ("notification_outbox", "createdAt", "now()"),
    ("notification_preference", "createdAt", "now()"),
    ("notification_preference", "updatedAt", "now()"),
    ("notification_template", "createdAt", "now()"),
    ("notification_template", "updatedAt", "now()"),
    ("ot_approval_request", "createdAt", "now()"),
    ("ot_approval_request", "updatedAt", "now()"),
    ("payroll_period", "createdAt", "now()"),
    ("payroll_period", "updatedAt", "now()"),
    ("people_count_bucket", "created_at", "now()"),
    ("people_count_bucket", "updated_at", "now()"),
    ("position", "createdAt", "now()"),
    ("position", "updatedAt", "now()"),
    ("rbac_permission", "createdAt", "now()"),
    ("rbac_role", "createdAt", "now()"),
    ("regularization_request", "createdAt", "now()"),
    ("regularization_request", "updatedAt", "now()"),
    ("sentinel_access_zone", "created_at", "now()"),
    ("sentinel_access_zone", "updated_at", "now()"),
    ("sentinel_event", "created_at", "now()"),
    ("sentinel_event", "updated_at", "now()"),
    ("sentinel_identity", "valid_from", "now()"),
    ("sentinel_identity", "created_at", "now()"),
    ("sentinel_identity", "updated_at", "now()"),
    ("sentinel_incident_log", "occurred_at", "now()"),
    ("site_floor", "created_at", "now()"),
    ("site_floor", "updated_at", "now()"),
    ("video_clip", "created_at", "now()"),
    ("work_shift", "created_at", "now()"),
    ("work_shift", "updated_at", "now()"),
]


def _qi(name: str) -> str:
    """Quote identifiers that use camelCase or are otherwise unsafe bare."""
    if name.isidentifier() and name.islower() and name.isascii():
        return name
    return f'"{name}"'


def upgrade() -> None:
    for table, column, fill in _NOT_NULL_COLUMNS:
        t = _qi(table)
        c = _qi(column)
        op.execute(f"UPDATE {t} SET {c} = {fill} WHERE {c} IS NULL")
        op.execute(f"ALTER TABLE {t} ALTER COLUMN {c} SET NOT NULL")


def downgrade() -> None:
    for table, column, _fill in reversed(_NOT_NULL_COLUMNS):
        t = _qi(table)
        c = _qi(column)
        op.execute(f"ALTER TABLE {t} ALTER COLUMN {c} DROP NOT NULL")
