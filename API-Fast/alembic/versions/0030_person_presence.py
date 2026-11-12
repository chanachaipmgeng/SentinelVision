"""Person presence sightings and sessions for CCTV locate trail.

Revision ID: 0030_person_presence
Revises: 0029_mapped_not_null
Create Date: 2026-11-12
"""
from __future__ import annotations

from alembic import op

revision = "0030_person_presence"
down_revision = "0029_mapped_not_null"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS person_sighting (
            "sightingId" UUID PRIMARY KEY,
            "companyId" UUID NOT NULL
                REFERENCES company("companyId") ON DELETE CASCADE,
            "memberId" UUID NOT NULL
                REFERENCES member("memberId") ON DELETE CASCADE,
            "cameraId" UUID NOT NULL
                REFERENCES camera("cameraId") ON DELETE CASCADE,
            "zoneId" UUID,
            site_floor_id UUID
                REFERENCES site_floor("siteFloorId") ON DELETE SET NULL,
            event_id UUID
                REFERENCES sentinel_event("eventId") ON DELETE SET NULL,
            seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            distance DOUBLE PRECISION,
            confidence DOUBLE PRECISION
        )
        """
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS person_sighting_company_member_seen_idx '
        'ON person_sighting ("companyId", "memberId", seen_at DESC)'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS person_sighting_company_camera_seen_idx '
        'ON person_sighting ("companyId", "cameraId", seen_at DESC)'
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS person_sighting_seen_idx ON person_sighting (seen_at)"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS person_presence_session (
            "sessionId" UUID PRIMARY KEY,
            "companyId" UUID NOT NULL
                REFERENCES company("companyId") ON DELETE CASCADE,
            "memberId" UUID NOT NULL
                REFERENCES member("memberId") ON DELETE CASCADE,
            "cameraId" UUID NOT NULL
                REFERENCES camera("cameraId") ON DELETE CASCADE,
            "zoneId" UUID,
            site_floor_id UUID
                REFERENCES site_floor("siteFloorId") ON DELETE SET NULL,
            event_id UUID
                REFERENCES sentinel_event("eventId") ON DELETE SET NULL,
            presence_role VARCHAR(20) NOT NULL DEFAULT 'LOCATE',
            started_at TIMESTAMPTZ NOT NULL,
            ended_at TIMESTAMPTZ,
            last_seen_at TIMESTAMPTZ NOT NULL,
            sample_count INTEGER NOT NULL DEFAULT 1,
            is_open BOOLEAN NOT NULL DEFAULT true
        )
        """
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS person_presence_session_company_member_idx '
        'ON person_presence_session ("companyId", "memberId", last_seen_at)'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS person_presence_session_company_camera_idx '
        'ON person_presence_session ("companyId", "cameraId", last_seen_at)'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS person_presence_session_open_idx '
        'ON person_presence_session ("companyId", "memberId", is_open) '
        'WHERE is_open = true'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS person_presence_session_event_idx '
        'ON person_presence_session ("companyId", event_id, started_at) '
        'WHERE event_id IS NOT NULL'
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS person_presence_session_event_idx")
    op.execute("DROP INDEX IF EXISTS person_presence_session_open_idx")
    op.execute("DROP INDEX IF EXISTS person_presence_session_company_camera_idx")
    op.execute("DROP INDEX IF EXISTS person_presence_session_company_member_idx")
    op.execute("DROP TABLE IF EXISTS person_presence_session")
    op.execute("DROP INDEX IF EXISTS person_sighting_seen_idx")
    op.execute("DROP INDEX IF EXISTS person_sighting_company_camera_seen_idx")
    op.execute("DROP INDEX IF EXISTS person_sighting_company_member_seen_idx")
    op.execute("DROP TABLE IF EXISTS person_sighting")
