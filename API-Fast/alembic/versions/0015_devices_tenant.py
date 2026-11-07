"""D2 devices + D5 tenant lifecycle/quotas.

Revision ID: 0015_devices_tenant
Revises: 0014_rbac
Create Date: 2026-11-07

Owned by branch ``feat/phase-d-devices-tenant``.
Idempotent DDL (IF NOT EXISTS / ADD COLUMN IF NOT EXISTS).
"""
from __future__ import annotations

from alembic import op

revision = "0015_devices_tenant"
down_revision = "0014_rbac"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- D2: expand kiosk_device -----------------------------------------------
    op.execute(
        """
        ALTER TABLE kiosk_device
          ADD COLUMN IF NOT EXISTS fingerprint VARCHAR(255),
          ADD COLUMN IF NOT EXISTS app_version VARCHAR(64),
          ADD COLUMN IF NOT EXISTS location_label VARCHAR(255),
          ADD COLUMN IF NOT EXISTS heartbeat_at TIMESTAMPTZ,
          ADD COLUMN IF NOT EXISTS config JSONB NOT NULL DEFAULT '{}'::jsonb,
          ADD COLUMN IF NOT EXISTS station_mode VARCHAR(40),
          ADD COLUMN IF NOT EXISTS zone_id UUID
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS kiosk_device_station_mode_idx
        ON kiosk_device ("companyId", station_mode)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS kiosk_device_zone_idx
        ON kiosk_device ("companyId", zone_id)
        WHERE zone_id IS NOT NULL
        """
    )

    # --- D5: tenant lifecycle + quotas on company ------------------------------
    op.execute(
        """
        ALTER TABLE company
          ADD COLUMN IF NOT EXISTS lifecycle_status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
          ADD COLUMN IF NOT EXISTS suspended_at TIMESTAMPTZ,
          ADD COLUMN IF NOT EXISTS offboarded_at TIMESTAMPTZ,
          ADD COLUMN IF NOT EXISTS max_devices INTEGER,
          ADD COLUMN IF NOT EXISTS max_employees INTEGER,
          ADD COLUMN IF NOT EXISTS gpu_priority INTEGER NOT NULL DEFAULT 0,
          ADD COLUMN IF NOT EXISTS package_code VARCHAR(64)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS company_lifecycle_idx
        ON company (lifecycle_status)
        WHERE deleted_at IS NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS company_lifecycle_idx")
    op.execute("ALTER TABLE company DROP COLUMN IF EXISTS package_code")
    op.execute("ALTER TABLE company DROP COLUMN IF EXISTS gpu_priority")
    op.execute("ALTER TABLE company DROP COLUMN IF EXISTS max_employees")
    op.execute("ALTER TABLE company DROP COLUMN IF EXISTS max_devices")
    op.execute("ALTER TABLE company DROP COLUMN IF EXISTS offboarded_at")
    op.execute("ALTER TABLE company DROP COLUMN IF EXISTS suspended_at")
    op.execute("ALTER TABLE company DROP COLUMN IF EXISTS lifecycle_status")

    op.execute("DROP INDEX IF EXISTS kiosk_device_zone_idx")
    op.execute("DROP INDEX IF EXISTS kiosk_device_station_mode_idx")
    op.execute("ALTER TABLE kiosk_device DROP COLUMN IF EXISTS zone_id")
    op.execute("ALTER TABLE kiosk_device DROP COLUMN IF EXISTS station_mode")
    op.execute("ALTER TABLE kiosk_device DROP COLUMN IF EXISTS config")
    op.execute("ALTER TABLE kiosk_device DROP COLUMN IF EXISTS heartbeat_at")
    op.execute("ALTER TABLE kiosk_device DROP COLUMN IF EXISTS location_label")
    op.execute("ALTER TABLE kiosk_device DROP COLUMN IF EXISTS app_version")
    op.execute("ALTER TABLE kiosk_device DROP COLUMN IF EXISTS fingerprint")
