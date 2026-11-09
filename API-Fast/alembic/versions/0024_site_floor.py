"""Phase 2: site_floor + pin FK/columns for camera, zone, kiosk.

Revision ID: 0024_site_floor
Revises: 0023_incident_sla
Create Date: 2026-11-09
"""
from __future__ import annotations

from alembic import op

revision = "0024_site_floor"
down_revision = "0023_incident_sla"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS site_floor (
            "siteFloorId" UUID PRIMARY KEY,
            "companyId" UUID NOT NULL REFERENCES company("companyId") ON DELETE CASCADE,
            name VARCHAR(160) NOT NULL,
            building_label VARCHAR(120),
            floor_label VARCHAR(60),
            plan_image_key VARCHAR(255),
            width_px INTEGER,
            height_px INTEGER,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ,
            deleted_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS site_floor_company_sort_idx
        ON site_floor ("companyId", sort_order)
        """
    )

    # Wire dangling camera.site_floor_id → site_floor (nullable SET NULL on delete).
    op.execute(
        """
        DO $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'camera_site_floor_id_fkey'
          ) THEN
            ALTER TABLE camera
              ADD CONSTRAINT camera_site_floor_id_fkey
              FOREIGN KEY (site_floor_id) REFERENCES site_floor("siteFloorId")
              ON DELETE SET NULL;
          END IF;
        END $$
        """
    )

    op.execute(
        """
        ALTER TABLE sentinel_access_zone
          ADD COLUMN IF NOT EXISTS site_floor_id UUID
            REFERENCES site_floor("siteFloorId") ON DELETE SET NULL
        """
    )
    op.execute(
        "ALTER TABLE sentinel_access_zone ADD COLUMN IF NOT EXISTS map_pos_x DOUBLE PRECISION"
    )
    op.execute(
        "ALTER TABLE sentinel_access_zone ADD COLUMN IF NOT EXISTS map_pos_y DOUBLE PRECISION"
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS sentinel_access_zone_floor_idx
        ON sentinel_access_zone ("companyId", site_floor_id)
        WHERE site_floor_id IS NOT NULL
        """
    )

    op.execute(
        """
        ALTER TABLE kiosk_device
          ADD COLUMN IF NOT EXISTS site_floor_id UUID
            REFERENCES site_floor("siteFloorId") ON DELETE SET NULL
        """
    )
    op.execute(
        "ALTER TABLE kiosk_device ADD COLUMN IF NOT EXISTS map_pos_x DOUBLE PRECISION"
    )
    op.execute(
        "ALTER TABLE kiosk_device ADD COLUMN IF NOT EXISTS map_pos_y DOUBLE PRECISION"
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS kiosk_device_floor_idx
        ON kiosk_device ("companyId", site_floor_id)
        WHERE site_floor_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS kiosk_device_floor_idx")
    op.execute("ALTER TABLE kiosk_device DROP COLUMN IF EXISTS map_pos_y")
    op.execute("ALTER TABLE kiosk_device DROP COLUMN IF EXISTS map_pos_x")
    op.execute("ALTER TABLE kiosk_device DROP COLUMN IF EXISTS site_floor_id")

    op.execute("DROP INDEX IF EXISTS sentinel_access_zone_floor_idx")
    op.execute("ALTER TABLE sentinel_access_zone DROP COLUMN IF EXISTS map_pos_y")
    op.execute("ALTER TABLE sentinel_access_zone DROP COLUMN IF EXISTS map_pos_x")
    op.execute("ALTER TABLE sentinel_access_zone DROP COLUMN IF EXISTS site_floor_id")

    op.execute(
        """
        ALTER TABLE camera DROP CONSTRAINT IF EXISTS camera_site_floor_id_fkey
        """
    )
    op.execute("DROP INDEX IF EXISTS site_floor_company_sort_idx")
    op.execute("DROP TABLE IF EXISTS site_floor")
