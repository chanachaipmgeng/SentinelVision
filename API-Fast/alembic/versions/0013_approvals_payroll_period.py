"""C4+C5: leave balance, regularization, OT approval, payroll period lock.

Revision ID: 0013_approvals_payroll_period
Revises: 0012_punch_break_holiday
Create Date: 2026-11-07
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0013_approvals_payroll_period"
down_revision = "0012_punch_break_holiday"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "leave_balance",
        sa.Column("balanceId", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("companyId", postgresql.UUID(as_uuid=True), sa.ForeignKey("company.companyId", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "company_employeeId",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("company_employee.company_employeeId", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("leaveType", sa.String(30), nullable=False, server_default="ANNUAL"),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("entitledDays", sa.Float(), nullable=False, server_default="0"),
        sa.Column("usedDays", sa.Float(), nullable=False, server_default="0"),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updatedAt", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("leave_balance_company_emp_idx", "leave_balance", ["companyId", "company_employeeId"])
    op.create_unique_constraint(
        "uq_leave_balance_emp_type_year",
        "leave_balance",
        ["companyId", "company_employeeId", "leaveType", "year"],
    )

    op.create_table(
        "regularization_request",
        sa.Column("requestId", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("companyId", postgresql.UUID(as_uuid=True), sa.ForeignKey("company.companyId", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "company_employeeId",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("company_employee.company_employeeId", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("workDate", sa.Date(), nullable=False),
        sa.Column("requestedTimestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requestedType", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("originalTimestampId", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approvedBy", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approvedAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejectReason", sa.String(), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updatedAt", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("regularization_company_status_idx", "regularization_request", ["companyId", "status"])
    op.create_index(
        "regularization_company_emp_date_idx",
        "regularization_request",
        ["companyId", "company_employeeId", "workDate"],
    )

    op.create_table(
        "ot_approval_request",
        sa.Column("requestId", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("companyId", postgresql.UUID(as_uuid=True), sa.ForeignKey("company.companyId", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "company_employeeId",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("company_employee.company_employeeId", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("workDate", sa.Date(), nullable=False),
        sa.Column("otMinutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("thresholdMinutes", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("requiresApproval", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("approvedBy", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approvedAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejectReason", sa.String(), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updatedAt", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ot_approval_company_status_idx", "ot_approval_request", ["companyId", "status"])
    op.create_index(
        "ot_approval_company_emp_date_idx",
        "ot_approval_request",
        ["companyId", "company_employeeId", "workDate"],
    )

    op.create_table(
        "payroll_period",
        sa.Column("periodId", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("companyId", postgresql.UUID(as_uuid=True), sa.ForeignKey("company.companyId", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=True),
        sa.Column("startDate", sa.Date(), nullable=False),
        sa.Column("endDate", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="OPEN"),
        sa.Column("lockedAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lockedBy", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updatedAt", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint(
        "uq_payroll_period_range",
        "payroll_period",
        ["companyId", "startDate", "endDate"],
    )
    op.create_index("payroll_period_company_status_idx", "payroll_period", ["companyId", "status"])


def downgrade() -> None:
    op.drop_index("payroll_period_company_status_idx", table_name="payroll_period")
    op.drop_constraint("uq_payroll_period_range", "payroll_period", type_="unique")
    op.drop_table("payroll_period")

    op.drop_index("ot_approval_company_emp_date_idx", table_name="ot_approval_request")
    op.drop_index("ot_approval_company_status_idx", table_name="ot_approval_request")
    op.drop_table("ot_approval_request")

    op.drop_index("regularization_company_emp_date_idx", table_name="regularization_request")
    op.drop_index("regularization_company_status_idx", table_name="regularization_request")
    op.drop_table("regularization_request")

    op.drop_constraint("uq_leave_balance_emp_type_year", "leave_balance", type_="unique")
    op.drop_index("leave_balance_company_emp_idx", table_name="leave_balance")
    op.drop_table("leave_balance")
