"""Phase 3: camera table + cameras.read/manage RBAC.

Revision ID: 0020_camera_cctv
Revises: 0019_sentinel_relay_secret
Create Date: 2026-11-10
"""
from __future__ import annotations

from alembic import op

revision = "0020_camera_cctv"
down_revision = "0019_sentinel_relay_secret"
branch_labels = None
depends_on = None

_NEW_PERMS = (
    ("cameras.read", "View CCTV cameras and live wall"),
    ("cameras.manage", "Create / update / delete CCTV cameras"),
)


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS camera (
            "cameraId" UUID PRIMARY KEY,
            "companyId" UUID NOT NULL REFERENCES company("companyId") ON DELETE CASCADE,
            name VARCHAR(160) NOT NULL,
            stream_url TEXT NOT NULL,
            protocol VARCHAR(20) NOT NULL DEFAULT 'rtsp',
            description TEXT,
            credentials_enc TEXT,
            site_floor_id UUID,
            zone_id UUID,
            station_mode VARCHAR(30),
            map_pos_x DOUBLE PRECISION,
            map_pos_y DOUBLE PRECISION,
            record_mode VARCHAR(20) NOT NULL DEFAULT 'event',
            status VARCHAR(20) NOT NULL DEFAULT 'unknown',
            last_ping_at TIMESTAMPTZ,
            last_ping_latency_ms DOUBLE PRECISION,
            preview_image_url VARCHAR(255),
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ,
            deleted_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS camera_company_active_idx ON camera (\"companyId\", is_active)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS camera_company_status_idx ON camera (\"companyId\", status)"
    )

    for code, desc in _NEW_PERMS:
        op.execute(
            f"""
            INSERT INTO rbac_permission (code, description)
            VALUES ('{code}', '{desc}')
            ON CONFLICT (code) DO NOTHING
            """
        )

    # Grant to SYSTEM_ADMIN + HR_ADMIN (company admin mirror).
    for role in ("SYSTEM_ADMIN", "HR_ADMIN"):
        for code, _label in _NEW_PERMS:
            op.execute(
                f"""
                INSERT INTO rbac_role_permission (role_code, permission_code)
                SELECT '{role}', '{code}'
                WHERE EXISTS (SELECT 1 FROM rbac_role WHERE code = '{role}')
                  AND EXISTS (SELECT 1 FROM rbac_permission WHERE code = '{code}')
                ON CONFLICT DO NOTHING
                """
            )

    # DEVICE_OPERATOR + AUDITOR: read only
    for role in ("DEVICE_OPERATOR", "AUDITOR"):
        op.execute(
            f"""
            INSERT INTO rbac_role_permission (role_code, permission_code)
            SELECT '{role}', 'cameras.read'
            WHERE EXISTS (SELECT 1 FROM rbac_role WHERE code = '{role}')
              AND EXISTS (SELECT 1 FROM rbac_permission WHERE code = 'cameras.read')
            ON CONFLICT DO NOTHING
            """
        )


def downgrade() -> None:
    for role in ("SYSTEM_ADMIN", "HR_ADMIN", "DEVICE_OPERATOR", "AUDITOR"):
        for code, _label in _NEW_PERMS:
            op.execute(
                f"""
                DELETE FROM rbac_role_permission
                WHERE role_code = '{role}' AND permission_code = '{code}'
                """
            )
    for code, _label in _NEW_PERMS:
        op.execute(f"DELETE FROM rbac_permission WHERE code = '{code}'")
    op.execute("DROP TABLE IF EXISTS camera")
