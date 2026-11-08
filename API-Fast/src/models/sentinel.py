"""SentinelVision Unified Biometric Identity, Access Control, Watchlist, Events & Incident Models."""
from __future__ import annotations

import uuid
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from ..config.database import Base

FACE_EMBEDDING_DIM = 512


class SentinelIdentity(Base):
    """Non-employee or special-purpose biometric identity (BLACKLIST, POI, VIP, VISITOR, EVENT_ATTENDEE)."""

    __tablename__ = "sentinel_identity"

    identityId = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId = Column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    identityType = Column("identity_type", String(30), nullable=False, default="VISITOR")
    fullName = Column("full_name", String(160), nullable=False)
    documentRef = Column("document_ref", String(100), nullable=True)
    phoneNumber = Column("phone_number", String(50), nullable=True)
    email = Column("email", String(150), nullable=True)
    organization = Column("organization", String(150), nullable=True)
    severity = Column("severity", String(20), nullable=False, default="LOW")
    alertNote = Column("alert_note", Text, nullable=True)
    visitPurpose = Column("visit_purpose", String(255), nullable=True)
    hostMemberId = Column("host_member_id", UUID(as_uuid=True), nullable=True)
    seatNumber = Column("seat_number", String(60), nullable=True)
    eventId = Column("event_id", UUID(as_uuid=True), nullable=True)
    allowedZoneIds = Column("allowed_zone_ids", JSONB, nullable=False, default=list)
    pictureUrl = Column("picture_url", String(255), nullable=True)
    embedding = Column(Vector(FACE_EMBEDDING_DIM), nullable=True)
    validFrom = Column("valid_from", DateTime(timezone=True), server_default=func.now())
    expiresAt = Column("expires_at", DateTime(timezone=True), nullable=True)
    consentAcceptedAt = Column("consent_accepted_at", DateTime(timezone=True), nullable=True)
    status = Column("status", String(20), nullable=False, default="ACTIVE")
    createdAt = Column("created_at", DateTime(timezone=True), server_default=func.now())
    updatedAt = Column("updated_at", DateTime(timezone=True), onupdate=func.now())
    deletedAt = Column("deleted_at", DateTime(timezone=True), nullable=True)

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

    zoneId = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId = Column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(120), nullable=False)
    code = Column(String(60), nullable=False, default="MAIN-GATE")
    locationId = Column("location_id", UUID(as_uuid=True), nullable=True)
    stationMode = Column("station_mode", String(30), nullable=False, default="ACCESS_CONTROL")
    allowedDepartments = Column("allowed_departments", JSONB, nullable=False, default=list)
    allowedIdentityTypes = Column(
        "allowed_identity_types",
        JSONB,
        nullable=False,
        default=lambda: ["EMPLOYEE", "VIP", "VISITOR"],
    )
    scheduleStart = Column("schedule_start", String(10), nullable=False, default="00:00")
    scheduleEnd = Column("schedule_end", String(10), nullable=False, default="23:59")
    require2FA = Column("require_2fa", Boolean, nullable=False, default=False)
    relayWebhookUrl = Column("relay_webhook_url", String(255), nullable=True)
    # Widened for Fernet-sealed values (`fernet:` + token); see Alembic 0019.
    relaySecret = Column("relay_secret", String(512), nullable=True)
    isActive = Column("is_active", Boolean, nullable=False, default=True)
    createdAt = Column("created_at", DateTime(timezone=True), server_default=func.now())
    updatedAt = Column("updated_at", DateTime(timezone=True), onupdate=func.now())
    deletedAt = Column("deleted_at", DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("sentinel_access_zone_company_idx", "companyId", "is_active"),)


class SentinelEvent(Base):
    """Smart Event / Seminar / Conference campaign."""

    __tablename__ = "sentinel_event"

    eventId = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId = Column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(160), nullable=False)
    locationName = Column("location_name", String(160), nullable=True)
    startAt = Column("start_at", DateTime(timezone=True), nullable=False)
    endAt = Column("end_at", DateTime(timezone=True), nullable=False)
    welcomeMessage = Column("welcome_message", String(255), nullable=True)
    capacity = Column("capacity", Integer, nullable=False, default=200)
    autoExpireDays = Column("auto_expire_days", Integer, nullable=False, default=7)
    status = Column("status", String(20), nullable=False, default="LIVE")
    createdAt = Column("created_at", DateTime(timezone=True), server_default=func.now())
    updatedAt = Column("updated_at", DateTime(timezone=True), onupdate=func.now())
    deletedAt = Column("deleted_at", DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("sentinel_event_company_idx", "companyId", "status", "start_at"),)


class SentinelIncidentLog(Base):
    """Security, Watchlist, Access Control & Event Check-in Incident Log."""

    __tablename__ = "sentinel_incident_log"

    incidentId = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyId = Column(
        UUID(as_uuid=True),
        ForeignKey("company.companyId", ondelete="CASCADE"),
        nullable=False,
    )
    eventType = Column("event_type", String(40), nullable=False)
    severity = Column("severity", String(20), nullable=False, default="INFO")
    identityId = Column("identity_id", UUID(as_uuid=True), nullable=True)
    memberId = Column("member_id", UUID(as_uuid=True), nullable=True)
    subjectName = Column("subject_name", String(160), nullable=True)
    identityType = Column("identity_type", String(30), nullable=True)
    zoneId = Column("zone_id", UUID(as_uuid=True), nullable=True)
    zoneName = Column("zone_name", String(120), nullable=True)
    eventId = Column("event_id", UUID(as_uuid=True), nullable=True)
    confidencePercent = Column("confidence_percent", Float, nullable=True)
    distance = Column("distance", Float, nullable=True)
    snapshotUrl = Column("snapshot_url", String(255), nullable=True)
    actionTaken = Column("action_taken", String(255), nullable=True)
    status = Column("status", String(20), nullable=False, default="OPEN", server_default="OPEN")
    acknowledgedBy = Column("acknowledged_by", UUID(as_uuid=True), nullable=True)
    acknowledgedAt = Column("acknowledged_at", DateTime(timezone=True), nullable=True)
    assignedTo = Column("assigned_to", UUID(as_uuid=True), nullable=True)
    assignedAt = Column("assigned_at", DateTime(timezone=True), nullable=True)
    closedBy = Column("closed_by", UUID(as_uuid=True), nullable=True)
    closedAt = Column("closed_at", DateTime(timezone=True), nullable=True)
    dedupeKey = Column("dedupe_key", String(180), nullable=True)
    occurredAt = Column("occurred_at", DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("sentinel_incident_company_occurred_idx", "companyId", occurredAt.desc()),
        Index("sentinel_incident_dedupe_open_idx", "companyId", "dedupe_key", "status", occurredAt.desc()),
    )
