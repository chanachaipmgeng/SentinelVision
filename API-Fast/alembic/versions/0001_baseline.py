"""Baseline schema — every table, index, FK and enum of the Phase A models.

Revision ID: 0001_baseline
Revises: None
Create Date: 2026-11-07

Up to Phase A this revision was an empty marker and the runtime created tables with
``Base.metadata.create_all`` + ``utils/schema_migrate.py``. Since Phase B1 Alembic is the only
schema source, so a fresh database gets the complete schema here; revisions 0002-0008 stay
idempotent (``IF NOT EXISTS``) for databases that were created by the old startup path and are
stamped at ``0008_revocation_kiosk_pairing`` (see docs/RUNBOOK.md, "Database migrations").
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None

ENUM_TYPES = (
    "publictype",
    "roletype",
    "statustype",
    "locationtype",
    "emptype",
    "companyroletype",
    "timestamptype",
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table('audit_log',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('occurredAt', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('actorMemberId', sa.UUID(), nullable=True),
    sa.Column('actorRole', sa.String(), nullable=True),
    sa.Column('companyId', sa.UUID(), nullable=True),
    sa.Column('action', sa.String(), nullable=False),
    sa.Column('entityType', sa.String(), nullable=True),
    sa.Column('entityId', sa.String(), nullable=True),
    sa.Column('path', sa.String(), nullable=True),
    sa.Column('statusCode', sa.String(), nullable=True),
    sa.Column('ip', sa.String(), nullable=True),
    sa.Column('userAgent', sa.Text(), nullable=True),
    sa.Column('requestId', sa.String(), nullable=True),
    sa.Column('detail', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('audit_log_company_occurred_idx', 'audit_log', ['companyId', sa.literal_column('"occurredAt" DESC')], unique=False)
    op.create_table('company',
    sa.Column('companyId', sa.UUID(), nullable=False),
    sa.Column('companyName', sa.String(), nullable=False),
    sa.Column('companyCode', sa.String(), nullable=False),
    sa.Column('companyInfo', sa.String(), nullable=False),
    sa.Column('picture', sa.String(), nullable=True),
    sa.Column('address', sa.String(), nullable=False),
    sa.Column('latitude', sa.Float(), nullable=False),
    sa.Column('longitude', sa.Float(), nullable=False),
    sa.Column('status', sa.Enum('PUBLIC', 'PENDING', name='publictype'), nullable=False),
    sa.Column('createdAt', sa.DateTime(), nullable=False),
    sa.Column('updatedAt', sa.DateTime(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('ownerName', sa.String(), nullable=True),
    sa.Column('contact', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('companyId'),
    sa.UniqueConstraint('companyCode'),
    sa.UniqueConstraint('companyName')
    )
    op.create_table('import_job',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('companyId', sa.UUID(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('error', sa.String(), nullable=True),
    sa.Column('createdAt', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('finishedAt', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('member',
    sa.Column('memberId', sa.UUID(), nullable=False),
    sa.Column('username', sa.String(), nullable=False),
    sa.Column('passwordHash', sa.String(), nullable=False),
    sa.Column('firstName', sa.String(), nullable=True),
    sa.Column('lastName', sa.String(), nullable=True),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('phoneNumber', sa.String(), nullable=True),
    sa.Column('role', sa.Enum('MEMBER', 'ADMIN_COMPANY', 'ADMIN_SYSTEM', name='roletype'), nullable=False),
    sa.Column('status', sa.Enum('ENABLE', 'DISABLED', name='statustype'), nullable=False),
    sa.Column('picture', sa.String(), nullable=True),
    sa.Column('birth_date', sa.Date(), nullable=True),
    sa.Column('address', sa.Text(), nullable=True),
    sa.Column('emergency_contact_name', sa.String(), nullable=True),
    sa.Column('emergency_contact_phone', sa.String(), nullable=True),
    sa.Column('attachment_urls', sa.Text(), nullable=True),
    sa.Column('must_change_password', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('failed_login_count', sa.Integer(), server_default='0', nullable=False),
    sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('biometric_consent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('totp_secret', sa.String(length=128), nullable=True),
    sa.Column('totp_enabled', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('createdAt', sa.DateTime(), nullable=False),
    sa.Column('updatedAt', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('memberId'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('username')
    )
    op.create_table('notification_outbox',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('companyId', sa.UUID(), nullable=True),
    sa.Column('event', sa.String(), nullable=False),
    sa.Column('channel', sa.String(), nullable=False),
    sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('lastError', sa.String(), nullable=True),
    sa.Column('createdAt', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('notification_outbox_status_created_idx', 'notification_outbox', ['status', 'createdAt'], unique=False)
    op.create_table('revoked_token',
    sa.Column('jti', sa.String(length=96), nullable=False),
    sa.Column('family_id', sa.String(length=64), nullable=True),
    sa.Column('scope', sa.String(length=10), server_default='token', nullable=False),
    sa.Column('exp', sa.DateTime(timezone=True), nullable=False),
    sa.Column('reason', sa.String(length=40), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('jti')
    )
    op.create_index('revoked_token_exp_idx', 'revoked_token', ['exp'], unique=False)
    op.create_index('revoked_token_family_idx', 'revoked_token', ['family_id', 'scope'], unique=False)
    op.create_table('system_setting',
    sa.Column('key', sa.String(), nullable=False),
    sa.Column('value', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('updatedAt', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('key')
    )
    op.create_table('company_holiday',
    sa.Column('holidayId', sa.UUID(), nullable=False),
    sa.Column('companyId', sa.UUID(), nullable=False),
    sa.Column('holiday_date', sa.Date(), nullable=False),
    sa.Column('name', sa.String(length=150), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['companyId'], ['company.companyId'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('holidayId')
    )
    op.create_index('company_holiday_company_date_idx', 'company_holiday', ['companyId', 'holiday_date'], unique=False)
    op.create_table('company_location',
    sa.Column('locationId', sa.UUID(), nullable=False),
    sa.Column('companyId', sa.UUID(), nullable=False),
    sa.Column('latitude', sa.Float(), nullable=False),
    sa.Column('longitude', sa.Float(), nullable=False),
    sa.Column('locationName', sa.String(), nullable=False),
    sa.Column('radius', sa.Float(), nullable=False),
    sa.Column('locationType', sa.Enum('PERMANENT', 'TEMPORARY', name='locationtype'), nullable=False),
    sa.Column('startDate', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('endDate', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('createdAt', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updatedAt', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['companyId'], ['company.companyId'], ),
    sa.PrimaryKeyConstraint('locationId')
    )
    op.create_table('department',
    sa.Column('departmentId', sa.UUID(), nullable=False),
    sa.Column('thName', sa.String(), nullable=False),
    sa.Column('engName', sa.String(), nullable=False),
    sa.Column('companyId', sa.UUID(), nullable=False),
    sa.Column('shift_id', sa.UUID(), nullable=True),
    sa.Column('createdAt', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updatedAt', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['companyId'], ['company.companyId'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('departmentId')
    )
    op.create_table('face_encoding',
    sa.Column('faceEncodingId', sa.UUID(), nullable=False),
    sa.Column('memberId', sa.UUID(), nullable=False),
    sa.Column('companyId', sa.UUID(), nullable=True),
    sa.Column('embedding', Vector(512), nullable=False),
    sa.Column('createdAt', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['companyId'], ['company.companyId'], ),
    sa.ForeignKeyConstraint(['memberId'], ['member.memberId'], ),
    sa.PrimaryKeyConstraint('faceEncodingId')
    )
    op.create_index('face_encoding_company_member_idx', 'face_encoding', ['companyId', 'memberId'], unique=False)
    op.create_index('face_encoding_embedding_hnsw_idx', 'face_encoding', ['embedding'], unique=False, postgresql_using='hnsw', postgresql_ops={'embedding': 'vector_cosine_ops'})
    op.create_index('face_encoding_member_idx', 'face_encoding', ['memberId'], unique=False)
    op.create_table('kiosk_device',
    sa.Column('deviceId', sa.UUID(), nullable=False),
    sa.Column('companyId', sa.UUID(), nullable=False),
    sa.Column('location_id', sa.UUID(), nullable=True),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('token_hash', sa.String(length=128), nullable=True),
    sa.Column('token_family', sa.String(length=64), nullable=True),
    sa.Column('pairing_code_hash', sa.String(length=128), nullable=True),
    sa.Column('pairing_expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('paired_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['companyId'], ['company.companyId'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('deviceId')
    )
    op.create_index('kiosk_device_company_idx', 'kiosk_device', ['companyId', 'revoked_at'], unique=False)
    op.create_index('kiosk_device_pairing_code_idx', 'kiosk_device', ['pairing_code_hash'], unique=False, postgresql_where=sa.text('pairing_code_hash IS NOT NULL'))
    op.create_table('position',
    sa.Column('positionId', sa.UUID(), nullable=False),
    sa.Column('thName', sa.String(), nullable=False),
    sa.Column('engName', sa.String(), nullable=False),
    sa.Column('companyId', sa.UUID(), nullable=False),
    sa.Column('createdAt', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updatedAt', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['companyId'], ['company.companyId'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('positionId')
    )
    op.create_table('sentinel_access_zone',
    sa.Column('zoneId', sa.UUID(), nullable=False),
    sa.Column('companyId', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('code', sa.String(length=60), nullable=False),
    sa.Column('location_id', sa.UUID(), nullable=True),
    sa.Column('station_mode', sa.String(length=30), nullable=False),
    sa.Column('allowed_departments', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('allowed_identity_types', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('schedule_start', sa.String(length=10), nullable=False),
    sa.Column('schedule_end', sa.String(length=10), nullable=False),
    sa.Column('require_2fa', sa.Boolean(), nullable=False),
    sa.Column('relay_webhook_url', sa.String(length=255), nullable=True),
    sa.Column('relay_secret', sa.String(length=128), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['companyId'], ['company.companyId'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('zoneId')
    )
    op.create_index('sentinel_access_zone_company_idx', 'sentinel_access_zone', ['companyId', 'is_active'], unique=False)
    op.create_table('sentinel_event',
    sa.Column('eventId', sa.UUID(), nullable=False),
    sa.Column('companyId', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=160), nullable=False),
    sa.Column('location_name', sa.String(length=160), nullable=True),
    sa.Column('start_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('end_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('welcome_message', sa.String(length=255), nullable=True),
    sa.Column('capacity', sa.Integer(), nullable=False),
    sa.Column('auto_expire_days', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['companyId'], ['company.companyId'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('eventId')
    )
    op.create_index('sentinel_event_company_idx', 'sentinel_event', ['companyId', 'status', 'start_at'], unique=False)
    op.create_table('sentinel_identity',
    sa.Column('identityId', sa.UUID(), nullable=False),
    sa.Column('companyId', sa.UUID(), nullable=False),
    sa.Column('identity_type', sa.String(length=30), nullable=False),
    sa.Column('full_name', sa.String(length=160), nullable=False),
    sa.Column('document_ref', sa.String(length=100), nullable=True),
    sa.Column('phone_number', sa.String(length=50), nullable=True),
    sa.Column('email', sa.String(length=150), nullable=True),
    sa.Column('organization', sa.String(length=150), nullable=True),
    sa.Column('severity', sa.String(length=20), nullable=False),
    sa.Column('alert_note', sa.Text(), nullable=True),
    sa.Column('visit_purpose', sa.String(length=255), nullable=True),
    sa.Column('host_member_id', sa.UUID(), nullable=True),
    sa.Column('seat_number', sa.String(length=60), nullable=True),
    sa.Column('event_id', sa.UUID(), nullable=True),
    sa.Column('allowed_zone_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('picture_url', sa.String(length=255), nullable=True),
    sa.Column('embedding', Vector(512), nullable=True),
    sa.Column('valid_from', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('consent_accepted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['companyId'], ['company.companyId'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('identityId')
    )
    op.create_index('sentinel_identity_company_type_idx', 'sentinel_identity', ['companyId', 'identity_type', 'status'], unique=False)
    op.create_index('sentinel_identity_embedding_hnsw_idx', 'sentinel_identity', ['embedding'], unique=False, postgresql_using='hnsw', postgresql_ops={'embedding': 'vector_cosine_ops'})
    op.create_table('sentinel_incident_log',
    sa.Column('incidentId', sa.UUID(), nullable=False),
    sa.Column('companyId', sa.UUID(), nullable=False),
    sa.Column('event_type', sa.String(length=40), nullable=False),
    sa.Column('severity', sa.String(length=20), nullable=False),
    sa.Column('identity_id', sa.UUID(), nullable=True),
    sa.Column('member_id', sa.UUID(), nullable=True),
    sa.Column('subject_name', sa.String(length=160), nullable=True),
    sa.Column('identity_type', sa.String(length=30), nullable=True),
    sa.Column('zone_id', sa.UUID(), nullable=True),
    sa.Column('zone_name', sa.String(length=120), nullable=True),
    sa.Column('event_id', sa.UUID(), nullable=True),
    sa.Column('confidence_percent', sa.Float(), nullable=True),
    sa.Column('distance', sa.Float(), nullable=True),
    sa.Column('snapshot_url', sa.String(length=255), nullable=True),
    sa.Column('action_taken', sa.String(length=255), nullable=True),
    sa.Column('acknowledged_by', sa.UUID(), nullable=True),
    sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['companyId'], ['company.companyId'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('incidentId')
    )
    op.create_index('sentinel_incident_company_occurred_idx', 'sentinel_incident_log', ['companyId', sa.literal_column('occurred_at DESC')], unique=False)
    op.create_table('work_shift',
    sa.Column('shiftId', sa.UUID(), nullable=False),
    sa.Column('companyId', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('start_time', sa.String(length=10), nullable=False),
    sa.Column('end_time', sa.String(length=10), nullable=False),
    sa.Column('grace_minutes', sa.Integer(), nullable=False),
    sa.Column('is_cross_midnight', sa.Boolean(), nullable=False),
    sa.Column('is_default', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['companyId'], ['company.companyId'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('shiftId')
    )
    op.create_index('work_shift_company_idx', 'work_shift', ['companyId'], unique=False)
    op.create_table('company_employee',
    sa.Column('company_employeeId', sa.UUID(), nullable=False),
    sa.Column('memberId', sa.UUID(), nullable=False),
    sa.Column('companyId', sa.UUID(), nullable=False),
    sa.Column('positionId', sa.UUID(), nullable=False),
    sa.Column('departmentId', sa.UUID(), nullable=False),
    sa.Column('shift_id', sa.UUID(), nullable=True),
    sa.Column('employeeId', sa.String(), nullable=True),
    sa.Column('startDate', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('empType', sa.Enum('PERMONTH', 'PERDAY', name='emptype'), nullable=False),
    sa.Column('companyRoleType', sa.Enum('EMP', 'ADMIN_COMPANY', name='companyroletype'), nullable=False),
    sa.Column('salary', sa.Float(), nullable=False),
    sa.Column('bossId', sa.String(), nullable=True),
    sa.Column('createdAt', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updatedAt', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['companyId'], ['company.companyId'], ),
    sa.ForeignKeyConstraint(['departmentId'], ['department.departmentId'], ),
    sa.ForeignKeyConstraint(['memberId'], ['member.memberId'], ),
    sa.ForeignKeyConstraint(['positionId'], ['position.positionId'], ),
    sa.PrimaryKeyConstraint('company_employeeId')
    )
    op.create_index('uq_company_employee_code', 'company_employee', ['companyId', 'employeeId'], unique=True, postgresql_where=sa.text('"employeeId" IS NOT NULL AND "employeeId" <> \'\''))
    op.create_index('uq_company_employee_member_company', 'company_employee', ['memberId', 'companyId'], unique=True)
    op.create_table('employee_timestamp',
    sa.Column('timestampId', sa.UUID(), nullable=False),
    sa.Column('company_employeeId', sa.UUID(), nullable=False),
    sa.Column('companyId', sa.UUID(), nullable=False),
    sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('timestampType', sa.Enum('CHECK_IN', 'CHECK_OUT', 'WARNING', 'DISAPPROVE', name='timestamptype'), nullable=False),
    sa.Column('createdAt', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updatedAt', sa.DateTime(timezone=True), nullable=True),
    sa.Column('locationName', sa.String(), nullable=True),
    sa.Column('latitude', sa.Float(), nullable=True),
    sa.Column('longitude', sa.Float(), nullable=True),
    sa.Column('photoTimestamp', sa.String(), nullable=True),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('approval_status', sa.String(length=20), nullable=False),
    sa.Column('approved_by', sa.UUID(), nullable=True),
    sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('reject_reason', sa.String(), nullable=True),
    sa.Column('is_late', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('late_minutes', sa.Integer(), server_default='0', nullable=False),
    sa.Column('overtime_minutes', sa.Integer(), server_default='0', nullable=False),
    sa.Column('shift_name', sa.String(length=100), nullable=True),
    sa.ForeignKeyConstraint(['approved_by'], ['member.memberId'], name='employee_timestamp_approved_by_fkey'),
    sa.ForeignKeyConstraint(['companyId'], ['company.companyId'], ),
    sa.ForeignKeyConstraint(['company_employeeId'], ['company_employee.company_employeeId'], ),
    sa.PrimaryKeyConstraint('timestampId')
    )
    op.create_index('employee_timestamp_company_ts_idx', 'employee_timestamp', ['companyId', 'timestamp'], unique=False)
    op.create_index('employee_timestamp_emp_ts_idx', 'employee_timestamp', ['company_employeeId', 'timestamp'], unique=False)
    op.create_table('leave_request',
    sa.Column('leaveId', sa.UUID(), nullable=False),
    sa.Column('companyId', sa.UUID(), nullable=False),
    sa.Column('company_employeeId', sa.UUID(), nullable=False),
    sa.Column('leave_type', sa.String(length=30), nullable=False),
    sa.Column('start_date', sa.Date(), nullable=False),
    sa.Column('end_date', sa.Date(), nullable=False),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('approved_by', sa.UUID(), nullable=True),
    sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('reject_reason', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['companyId'], ['company.companyId'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['company_employeeId'], ['company_employee.company_employeeId'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('leaveId')
    )
    op.create_index('leave_request_company_dates_idx', 'leave_request', ['companyId', 'start_date', 'end_date', 'status'], unique=False)



def downgrade() -> None:
    # Later revisions (0007, 0009) may already have dropped some of these indexes.
    op.drop_index('leave_request_company_dates_idx', table_name='leave_request', if_exists=True)
    op.drop_table('leave_request')
    op.drop_index('employee_timestamp_emp_ts_idx', table_name='employee_timestamp', if_exists=True)
    op.drop_index('employee_timestamp_company_ts_idx', table_name='employee_timestamp', if_exists=True)
    op.drop_table('employee_timestamp')
    op.drop_index('uq_company_employee_member_company', table_name='company_employee', if_exists=True)
    op.drop_index('uq_company_employee_code', table_name='company_employee', postgresql_where=sa.text('"employeeId" IS NOT NULL AND "employeeId" <> \'\''), if_exists=True)
    op.drop_table('company_employee')
    op.drop_index('work_shift_company_idx', table_name='work_shift', if_exists=True)
    op.drop_table('work_shift')
    op.drop_index('sentinel_incident_company_occurred_idx', table_name='sentinel_incident_log', if_exists=True)
    op.drop_table('sentinel_incident_log')
    op.drop_index('sentinel_identity_embedding_hnsw_idx', table_name='sentinel_identity', postgresql_using='hnsw', postgresql_ops={'embedding': 'vector_cosine_ops'}, if_exists=True)
    op.drop_index('sentinel_identity_company_type_idx', table_name='sentinel_identity', if_exists=True)
    op.drop_table('sentinel_identity')
    op.drop_index('sentinel_event_company_idx', table_name='sentinel_event', if_exists=True)
    op.drop_table('sentinel_event')
    op.drop_index('sentinel_access_zone_company_idx', table_name='sentinel_access_zone', if_exists=True)
    op.drop_table('sentinel_access_zone')
    op.drop_table('position')
    op.drop_index('kiosk_device_pairing_code_idx', table_name='kiosk_device', postgresql_where=sa.text('pairing_code_hash IS NOT NULL'), if_exists=True)
    op.drop_index('kiosk_device_company_idx', table_name='kiosk_device', if_exists=True)
    op.drop_table('kiosk_device')
    op.drop_index('face_encoding_member_idx', table_name='face_encoding', if_exists=True)
    op.drop_index('face_encoding_embedding_hnsw_idx', table_name='face_encoding', postgresql_using='hnsw', postgresql_ops={'embedding': 'vector_cosine_ops'}, if_exists=True)
    op.drop_index('face_encoding_company_member_idx', table_name='face_encoding', if_exists=True)
    op.drop_table('face_encoding')
    op.drop_table('department')
    op.drop_table('company_location')
    op.drop_index('company_holiday_company_date_idx', table_name='company_holiday', if_exists=True)
    op.drop_table('company_holiday')
    op.drop_table('system_setting')
    op.drop_index('revoked_token_family_idx', table_name='revoked_token', if_exists=True)
    op.drop_index('revoked_token_exp_idx', table_name='revoked_token', if_exists=True)
    op.drop_table('revoked_token')
    op.drop_index('notification_outbox_status_created_idx', table_name='notification_outbox', if_exists=True)
    op.drop_table('notification_outbox')
    op.drop_table('member')
    op.drop_table('import_job')
    op.drop_table('company')
    op.drop_index('audit_log_company_occurred_idx', table_name='audit_log', if_exists=True)
    op.drop_table('audit_log')
    for enum_name in ENUM_TYPES:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
