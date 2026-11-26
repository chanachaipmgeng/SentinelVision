"""SentinelVision Unified Biometric Identity, Access Control, Watchlist, Events & Incident Models."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from ..config.database import Base

FACE_EMBEDDING_DIM = 512


class SentinelIdentity(Base):
    """Non-employee or special-purpose biometric identity (BLACKLIST, POI, VIP, VISITOR, EVENT_ATTENDEE)."""

    __tablename__ = "sentinel_identity"

    identityId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    identityType: Mapped[str] = mapped_column("identity_type", String(30), nullable=False, default="VISITOR")
    fullName: Mapped[str] = mapped_column("full_name", String(160), nullable=False)
    documentRef: Mapped[str | None] = mapped_column("document_ref", String(100), nullable=True)
    phoneNumber: Mapped[str | None] = mapped_column("phone_number", String(50), nullable=True)
    email: Mapped[str | None] = mapped_column("email", String(150), nullable=True)
    organization: Mapped[str | None] = mapped_column("organization", String(150), nullable=True)
    severity: Mapped[str] = mapped_column("severity", String(20), nullable=False, default="LOW")
    alertNote: Mapped[str | None] = mapped_column("alert_note", Text, nullable=True)
    visitPurpose: Mapped[str | None] = mapped_column("visit_purpose", String(255), nullable=True)
    hostMemberId: Mapped[uuid.UUID | None] = mapped_column("host_member_id", UUID(as_uuid=True), nullable=True)
    seatNumber: Mapped[str | None] = mapped_column("seat_number", String(60), nullable=True)
    eventId: Mapped[uuid.UUID | None] = mapped_column("event_id", UUID(as_uuid=True), nullable=True)
    allowedZoneIds: Mapped[Any] = mapped_column("allowed_zone_ids", JSONB, nullable=False, default=list)
    pictureUrl: Mapped[str | None] = mapped_column("picture_url", String(255), nullable=True)
    embedding: Mapped[Any | None] = mapped_column(Vector(FACE_EMBEDDING_DIM), nullable=True)
    validFrom: Mapped[datetime] = mapped_column("valid_from", DateTime(timezone=True), server_default=func.now())
    expiresAt: Mapped[datetime | None] = mapped_column("expires_at", DateTime(timezone=True), nullable=True)
    consentAcceptedAt: Mapped[datetime | None] = mapped_column("consent_accepted_at", DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column("status", String(20), nullable=False, default="ACTIVE")
    createdAt: Mapped[datetime] = mapped_column("created_at", DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column("updated_at", DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now())
    deletedAt: Mapped[datetime | None] = mapped_column("deleted_at", DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("sentinel_identity_company_type_idx", "companyId", "identity_type", "status"),
        Index(
            "sentinel_identity_company_event_idx",
            "companyId",
            "event_id",
            postgresql_where=text("event_id IS NOT NULL"),
        ),
        Index(
            "sentinel_identity_embedding_hnsw_idx",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class SentinelAccessZone(Base):
    """Smart Access Control Zone / Door / Kiosk Station policy & IoT Relay configuration."""

    __tablename__ = "sentinel_access_zone"

    zoneId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(60), nullable=False, default="MAIN-GATE")
    locationId: Mapped[uuid.UUID | None] = mapped_column("location_id", UUID(as_uuid=True), nullable=True)
    siteFloorId: Mapped[uuid.UUID | None] = mapped_column(
        "site_floor_id",
        UUID(as_uuid=True),
        ForeignKey("site_floor.siteFloorId", ondelete="SET NULL"),
        nullable=True,
    )
    mapPosX: Mapped[float | None] = mapped_column("map_pos_x", Float, nullable=True)
    mapPosY: Mapped[float | None] = mapped_column("map_pos_y", Float, nullable=True)
    stationMode: Mapped[str] = mapped_column("station_mode", String(30), nullable=False, default="ACCESS_CONTROL")
    allowedDepartments: Mapped[Any] = mapped_column("allowed_departments", JSONB, nullable=False, default=list)
    allowedIdentityTypes: Mapped[Any] = mapped_column(
        "allowed_identity_types",
        JSONB,
        nullable=False,
        default=lambda: ["EMPLOYEE", "VIP", "VISITOR"],
    )
    scheduleStart: Mapped[str] = mapped_column("schedule_start", String(10), nullable=False, default="00:00")
    scheduleEnd: Mapped[str] = mapped_column("schedule_end", String(10), nullable=False, default="23:59")
    require2FA: Mapped[bool] = mapped_column("require_2fa", Boolean, nullable=False, default=False)
    relayWebhookUrl: Mapped[str | None] = mapped_column("relay_webhook_url", String(255), nullable=True)
    relaySecret: Mapped[str | None] = mapped_column("relay_secret", String(512), nullable=True)
    direction: Mapped[str] = mapped_column(
        "direction", String(20), nullable=False, default="BIDIRECTIONAL", server_default="BIDIRECTIONAL"
    )
    antiPassbackEnabled: Mapped[bool] = mapped_column(
        "anti_passback_enabled", Boolean, nullable=False, default=False, server_default="false"
    )
    antiPassbackMinutes: Mapped[int] = mapped_column(
        "anti_passback_minutes", Integer, nullable=False, default=15, server_default="15"
    )
    doorHeldMaxSeconds: Mapped[int] = mapped_column(
        "door_held_max_seconds", Integer, nullable=False, default=30, server_default="30"
    )
    doorOpenSince: Mapped[datetime | None] = mapped_column(
        "door_open_since", DateTime(timezone=True), nullable=True
    )
    edgeProtocol: Mapped[str] = mapped_column(
        "edge_protocol", String(20), nullable=False, default="WEBHOOK", server_default="WEBHOOK"
    )
    edgeBridgeUrl: Mapped[str | None] = mapped_column("edge_bridge_url", String(255), nullable=True)
    osdpAddress: Mapped[int] = mapped_column(
        "osdp_address", Integer, nullable=False, default=0, server_default="0"
    )
    isActive: Mapped[bool] = mapped_column("is_active", Boolean, nullable=False, default=True)
    createdAt: Mapped[datetime] = mapped_column("created_at", DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column("updated_at", DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now())
    deletedAt: Mapped[datetime | None] = mapped_column("deleted_at", DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("sentinel_access_zone_company_idx", "companyId", "is_active"),
        Index(
            "sentinel_access_zone_floor_idx",
            "companyId",
            "site_floor_id",
            postgresql_where=text("site_floor_id IS NOT NULL"),
        ),
    )


class SentinelEvent(Base):
    """Smart Event / Seminar / Conference campaign."""

    __tablename__ = "sentinel_event"

    eventId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    locationName: Mapped[str | None] = mapped_column("location_name", String(160), nullable=True)
    startAt: Mapped[datetime] = mapped_column("start_at", DateTime(timezone=True), nullable=False)
    endAt: Mapped[datetime] = mapped_column("end_at", DateTime(timezone=True), nullable=False)
    welcomeMessage: Mapped[str | None] = mapped_column("welcome_message", String(255), nullable=True)
    capacity: Mapped[int] = mapped_column("capacity", Integer, nullable=False, default=200)
    autoExpireDays: Mapped[int] = mapped_column("auto_expire_days", Integer, nullable=False, default=7)
    publicSlug: Mapped[str | None] = mapped_column("public_slug", String(100), nullable=True, unique=True, index=True)
    registrationOpen: Mapped[bool] = mapped_column("registration_open", Boolean, nullable=False, default=False, server_default="false")
    registrationDeadline: Mapped[datetime | None] = mapped_column("registration_deadline", DateTime(timezone=True), nullable=True)
    description: Mapped[str | None] = mapped_column("description", Text, nullable=True)
    status: Mapped[str] = mapped_column("status", String(20), nullable=False, default="LIVE")
    createdAt: Mapped[datetime] = mapped_column("created_at", DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column("updated_at", DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now())
    deletedAt: Mapped[datetime | None] = mapped_column("deleted_at", DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("sentinel_event_company_idx", "companyId", "status", "start_at"),)


class SentinelIncidentLog(Base):
    """Security, Watchlist, Access Control & Event Check-in Incident Log."""

    __tablename__ = "sentinel_incident_log"

    incidentId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    eventType: Mapped[str] = mapped_column("event_type", String(40), nullable=False)
    severity: Mapped[str] = mapped_column("severity", String(20), nullable=False, default="INFO")
    identityId: Mapped[uuid.UUID | None] = mapped_column("identity_id", UUID(as_uuid=True), nullable=True)
    memberId: Mapped[uuid.UUID | None] = mapped_column("member_id", UUID(as_uuid=True), nullable=True)
    subjectName: Mapped[str | None] = mapped_column("subject_name", String(160), nullable=True)
    identityType: Mapped[str | None] = mapped_column("identity_type", String(30), nullable=True)
    zoneId: Mapped[uuid.UUID | None] = mapped_column("zone_id", UUID(as_uuid=True), nullable=True)
    zoneName: Mapped[str | None] = mapped_column("zone_name", String(120), nullable=True)
    direction: Mapped[str | None] = mapped_column("direction", String(20), nullable=True)
    cameraId: Mapped[uuid.UUID | None] = mapped_column(
        "camera_id",
        UUID(as_uuid=True),
        ForeignKey("camera.cameraId", ondelete="SET NULL"),
        nullable=True,
    )
    eventId: Mapped[uuid.UUID | None] = mapped_column("event_id", UUID(as_uuid=True), nullable=True)
    confidencePercent: Mapped[float | None] = mapped_column("confidence_percent", Float, nullable=True)
    distance: Mapped[float | None] = mapped_column("distance", Float, nullable=True)
    snapshotUrl: Mapped[str | None] = mapped_column("snapshot_url", String(255), nullable=True)
    actionTaken: Mapped[str | None] = mapped_column("action_taken", String(255), nullable=True)
    status: Mapped[str] = mapped_column("status", String(20), nullable=False, default="OPEN", server_default="OPEN")
    acknowledgedBy: Mapped[uuid.UUID | None] = mapped_column("acknowledged_by", UUID(as_uuid=True), nullable=True)
    acknowledgedAt: Mapped[datetime | None] = mapped_column("acknowledged_at", DateTime(timezone=True), nullable=True)
    assignedTo: Mapped[uuid.UUID | None] = mapped_column("assigned_to", UUID(as_uuid=True), nullable=True)
    assignedAt: Mapped[datetime | None] = mapped_column("assigned_at", DateTime(timezone=True), nullable=True)
    closedBy: Mapped[uuid.UUID | None] = mapped_column("closed_by", UUID(as_uuid=True), nullable=True)
    closedAt: Mapped[datetime | None] = mapped_column("closed_at", DateTime(timezone=True), nullable=True)
    dedupeKey: Mapped[str | None] = mapped_column("dedupe_key", String(180), nullable=True)
    slaDueAt: Mapped[datetime | None] = mapped_column("sla_due_at", DateTime(timezone=True), nullable=True)
    occurredAt: Mapped[datetime] = mapped_column("occurred_at", DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("sentinel_incident_company_occurred_idx", "companyId", occurredAt.desc()),
        Index("sentinel_incident_dedupe_open_idx", "companyId", "dedupe_key", "status", occurredAt.desc()),
        Index(
            "sentinel_incident_company_camera_idx",
            "companyId",
            "camera_id",
            occurredAt.desc(),
        ),
        Index("sentinel_incident_company_hour_idx", "companyId", "occurred_at"),
        Index(
            "sentinel_incident_company_event_idx",
            "companyId",
            "event_id",
            "event_type",
            postgresql_where=text("event_id IS NOT NULL"),
        ),
        Index(
            "sentinel_incident_sla_due_idx",
            "companyId",
            "status",
            "sla_due_at",
            postgresql_where=text("sla_due_at IS NOT NULL"),
        ),
    )


class SentinelEventRegistration(Base):
    """Public or Self-Service Registration for Sentinel Events."""

    __tablename__ = "sentinel_event_registration"

    registrationId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    eventId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sentinel_event.eventId", ondelete="CASCADE"),
        nullable=False,
    )
    companyId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    identityId: Mapped[uuid.UUID | None] = mapped_column(
        "identity_id",
        UUID(as_uuid=True),
        ForeignKey("sentinel_identity.identityId", ondelete="SET NULL"),
        nullable=True,
    )
    fullName: Mapped[str] = mapped_column("full_name", String(160), nullable=False)
    email: Mapped[str] = mapped_column("email", String(160), nullable=False)
    phoneNumber: Mapped[str | None] = mapped_column("phone_number", String(50), nullable=True)
    organization: Mapped[str | None] = mapped_column("organization", String(160), nullable=True)
    status: Mapped[str] = mapped_column(
        "status", String(30), nullable=False, default="REGISTERED", server_default="REGISTERED"
    )
    consentAt: Mapped[datetime] = mapped_column("consent_at", DateTime(timezone=True), nullable=False)
    checkInAt: Mapped[datetime | None] = mapped_column("check_in_at", DateTime(timezone=True), nullable=True)
    createdAt: Mapped[datetime] = mapped_column("created_at", DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(
        "updated_at", DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now()
    )
    deletedAt: Mapped[datetime | None] = mapped_column("deleted_at", DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("sentinel_event_reg_event_idx", "eventId", "status"),
        Index("sentinel_event_reg_company_idx", "companyId", "email"),
    )


class SentinelVehicle(Base):
    """Registered vehicles for LPR, employee parking, VIPs, and visitor pass tracking."""

    __tablename__ = "sentinel_vehicle"

    vehicleId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    licensePlate: Mapped[str] = mapped_column("license_plate", String(50), nullable=False)
    province: Mapped[str | None] = mapped_column("province", String(100), nullable=True)
    vehicleType: Mapped[str] = mapped_column(
        "vehicle_type", String(30), nullable=False, default="CAR", server_default="CAR"
    )
    brand: Mapped[str | None] = mapped_column("brand", String(100), nullable=True)
    model: Mapped[str | None] = mapped_column("model", String(100), nullable=True)
    color: Mapped[str | None] = mapped_column("color", String(50), nullable=True)
    ownerType: Mapped[str] = mapped_column(
        "owner_type", String(30), nullable=False, default="EMPLOYEE", server_default="EMPLOYEE"
    )
    ownerName: Mapped[str | None] = mapped_column("owner_name", String(160), nullable=True)
    ownerContact: Mapped[str | None] = mapped_column("owner_contact", String(100), nullable=True)
    companyEmployeeId: Mapped[uuid.UUID | None] = mapped_column(
        "company_employee_id",
        UUID(as_uuid=True),
        ForeignKey("company_employee.company_employeeId", ondelete="SET NULL"),
        nullable=True,
    )
    identityId: Mapped[uuid.UUID | None] = mapped_column(
        "identity_id",
        UUID(as_uuid=True),
        ForeignKey("sentinel_identity.identityId", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        "status", String(30), nullable=False, default="ACTIVE", server_default="ACTIVE"
    )
    notes: Mapped[str | None] = mapped_column("notes", Text, nullable=True)
    createdAt: Mapped[datetime] = mapped_column("created_at", DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(
        "updated_at", DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now()
    )
    deletedAt: Mapped[datetime | None] = mapped_column("deleted_at", DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("sentinel_vehicle_company_plate_idx", "companyId", "license_plate"),
        Index("sentinel_vehicle_company_status_idx", "companyId", "status"),
    )


class SentinelParkingSpot(Base):
    """Physical parking spots with real-time occupancy status and zone allocation."""

    __tablename__ = "sentinel_parking_spot"

    spotId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    spotCode: Mapped[str] = mapped_column("spot_code", String(50), nullable=False)
    zone: Mapped[str] = mapped_column("zone", String(100), nullable=False)
    floor: Mapped[str | None] = mapped_column("floor", String(50), nullable=True)
    spotType: Mapped[str] = mapped_column(
        "spot_type", String(30), nullable=False, default="STANDARD", server_default="STANDARD"
    )
    isOccupied: Mapped[bool] = mapped_column(
        "is_occupied", Boolean, nullable=False, default=False, server_default=text("false")
    )
    occupiedVehicleId: Mapped[uuid.UUID | None] = mapped_column(
        "occupied_vehicle_id",
        UUID(as_uuid=True),
        ForeignKey("sentinel_vehicle.vehicleId", ondelete="SET NULL"),
        nullable=True,
    )
    occupiedPlate: Mapped[str | None] = mapped_column("occupied_plate", String(50), nullable=True)
    occupiedSince: Mapped[datetime | None] = mapped_column("occupied_since", DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        "status", String(30), nullable=False, default="AVAILABLE", server_default="AVAILABLE"
    )
    createdAt: Mapped[datetime] = mapped_column("created_at", DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(
        "updated_at", DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now()
    )
    deletedAt: Mapped[datetime | None] = mapped_column("deleted_at", DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("sentinel_parking_spot_company_code_idx", "companyId", "spot_code"),
        Index("sentinel_parking_spot_company_zone_idx", "companyId", "zone"),
        Index("sentinel_parking_spot_company_status_idx", "companyId", "status"),
    )


class SentinelParkingTransaction(Base):
    """LPR barrier scan transaction records, dwell time, and authorization logging."""

    __tablename__ = "sentinel_parking_transaction"

    transactionId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    vehicleId: Mapped[uuid.UUID | None] = mapped_column(
        "vehicle_id",
        UUID(as_uuid=True),
        ForeignKey("sentinel_vehicle.vehicleId", ondelete="SET NULL"),
        nullable=True,
    )
    spotId: Mapped[uuid.UUID | None] = mapped_column(
        "spot_id",
        UUID(as_uuid=True),
        ForeignKey("sentinel_parking_spot.spotId", ondelete="SET NULL"),
        nullable=True,
    )
    licensePlate: Mapped[str] = mapped_column("license_plate", String(50), nullable=False)
    province: Mapped[str | None] = mapped_column("province", String(100), nullable=True)
    entryTime: Mapped[datetime] = mapped_column("entry_time", DateTime(timezone=True), server_default=func.now())
    exitTime: Mapped[datetime | None] = mapped_column("exit_time", DateTime(timezone=True), nullable=True)
    dwellMinutes: Mapped[int | None] = mapped_column("dwell_minutes", Integer, nullable=True)
    gateIn: Mapped[str | None] = mapped_column("gate_in", String(100), nullable=True)
    gateOut: Mapped[str | None] = mapped_column("gate_out", String(100), nullable=True)
    entryConfidence: Mapped[float | None] = mapped_column("entry_confidence", Float, nullable=True)
    exitConfidence: Mapped[float | None] = mapped_column("exit_confidence", Float, nullable=True)
    entrySnapshotUrl: Mapped[str | None] = mapped_column("entry_snapshot_url", String(500), nullable=True)
    exitSnapshotUrl: Mapped[str | None] = mapped_column("exit_snapshot_url", String(500), nullable=True)
    authStatus: Mapped[str] = mapped_column(
        "auth_status", String(30), nullable=False, default="AUTHORIZED", server_default="AUTHORIZED"
    )
    actionTaken: Mapped[str] = mapped_column(
        "action_taken", String(50), nullable=False, default="BARRIER_OPEN", server_default="BARRIER_OPEN"
    )
    createdAt: Mapped[datetime] = mapped_column("created_at", DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("sentinel_parking_tx_company_plate_idx", "companyId", "license_plate"),
        Index("sentinel_parking_tx_company_entry_idx", "companyId", "entry_time"),
        Index("sentinel_parking_tx_company_status_idx", "companyId", "auth_status"),
    )


class SentinelRfidCard(Base):
    """Physical RFID cards (Mifare, HID, etc.) linked to employees or visitor passes."""

    __tablename__ = "sentinel_rfid_card"

    cardId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    cardNumber: Mapped[str] = mapped_column("card_number", String(100), nullable=False)
    facilityCode: Mapped[str | None] = mapped_column("facility_code", String(50), nullable=True)
    cardType: Mapped[str] = mapped_column(
        "card_type", String(30), nullable=False, default="MIFARE", server_default="MIFARE"
    )
    assignedType: Mapped[str] = mapped_column(
        "assigned_type", String(30), nullable=False, default="EMPLOYEE", server_default="EMPLOYEE"
    )
    companyEmployeeId: Mapped[uuid.UUID | None] = mapped_column(
        "company_employee_id",
        UUID(as_uuid=True),
        ForeignKey("company_employee.company_employeeId", ondelete="SET NULL"),
        nullable=True,
    )
    identityId: Mapped[uuid.UUID | None] = mapped_column(
        "identity_id",
        UUID(as_uuid=True),
        ForeignKey("sentinel_identity.identityId", ondelete="SET NULL"),
        nullable=True,
    )
    holderName: Mapped[str | None] = mapped_column("holder_name", String(160), nullable=True)
    cardStatus: Mapped[str] = mapped_column(
        "card_status", String(30), nullable=False, default="ACTIVE", server_default="ACTIVE"
    )
    issuedAt: Mapped[datetime] = mapped_column("issued_at", DateTime(timezone=True), server_default=func.now())
    expiresAt: Mapped[datetime | None] = mapped_column("expires_at", DateTime(timezone=True), nullable=True)
    lastSwipedAt: Mapped[datetime | None] = mapped_column("last_swiped_at", DateTime(timezone=True), nullable=True)
    lastDoor: Mapped[str | None] = mapped_column("last_door", String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column("notes", Text, nullable=True)
    createdAt: Mapped[datetime] = mapped_column("created_at", DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(
        "updated_at", DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now()
    )
    deletedAt: Mapped[datetime | None] = mapped_column("deleted_at", DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("sentinel_rfid_card_company_number_idx", "companyId", "card_number"),
        Index("sentinel_rfid_card_company_status_idx", "companyId", "card_status"),
    )


