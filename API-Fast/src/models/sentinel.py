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
    updatedAt: Mapped[datetime] = mapped_column("updated_at", DateTime(timezone=True), onupdate=func.now())
    deletedAt: Mapped[datetime | None] = mapped_column("deleted_at", DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("sentinel_identity_company_type_idx", "companyId", "identity_type", "status"),
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
    isActive: Mapped[bool] = mapped_column("is_active", Boolean, nullable=False, default=True)
    createdAt: Mapped[datetime] = mapped_column("created_at", DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column("updated_at", DateTime(timezone=True), onupdate=func.now())
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
    status: Mapped[str] = mapped_column("status", String(20), nullable=False, default="LIVE")
    createdAt: Mapped[datetime] = mapped_column("created_at", DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column("updated_at", DateTime(timezone=True), onupdate=func.now())
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
            "sentinel_incident_sla_due_idx",
            "companyId",
            "status",
            "sla_due_at",
            postgresql_where=text("sla_due_at IS NOT NULL"),
        ),
    )
