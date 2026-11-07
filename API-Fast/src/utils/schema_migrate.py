"""Ensure new columns and Phase 3–4 tables exist on already-created tables (idempotent)."""
from sqlalchemy import text


async def ensure_profile_and_approval_columns(connection) -> None:
    statements = [
        "ALTER TABLE member ADD COLUMN IF NOT EXISTS birth_date DATE",
        "ALTER TABLE member ADD COLUMN IF NOT EXISTS address TEXT",
        "ALTER TABLE member ADD COLUMN IF NOT EXISTS emergency_contact_name VARCHAR",
        "ALTER TABLE member ADD COLUMN IF NOT EXISTS emergency_contact_phone VARCHAR",
        "ALTER TABLE member ADD COLUMN IF NOT EXISTS attachment_urls TEXT",
        "ALTER TABLE employee_timestamp ADD COLUMN IF NOT EXISTS note TEXT",
        "ALTER TABLE employee_timestamp ADD COLUMN IF NOT EXISTS approval_status VARCHAR(20) DEFAULT 'NONE'",
        "ALTER TABLE employee_timestamp ADD COLUMN IF NOT EXISTS approved_by UUID",
        "ALTER TABLE employee_timestamp ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ",
        "ALTER TABLE employee_timestamp ADD COLUMN IF NOT EXISTS reject_reason VARCHAR",
        "ALTER TABLE employee_timestamp ADD COLUMN IF NOT EXISTS is_late BOOLEAN DEFAULT FALSE",
        "ALTER TABLE employee_timestamp ADD COLUMN IF NOT EXISTS late_minutes INTEGER DEFAULT 0",
        "ALTER TABLE employee_timestamp ADD COLUMN IF NOT EXISTS overtime_minutes INTEGER DEFAULT 0",
        "ALTER TABLE employee_timestamp ADD COLUMN IF NOT EXISTS shift_name VARCHAR(100)",
        "ALTER TABLE member ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN DEFAULT FALSE",
        "ALTER TABLE member ADD COLUMN IF NOT EXISTS failed_login_count INTEGER DEFAULT 0",
        "ALTER TABLE member ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ",
        "ALTER TABLE member ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ",
        "ALTER TABLE member ADD COLUMN IF NOT EXISTS biometric_consent_at TIMESTAMPTZ",
        "ALTER TABLE member ADD COLUMN IF NOT EXISTS totp_secret VARCHAR(128)",
        "ALTER TABLE member ADD COLUMN IF NOT EXISTS totp_enabled BOOLEAN DEFAULT FALSE",
        "ALTER TABLE company ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ",
        "ALTER TABLE company_employee ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ",
        "ALTER TABLE company_employee ADD COLUMN IF NOT EXISTS shift_id UUID",
        "ALTER TABLE department ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ",
        "ALTER TABLE department ADD COLUMN IF NOT EXISTS shift_id UUID",
        "ALTER TABLE position ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ",
        "ALTER TABLE company_location ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ",
        """
        CREATE TABLE IF NOT EXISTS work_shift (
            "shiftId" UUID PRIMARY KEY,
            "companyId" UUID NOT NULL REFERENCES company("companyId") ON DELETE CASCADE,
            name VARCHAR(100) NOT NULL,
            start_time VARCHAR(10) NOT NULL DEFAULT '09:00',
            end_time VARCHAR(10) NOT NULL DEFAULT '18:00',
            grace_minutes INTEGER NOT NULL DEFAULT 15,
            is_cross_midnight BOOLEAN NOT NULL DEFAULT FALSE,
            is_default BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ,
            deleted_at TIMESTAMPTZ
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS company_holiday (
            "holidayId" UUID PRIMARY KEY,
            "companyId" UUID NOT NULL REFERENCES company("companyId") ON DELETE CASCADE,
            holiday_date DATE NOT NULL,
            name VARCHAR(150) NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now(),
            deleted_at TIMESTAMPTZ
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS leave_request (
            "leaveId" UUID PRIMARY KEY,
            "companyId" UUID NOT NULL REFERENCES company("companyId") ON DELETE CASCADE,
            "company_employeeId" UUID NOT NULL REFERENCES company_employee("company_employeeId") ON DELETE CASCADE,
            leave_type VARCHAR(30) NOT NULL DEFAULT 'ANNUAL',
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            reason TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
            approved_by UUID,
            approved_at TIMESTAMPTZ,
            reject_reason VARCHAR,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS kiosk_device (
            "deviceId" UUID PRIMARY KEY,
            "companyId" UUID NOT NULL REFERENCES company("companyId") ON DELETE CASCADE,
            location_id UUID,
            name VARCHAR(120) NOT NULL,
            token_hash VARCHAR(128) NOT NULL,
            last_seen_at TIMESTAMPTZ,
            revoked_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS work_shift_company_idx
        ON work_shift ("companyId")
        """,
        """
        CREATE INDEX IF NOT EXISTS company_holiday_company_date_idx
        ON company_holiday ("companyId", holiday_date)
        """,
        """
        CREATE INDEX IF NOT EXISTS leave_request_company_dates_idx
        ON leave_request ("companyId", start_date, end_date, status)
        """,
        """
        CREATE INDEX IF NOT EXISTS kiosk_device_company_idx
        ON kiosk_device ("companyId", revoked_at)
        """,
        "ALTER TABLE kiosk_device ALTER COLUMN token_hash DROP NOT NULL",
        "ALTER TABLE kiosk_device ADD COLUMN IF NOT EXISTS token_family VARCHAR(64)",
        "ALTER TABLE kiosk_device ADD COLUMN IF NOT EXISTS pairing_code_hash VARCHAR(128)",
        "ALTER TABLE kiosk_device ADD COLUMN IF NOT EXISTS pairing_expires_at TIMESTAMPTZ",
        "ALTER TABLE kiosk_device ADD COLUMN IF NOT EXISTS paired_at TIMESTAMPTZ",
        """
        CREATE INDEX IF NOT EXISTS kiosk_device_pairing_code_idx
        ON kiosk_device (pairing_code_hash)
        WHERE pairing_code_hash IS NOT NULL
        """,
        """
        CREATE TABLE IF NOT EXISTS revoked_token (
            jti VARCHAR(96) PRIMARY KEY,
            family_id VARCHAR(64),
            scope VARCHAR(10) NOT NULL DEFAULT 'token',
            exp TIMESTAMPTZ NOT NULL,
            reason VARCHAR(40),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS revoked_token_family_idx
        ON revoked_token (family_id, scope)
        """,
        "CREATE INDEX IF NOT EXISTS revoked_token_exp_idx ON revoked_token (exp)",
        """
        CREATE TABLE IF NOT EXISTS sentinel_identity (
            "identityId" UUID PRIMARY KEY,
            "companyId" UUID NOT NULL REFERENCES company("companyId") ON DELETE CASCADE,
            identity_type VARCHAR(30) NOT NULL DEFAULT 'VISITOR',
            full_name VARCHAR(160) NOT NULL,
            document_ref VARCHAR(100),
            phone_number VARCHAR(50),
            email VARCHAR(150),
            organization VARCHAR(150),
            severity VARCHAR(20) NOT NULL DEFAULT 'LOW',
            alert_note TEXT,
            visit_purpose VARCHAR(255),
            host_member_id UUID,
            seat_number VARCHAR(60),
            event_id UUID,
            allowed_zone_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
            picture_url VARCHAR(255),
            embedding vector(512),
            valid_from TIMESTAMPTZ DEFAULT now(),
            expires_at TIMESTAMPTZ,
            consent_accepted_at TIMESTAMPTZ,
            status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ,
            deleted_at TIMESTAMPTZ
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS sentinel_identity_company_type_idx
        ON sentinel_identity ("companyId", identity_type, status)
        """,
        """
        CREATE INDEX IF NOT EXISTS sentinel_identity_embedding_hnsw_idx
        ON sentinel_identity
        USING hnsw (embedding vector_cosine_ops)
        """,
        """
        CREATE TABLE IF NOT EXISTS sentinel_access_zone (
            "zoneId" UUID PRIMARY KEY,
            "companyId" UUID NOT NULL REFERENCES company("companyId") ON DELETE CASCADE,
            name VARCHAR(120) NOT NULL,
            code VARCHAR(60) NOT NULL DEFAULT 'MAIN-GATE',
            location_id UUID,
            station_mode VARCHAR(30) NOT NULL DEFAULT 'ACCESS_CONTROL',
            allowed_departments JSONB NOT NULL DEFAULT '[]'::jsonb,
            allowed_identity_types JSONB NOT NULL DEFAULT '["EMPLOYEE","VIP","VISITOR"]'::jsonb,
            schedule_start VARCHAR(10) NOT NULL DEFAULT '00:00',
            schedule_end VARCHAR(10) NOT NULL DEFAULT '23:59',
            require_2fa BOOLEAN NOT NULL DEFAULT FALSE,
            relay_webhook_url VARCHAR(255),
            relay_secret VARCHAR(128),
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ,
            deleted_at TIMESTAMPTZ
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS sentinel_access_zone_company_idx
        ON sentinel_access_zone ("companyId", is_active)
        """,
        """
        CREATE TABLE IF NOT EXISTS sentinel_event (
            "eventId" UUID PRIMARY KEY,
            "companyId" UUID NOT NULL REFERENCES company("companyId") ON DELETE CASCADE,
            name VARCHAR(160) NOT NULL,
            location_name VARCHAR(160),
            start_at TIMESTAMPTZ NOT NULL,
            end_at TIMESTAMPTZ NOT NULL,
            welcome_message VARCHAR(255),
            capacity INTEGER NOT NULL DEFAULT 200,
            auto_expire_days INTEGER NOT NULL DEFAULT 7,
            status VARCHAR(20) NOT NULL DEFAULT 'LIVE',
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ,
            deleted_at TIMESTAMPTZ
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS sentinel_event_company_idx
        ON sentinel_event ("companyId", status, start_at)
        """,
        """
        CREATE TABLE IF NOT EXISTS sentinel_incident_log (
            "incidentId" UUID PRIMARY KEY,
            "companyId" UUID NOT NULL REFERENCES company("companyId") ON DELETE CASCADE,
            event_type VARCHAR(40) NOT NULL,
            severity VARCHAR(20) NOT NULL DEFAULT 'INFO',
            identity_id UUID,
            member_id UUID,
            subject_name VARCHAR(160),
            identity_type VARCHAR(30),
            zone_id UUID,
            zone_name VARCHAR(120),
            event_id UUID,
            confidence_percent DOUBLE PRECISION,
            distance DOUBLE PRECISION,
            snapshot_url VARCHAR(255),
            action_taken VARCHAR(255),
            acknowledged_by UUID,
            acknowledged_at TIMESTAMPTZ,
            occurred_at TIMESTAMPTZ DEFAULT now()
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS sentinel_incident_company_occurred_idx
        ON sentinel_incident_log ("companyId", occurred_at DESC)
        """,
        """
        CREATE INDEX IF NOT EXISTS employee_timestamp_company_ts_idx
        ON employee_timestamp ("companyId", "timestamp")
        """,
        """
        CREATE INDEX IF NOT EXISTS employee_timestamp_emp_ts_idx
        ON employee_timestamp ("company_employeeId", "timestamp")
        """,
        """
        CREATE INDEX IF NOT EXISTS face_encoding_member_idx
        ON face_encoding ("memberId")
        """,
        """
        CREATE INDEX IF NOT EXISTS audit_log_company_occurred_idx
        ON audit_log ("companyId", "occurredAt" DESC)
        """,
        """
        CREATE INDEX IF NOT EXISTS notification_outbox_status_created_idx
        ON notification_outbox ("status", "createdAt")
        """,
        """
        DO $$ BEGIN
          CREATE UNIQUE INDEX uq_company_employee_member_company
          ON company_employee ("memberId", "companyId");
        EXCEPTION WHEN duplicate_table OR unique_violation THEN NULL;
        END $$;
        """,
        """
        DO $$ BEGIN
          CREATE UNIQUE INDEX uq_company_employee_code
          ON company_employee ("companyId", "employeeId")
          WHERE "employeeId" IS NOT NULL AND "employeeId" <> '';
        EXCEPTION WHEN duplicate_table OR unique_violation THEN NULL;
        END $$;
        """,
        """
        DO $$ BEGIN
          ALTER TABLE employee_timestamp
            ADD CONSTRAINT employee_timestamp_approved_by_fkey
            FOREIGN KEY (approved_by) REFERENCES member("memberId");
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """,
    ]
    for stmt in statements:
        await connection.execute(text(stmt))
