"""D4 PDPA helpers — consent policy, DSAR export, erasure, per-type retention."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config.settings import settings
from ..models.company_employee import CompanyEmployee
from ..models.employee_timestamp import EmployeeTimestamp
from ..models.face_encoding import FaceEncoding
from ..models.member import Member
from ..models.sentinel import SentinelIncidentLog
from ..models.system_setting import SystemSetting
from .storage_service import delete_stored_image

logger = logging.getLogger("dpu.pdpa")

DEFAULT_CONSENT_VERSION = "1.0"
DEFAULT_CONSENT_TEXT_TH = (
    "ข้าพเจ้ายินยอมให้บริษัทเก็บและใช้ข้อมูลชีวภาพ (ใบหน้า) "
    "เพื่อการลงเวลาทำงานและรักษาความปลอดภัยตามนโยบายความเป็นส่วนตัวของบริษัท"
)
DEFAULT_CONSENT_TEXT_EN = (
    "I consent to the company collecting and using my biometric (face) data "
    "for attendance and security purposes under the company privacy policy."
)


def _consent_key(company_id: str) -> str:
    return f"pdpa_consent:{company_id}"


def _retention_key(company_id: str) -> str:
    return f"retention:{company_id}"


def default_retention() -> dict[str, int]:
    return {
        "biometricDays": int(getattr(settings, "IMAGE_RETENTION_DAYS", 90) or 90),
        "punchPhotoDays": int(getattr(settings, "IMAGE_RETENTION_DAYS", 90) or 90),
        "incidentSnapshotDays": int(getattr(settings, "IMAGE_RETENTION_DAYS", 90) or 90),
        # Separate from punch-photo / incident stills (Phase 4B).
        "videoClipDays": int(getattr(settings, "VIDEO_CLIP_RETENTION_DAYS", 30) or 30),
        "tempHours": int(getattr(settings, "TEMP_RETENTION_HOURS", 24) or 24),
    }


async def get_consent_policy(db: AsyncSession, company_id: UUID | str) -> dict[str, Any]:
    row = await db.get(SystemSetting, _consent_key(str(company_id)))
    val = row.value if (row and isinstance(row.value, dict)) else {}
    return {
        "version": str(val.get("version") or DEFAULT_CONSENT_VERSION),
        "textTh": str(val.get("textTh") or DEFAULT_CONSENT_TEXT_TH),
        "textEn": str(val.get("textEn") or DEFAULT_CONSENT_TEXT_EN),
        "updatedAt": val.get("updatedAt"),
    }


async def put_consent_policy(
    db: AsyncSession, company_id: UUID | str, body: dict[str, Any]
) -> dict[str, Any]:
    key = _consent_key(str(company_id))
    row = await db.get(SystemSetting, key)
    value = {
        "version": str((body or {}).get("version") or DEFAULT_CONSENT_VERSION).strip()[:40],
        "textTh": str((body or {}).get("textTh") or DEFAULT_CONSENT_TEXT_TH),
        "textEn": str((body or {}).get("textEn") or DEFAULT_CONSENT_TEXT_EN),
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }
    if row:
        row.value = value
    else:
        db.add(SystemSetting(key=key, value=value))
    await db.commit()
    return value


async def get_retention_settings(db: AsyncSession, company_id: UUID | str) -> dict[str, int]:
    row = await db.get(SystemSetting, _retention_key(str(company_id)))
    base = default_retention()
    if row and isinstance(row.value, dict):
        for k in base:
            if k in row.value:
                try:
                    base[k] = max(0, int(row.value[k]))
                except (TypeError, ValueError):
                    pass
    return base


async def put_retention_settings(
    db: AsyncSession, company_id: UUID | str, body: dict[str, Any]
) -> dict[str, int]:
    key = _retention_key(str(company_id))
    current = await get_retention_settings(db, company_id)
    for k in current:
        if k in (body or {}):
            try:
                current[k] = max(0, int(body[k]))
            except (TypeError, ValueError):
                pass
    row = await db.get(SystemSetting, key)
    if row:
        row.value = current
    else:
        db.add(SystemSetting(key=key, value=current))
    await db.commit()
    return current


async def record_biometric_consent(
    db: AsyncSession,
    member: Member,
    company_id: UUID | str,
    *,
    locale: str = "th",
) -> dict[str, Any]:
    policy = await get_consent_policy(db, company_id)
    text = policy["textTh"] if (locale or "th").lower().startswith("th") else policy["textEn"]
    member.biometricConsentAt = datetime.now(timezone.utc)
    member.biometricConsentVersion = policy["version"]
    member.biometricConsentText = text
    await db.commit()
    return {
        "memberId": str(member.memberId),
        "biometricConsentAt": member.biometricConsentAt,
        "biometricConsentVersion": member.biometricConsentVersion,
        "hasConsent": True,
    }


async def build_dsar_export(
    db: AsyncSession, company_id: UUID, member_id: UUID
) -> dict[str, Any]:
    """Subject-access package for one member within a company (no raw embeddings)."""
    member = await db.get(Member, member_id)
    if not member or getattr(member, "deletedAt", None) is not None:
        return {"error": "member_not_found"}

    emp_rows = (
        await db.execute(
            select(CompanyEmployee)
            .options(selectinload(CompanyEmployee.department), selectinload(CompanyEmployee.position))
            .where(
                CompanyEmployee.companyId == company_id,
                CompanyEmployee.memberId == member_id,
                CompanyEmployee.deletedAt.is_(None),
            )
        )
    ).scalars().all()

    emp_ids = [e.company_employeeId for e in emp_rows]
    timestamps: list[EmployeeTimestamp] = []
    if emp_ids:
        timestamps = (
            await db.execute(
                select(EmployeeTimestamp)
                .where(
                    EmployeeTimestamp.companyId == company_id,
                    EmployeeTimestamp.company_employeeId.in_(emp_ids),
                )
                .order_by(EmployeeTimestamp.timestamp.desc())
                .limit(5000)
            )
        ).scalars().all()

    encodings = (
        await db.execute(
            select(FaceEncoding).where(
                FaceEncoding.memberId == member_id,
                FaceEncoding.companyId == company_id,
            )
        )
    ).scalars().all()

    incidents = (
        await db.execute(
            select(SentinelIncidentLog)
            .where(
                SentinelIncidentLog.companyId == company_id,
                SentinelIncidentLog.memberId == member_id,
            )
            .order_by(SentinelIncidentLog.occurredAt.desc())
            .limit(1000)
        )
    ).scalars().all()

    return {
        "exportedAt": datetime.now(timezone.utc).isoformat(),
        "companyId": str(company_id),
        "member": {
            "memberId": str(member.memberId),
            "username": member.username,
            "email": member.email,
            "firstName": member.firstName,
            "lastName": member.lastName,
            "phoneNumber": member.phoneNumber,
            "birthDate": member.birthDate.isoformat() if member.birthDate else None,
            "address": member.address,
            "biometricConsentAt": (
                member.biometricConsentAt.isoformat() if member.biometricConsentAt else None
            ),
            "biometricConsentVersion": getattr(member, "biometricConsentVersion", None),
            "biometricConsentText": getattr(member, "biometricConsentText", None),
        },
        "employment": [
            {
                "companyEmployeeId": str(e.company_employeeId),
                "employeeId": e.employeeId,
                "department": (e.department.thName if e.department else None),
                "position": (e.position.thName if e.position else None),
            }
            for e in emp_rows
        ],
        "faceEncodings": [
            {
                "faceEncodingId": str(enc.faceEncodingId),
                "companyId": str(enc.companyId) if enc.companyId else None,
                "createdAt": enc.createdAt.isoformat() if getattr(enc, "createdAt", None) else None,
                "embeddingPresent": True,
            }
            for enc in encodings
        ],
        "timestamps": [
            {
                "timestampId": str(t.timestampId),
                "timestamp": t.timestamp.isoformat() if t.timestamp else None,
                "timestampType": int(t.timestampType.value) if t.timestampType else None,
                "locationName": t.locationName,
                "photoTimestamp": t.photoTimestamp,
                "note": t.note,
            }
            for t in timestamps
        ],
        "incidents": [
            {
                "incidentId": str(i.incidentId),
                "eventType": i.eventType,
                "severity": i.severity,
                "occurredAt": i.occurredAt.isoformat() if i.occurredAt else None,
                "snapshotUrl": i.snapshotUrl,
                "zoneName": i.zoneName,
            }
            for i in incidents
        ],
    }


def _filename_from_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    name = Path(str(url).split("?")[0]).name
    return name or None


async def erase_member_personal_data(
    db: AsyncSession,
    company_id: UUID,
    member_id: UUID,
    *,
    clear_consent: bool = True,
) -> dict[str, Any]:
    """Right-to-erasure for punch photos, face encodings, and incident snapshots."""
    from ..controllers.face_controller import clear_member_face_encodings

    photos_removed = 0
    snapshots_removed = 0
    timestamps_cleared = 0
    incidents_cleared = 0

    emp_ids = [
        r[0]
        for r in (
            await db.execute(
                select(CompanyEmployee.company_employeeId).where(
                    CompanyEmployee.companyId == company_id,
                    CompanyEmployee.memberId == member_id,
                )
            )
        ).all()
    ]

    if emp_ids:
        ts_rows = (
            await db.execute(
                select(EmployeeTimestamp).where(
                    EmployeeTimestamp.companyId == company_id,
                    EmployeeTimestamp.company_employeeId.in_(emp_ids),
                    EmployeeTimestamp.photoTimestamp.isnot(None),
                )
            )
        ).scalars().all()
        for ts in ts_rows:
            fname = _filename_from_url(ts.photoTimestamp)
            if fname and delete_stored_image("uploaded_images", fname):
                photos_removed += 1
            ts.photoTimestamp = None
            timestamps_cleared += 1

    incidents = (
        await db.execute(
            select(SentinelIncidentLog).where(
                SentinelIncidentLog.companyId == company_id,
                SentinelIncidentLog.memberId == member_id,
                SentinelIncidentLog.snapshotUrl.isnot(None),
            )
        )
    ).scalars().all()
    for inc in incidents:
        fname = _filename_from_url(inc.snapshotUrl)
        if fname:
            # Sentinel stores under uploaded_images or as /images/<name>
            if delete_stored_image("uploaded_images", fname) or delete_stored_image(
                "temp_images", fname
            ):
                snapshots_removed += 1
        inc.snapshotUrl = None
        inc.subjectName = None
        incidents_cleared += 1

    cleared = await clear_member_face_encodings(member_id, db)

    member = await db.get(Member, member_id)
    if member and clear_consent:
        member.biometricConsentAt = None
        member.biometricConsentVersion = None
        member.biometricConsentText = None

    await db.commit()
    return {
        "memberId": str(member_id),
        "companyId": str(company_id),
        "deletedEncodings": int(cleared.get("deleted", 0)) if isinstance(cleared, dict) else 0,
        "punchPhotosRemoved": photos_removed,
        "timestampsCleared": timestamps_cleared,
        "incidentSnapshotsRemoved": snapshots_removed,
        "incidentsAnonymized": incidents_cleared,
        "consentCleared": bool(clear_consent),
    }


async def company_retention_tick(db: AsyncSession, company_id: UUID) -> dict[str, int]:
    """Apply per-type retention for one company (called from worker retention job)."""
    from datetime import timedelta

    from ..models.video_clip import CLIP_KIND_EVENT, VideoClip

    cfg = await get_retention_settings(db, company_id)
    now = datetime.now(timezone.utc)
    removed_photos = 0
    removed_snaps = 0
    removed_clips = 0

    punch_cut = now - timedelta(days=int(cfg["punchPhotoDays"]))
    if cfg["punchPhotoDays"] > 0:
        old_ts = (
            await db.execute(
                select(EmployeeTimestamp).where(
                    EmployeeTimestamp.companyId == company_id,
                    EmployeeTimestamp.timestamp < punch_cut,
                    EmployeeTimestamp.photoTimestamp.isnot(None),
                ).limit(500)
            )
        ).scalars().all()
        for ts in old_ts:
            fname = _filename_from_url(ts.photoTimestamp)
            if fname and delete_stored_image("uploaded_images", fname):
                removed_photos += 1
            ts.photoTimestamp = None

    snap_cut = now - timedelta(days=int(cfg["incidentSnapshotDays"]))
    if cfg["incidentSnapshotDays"] > 0:
        old_inc = (
            await db.execute(
                select(SentinelIncidentLog).where(
                    SentinelIncidentLog.companyId == company_id,
                    SentinelIncidentLog.occurredAt < snap_cut,
                    SentinelIncidentLog.snapshotUrl.isnot(None),
                ).limit(500)
            )
        ).scalars().all()
        for inc in old_inc:
            fname = _filename_from_url(inc.snapshotUrl)
            if fname:
                delete_stored_image("uploaded_images", fname)
                removed_snaps += 1
            inc.snapshotUrl = None

    clip_days = int(cfg.get("videoClipDays") or 0)
    if clip_days > 0:
        clip_cut = now - timedelta(days=clip_days)
        old_clips = (
            await db.execute(
                select(VideoClip).where(
                    VideoClip.companyId == company_id,
                    VideoClip.kind == CLIP_KIND_EVENT,
                    VideoClip.startedAt < clip_cut,
                ).limit(500)
            )
        ).scalars().all()
        for clip in old_clips:
            key = (clip.storageKey or "").strip()
            if key and not key.startswith("mtx:"):
                delete_stored_image("video_clips", Path(key).name)
                removed_clips += 1
            await db.delete(clip)

    await db.commit()
    return {
        "punchPhotosRemoved": removed_photos,
        "incidentSnapshotsRemoved": removed_snaps,
        "videoClipsRemoved": removed_clips,
    }
