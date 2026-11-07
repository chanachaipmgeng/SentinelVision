"""SentinelVision Core: Unified Identity (Watchlist/Visitor/Event), Access Zones, Events & Incident Log.

Revision ID: 0006_sentinel_vision_core
Revises: 0005_phase4_kiosk_mfa_antispoof
Create Date: 2026-11-07
"""
from alembic import op

revision = "0006_sentinel_vision_core"
down_revision = "0005_phase4_kiosk_mfa_antispoof"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
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
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS sentinel_identity_company_type_idx
        ON sentinel_identity ("companyId", identity_type, status)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS sentinel_identity_embedding_hnsw_idx
        ON sentinel_identity
        USING hnsw (embedding vector_cosine_ops)
        """
    )
    op.execute(
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
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS sentinel_access_zone_company_idx
        ON sentinel_access_zone ("companyId", is_active)
        """
    )
    op.execute(
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
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS sentinel_event_company_idx
        ON sentinel_event ("companyId", status, start_at)
        """
    )
    op.execute(
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
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS sentinel_incident_company_occurred_idx
        ON sentinel_incident_log ("companyId", occurred_at DESC)
        """
    )


def downgrade() -> None:
    pass
