"""P3: Vehicle LPR, Smart Parking, and RFID Card Management.

Revision ID: 0037_vehicle_parking_rfid
Revises: 0036_event_public_registration
Create Date: 2026-11-21
"""
from __future__ import annotations

from alembic import op

revision = "0037_vehicle_parking_rfid"
down_revision = "0036_event_public_registration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS sentinel_vehicle (
            "vehicleId" UUID PRIMARY KEY,
            "companyId" UUID NOT NULL REFERENCES company("companyId") ON DELETE CASCADE,
            license_plate VARCHAR(50) NOT NULL,
            province VARCHAR(100),
            vehicle_type VARCHAR(30) NOT NULL DEFAULT 'CAR',
            brand VARCHAR(100),
            model VARCHAR(100),
            color VARCHAR(50),
            owner_type VARCHAR(30) NOT NULL DEFAULT 'EMPLOYEE',
            owner_name VARCHAR(160),
            owner_contact VARCHAR(100),
            company_employee_id UUID REFERENCES company_employee("company_employeeId") ON DELETE SET NULL,
            identity_id UUID REFERENCES sentinel_identity("identityId") ON DELETE SET NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMPTZ
        );

        CREATE INDEX IF NOT EXISTS sentinel_vehicle_company_plate_idx
            ON sentinel_vehicle("companyId", license_plate);

        CREATE INDEX IF NOT EXISTS sentinel_vehicle_company_status_idx
            ON sentinel_vehicle("companyId", status);

        CREATE TABLE IF NOT EXISTS sentinel_parking_spot (
            "spotId" UUID PRIMARY KEY,
            "companyId" UUID NOT NULL REFERENCES company("companyId") ON DELETE CASCADE,
            spot_code VARCHAR(50) NOT NULL,
            zone VARCHAR(100) NOT NULL,
            floor VARCHAR(50),
            spot_type VARCHAR(30) NOT NULL DEFAULT 'STANDARD',
            is_occupied BOOLEAN NOT NULL DEFAULT false,
            occupied_vehicle_id UUID REFERENCES sentinel_vehicle("vehicleId") ON DELETE SET NULL,
            occupied_plate VARCHAR(50),
            occupied_since TIMESTAMPTZ,
            status VARCHAR(30) NOT NULL DEFAULT 'AVAILABLE',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMPTZ
        );

        CREATE INDEX IF NOT EXISTS sentinel_parking_spot_company_code_idx
            ON sentinel_parking_spot("companyId", spot_code);

        CREATE INDEX IF NOT EXISTS sentinel_parking_spot_company_zone_idx
            ON sentinel_parking_spot("companyId", zone);

        CREATE INDEX IF NOT EXISTS sentinel_parking_spot_company_status_idx
            ON sentinel_parking_spot("companyId", status);

        CREATE TABLE IF NOT EXISTS sentinel_parking_transaction (
            "transactionId" UUID PRIMARY KEY,
            "companyId" UUID NOT NULL REFERENCES company("companyId") ON DELETE CASCADE,
            vehicle_id UUID REFERENCES sentinel_vehicle("vehicleId") ON DELETE SET NULL,
            spot_id UUID REFERENCES sentinel_parking_spot("spotId") ON DELETE SET NULL,
            license_plate VARCHAR(50) NOT NULL,
            province VARCHAR(100),
            entry_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            exit_time TIMESTAMPTZ,
            dwell_minutes INTEGER,
            gate_in VARCHAR(100),
            gate_out VARCHAR(100),
            entry_confidence DOUBLE PRECISION,
            exit_confidence DOUBLE PRECISION,
            entry_snapshot_url VARCHAR(500),
            exit_snapshot_url VARCHAR(500),
            auth_status VARCHAR(30) NOT NULL DEFAULT 'AUTHORIZED',
            action_taken VARCHAR(50) NOT NULL DEFAULT 'BARRIER_OPEN',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS sentinel_parking_tx_company_plate_idx
            ON sentinel_parking_transaction("companyId", license_plate);

        CREATE INDEX IF NOT EXISTS sentinel_parking_tx_company_entry_idx
            ON sentinel_parking_transaction("companyId", entry_time);

        CREATE INDEX IF NOT EXISTS sentinel_parking_tx_company_status_idx
            ON sentinel_parking_transaction("companyId", auth_status);

        CREATE TABLE IF NOT EXISTS sentinel_rfid_card (
            "cardId" UUID PRIMARY KEY,
            "companyId" UUID NOT NULL REFERENCES company("companyId") ON DELETE CASCADE,
            card_number VARCHAR(100) NOT NULL,
            facility_code VARCHAR(50),
            card_type VARCHAR(30) NOT NULL DEFAULT 'MIFARE',
            assigned_type VARCHAR(30) NOT NULL DEFAULT 'EMPLOYEE',
            company_employee_id UUID REFERENCES company_employee("company_employeeId") ON DELETE SET NULL,
            identity_id UUID REFERENCES sentinel_identity("identityId") ON DELETE SET NULL,
            holder_name VARCHAR(160),
            card_status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
            issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            expires_at TIMESTAMPTZ,
            last_swiped_at TIMESTAMPTZ,
            last_door VARCHAR(100),
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMPTZ
        );

        CREATE INDEX IF NOT EXISTS sentinel_rfid_card_company_number_idx
            ON sentinel_rfid_card("companyId", card_number);

        CREATE INDEX IF NOT EXISTS sentinel_rfid_card_company_status_idx
            ON sentinel_rfid_card("companyId", card_status);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS sentinel_rfid_card;
        DROP TABLE IF EXISTS sentinel_parking_transaction;
        DROP TABLE IF EXISTS sentinel_parking_spot;
        DROP TABLE IF EXISTS sentinel_vehicle;
        """
    )
