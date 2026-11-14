"""Person presence trail: sightings, session fold, search, dwell, OT evidence, live."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config.settings import settings
from ..models.camera import Camera
from ..models.company_employee import CompanyEmployee
from ..models.employee_timestamp import EmployeeTimestamp
from ..models.hr_schedule import WorkShift
from ..models.member import Member, StatusType
from ..models.person_presence import PersonPresenceSession, PersonSighting
from ..models.sentinel import SentinelEvent
from .company_ai_settings_service import resolve_cctv_camera_interval, resolve_face_match_threshold
from .face_match_service import search_face_pgvector_presence

logger = logging.getLogger("dpu.presence")

PRESENCE_ROLES = frozenset({"LOCATE", "BOOTH", "OT_AREA"})
SESSION_GAP_SECONDS_DEFAULT = 90


def bangkok_tz():
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo("Asia/Bangkok")
    except Exception:  # pragma: no cover
        return timezone(timedelta(hours=7))


def session_gap_seconds() -> int:
    return max(15, int(getattr(settings, "PRESENCE_SESSION_GAP_SECONDS", SESSION_GAP_SECONDS_DEFAULT) or 90))


def camera_presence_meta(cam: Camera) -> dict[str, Any]:
    """Read presenceRole / eventId from camera.aiConfig (defaults LOCATE)."""
    raw = cam.aiConfig if isinstance(cam.aiConfig, dict) else {}
    role = str(raw.get("presenceRole") or raw.get("presence_role") or "LOCATE").strip().upper()
    if role not in PRESENCE_ROLES:
        role = "LOCATE"
    event_id = raw.get("eventId") or raw.get("event_id")
    event_uuid: Optional[UUID] = None
    if event_id:
        try:
            event_uuid = UUID(str(event_id))
        except (TypeError, ValueError):
            event_uuid = None
    if role == "BOOTH" and event_uuid is None:
        # Booth without event stays LOCATE for reporting.
        role = "LOCATE"
    return {"presenceRole": role, "eventId": event_uuid}


def _confidence_from_distance(distance: float) -> float:
    return round(max(0.0, min(1.0, 1.0 - float(distance))) * 100.0, 2)


def _member_display_name(member: Member | None) -> str:
    if member is None:
        return "Employee"
    name = f"{member.firstName or ''} {member.lastName or ''}".strip()
    return name or (member.username or "Employee")


async def record_sighting(
    db: AsyncSession,
    *,
    company_id: UUID,
    member_id: UUID,
    camera: Camera,
    seen_at: Optional[datetime] = None,
    distance: Optional[float] = None,
    confidence: Optional[float] = None,
) -> dict[str, Any]:
    """Insert a sighting and fold into an open presence session (or open a new one)."""
    now = seen_at or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    meta = camera_presence_meta(camera)
    gap = timedelta(seconds=session_gap_seconds())

    sighting = PersonSighting(
        companyId=company_id,
        memberId=member_id,
        cameraId=camera.cameraId,
        zoneId=camera.zoneId,
        siteFloorId=camera.siteFloorId,
        eventId=meta["eventId"],
        seenAt=now,
        distance=distance,
        confidence=confidence if confidence is not None else (
            _confidence_from_distance(distance) if distance is not None else None
        ),
    )
    db.add(sighting)

    # Close any open sessions for this member on a *different* camera.
    other_open = (
        await db.execute(
            select(PersonPresenceSession).where(
                PersonPresenceSession.companyId == company_id,
                PersonPresenceSession.memberId == member_id,
                PersonPresenceSession.open.is_(True),
                PersonPresenceSession.cameraId != camera.cameraId,
            )
        )
    ).scalars().all()
    for sess in other_open:
        sess.open = False
        sess.endedAt = sess.lastSeenAt

    open_same = (
        await db.execute(
            select(PersonPresenceSession)
            .where(
                PersonPresenceSession.companyId == company_id,
                PersonPresenceSession.memberId == member_id,
                PersonPresenceSession.cameraId == camera.cameraId,
                PersonPresenceSession.open.is_(True),
            )
            .order_by(PersonPresenceSession.lastSeenAt.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    if open_same is not None and (now - open_same.lastSeenAt) <= gap:
        open_same.lastSeenAt = now
        open_same.sampleCount = int(open_same.sampleCount or 0) + 1
        open_same.zoneId = camera.zoneId
        open_same.siteFloorId = camera.siteFloorId
        open_same.eventId = meta["eventId"] or open_same.eventId
        open_same.presenceRole = meta["presenceRole"]
        session = open_same
        created = False
    else:
        if open_same is not None:
            open_same.open = False
            open_same.endedAt = open_same.lastSeenAt
        session = PersonPresenceSession(
            companyId=company_id,
            memberId=member_id,
            cameraId=camera.cameraId,
            zoneId=camera.zoneId,
            siteFloorId=camera.siteFloorId,
            eventId=meta["eventId"],
            presenceRole=meta["presenceRole"],
            startedAt=now,
            endedAt=None,
            lastSeenAt=now,
            sampleCount=1,
            open=True,
        )
        db.add(session)
        created = True

    await db.flush()
    return {
        "sightingId": str(sighting.sightingId),
        "sessionId": str(session.sessionId),
        "sessionCreated": created,
        "sampleCount": session.sampleCount,
        "memberId": str(member_id),
        "cameraId": str(camera.cameraId),
        "presenceRole": session.presenceRole,
        "eventId": str(session.eventId) if session.eventId else None,
    }


async def try_record_from_encoding(
    db: AsyncSession,
    *,
    company_id: UUID,
    camera: Camera,
    encoding: list[float],
    seen_at: Optional[datetime] = None,
) -> Optional[dict[str, Any]]:
    """Ambiguity-gated presence match then record_sighting. Returns None if rejected."""
    threshold = await resolve_face_match_threshold(db, company_id)
    margin = float(getattr(settings, "FACE_PRESENCE_AMBIGUITY_MARGIN", 0.08) or 0.08)
    hit = await search_face_pgvector_presence(
        db,
        encoding,
        threshold,
        companyId=company_id,
        ambiguity_margin=margin,
    )
    if hit is None:
        return None
    _fe_id, member_id, distance = hit
    return await record_sighting(
        db,
        company_id=company_id,
        member_id=member_id,
        camera=camera,
        seen_at=seen_at,
        distance=float(distance),
        confidence=_confidence_from_distance(float(distance)),
    )


def _here_cutoff(interval_seconds: int) -> timedelta:
    return timedelta(seconds=max(30, int(interval_seconds) * 2))


async def search_members(
    db: AsyncSession,
    company_id: UUID,
    q: str,
    *,
    limit: int = 20,
) -> dict[str, Any]:
    needle = (q or "").strip()
    safe_limit = min(max(1, int(limit or 20)), 50)
    stmt = (
        select(CompanyEmployee)
        .options(selectinload(CompanyEmployee.member))
        .join(Member, Member.memberId == CompanyEmployee.memberId)
        .where(
            CompanyEmployee.companyId == company_id,
            CompanyEmployee.deletedAt.is_(None),
            Member.deletedAt.is_(None),
            Member.status == StatusType.ENABLE,
        )
    )
    if len(needle) >= 1:
        pattern = f"%{needle}%"
        stmt = stmt.where(
            or_(
                Member.firstName.ilike(pattern),
                Member.lastName.ilike(pattern),
                Member.username.ilike(pattern),
                func.concat(Member.firstName, " ", Member.lastName).ilike(pattern),
            )
        )
    emp_rows = (
        await db.execute(
            stmt.order_by(Member.firstName.asc(), Member.lastName.asc()).limit(safe_limit)
        )
    ).scalars().all()

    interval = await resolve_cctv_camera_interval(db, company_id)
    cutoff = datetime.now(timezone.utc) - _here_cutoff(interval)
    items: list[dict[str, Any]] = []

    for emp in emp_rows:
        member = emp.member
        member_id = emp.memberId
        sess = (
            await db.execute(
                select(PersonPresenceSession)
                .where(
                    PersonPresenceSession.companyId == company_id,
                    PersonPresenceSession.memberId == member_id,
                )
                .order_by(PersonPresenceSession.lastSeenAt.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        status = "not_seen"
        camera_name = None
        camera_id = None
        zone_id = None
        site_floor_id = None
        last_seen_at = None
        confidence = None
        if sess is not None:
            last_seen_at = sess.lastSeenAt.isoformat() if sess.lastSeenAt else None
            camera_id = str(sess.cameraId)
            zone_id = str(sess.zoneId) if sess.zoneId else None
            site_floor_id = str(sess.siteFloorId) if sess.siteFloorId else None
            cam = await db.get(Camera, sess.cameraId)
            camera_name = cam.name if cam else None
            if sess.open and sess.lastSeenAt and sess.lastSeenAt >= cutoff:
                status = "here"
            else:
                status = "last_seen"

        items.append(
            {
                "memberId": str(member_id),
                "employeeId": str(emp.company_employeeId),
                "fullName": _member_display_name(member),
                "status": status,
                "cameraId": camera_id,
                "cameraName": camera_name,
                "zoneId": zone_id,
                "siteFloorId": site_floor_id,
                "lastSeenAt": last_seen_at,
                "confidence": confidence,
                "sessionOpen": bool(sess.open) if sess else False,
            }
        )

    status_rank = {"here": 0, "last_seen": 1, "not_seen": 2}
    items.sort(
        key=lambda x: (
            status_rank.get(str(x.get("status")), 3),
            str(x.get("fullName") or ""),
        )
    )

    return {"items": items, "query": needle, "hereCutoffSeconds": int(_here_cutoff(interval).total_seconds())}


async def member_trail(
    db: AsyncSession,
    company_id: UUID,
    member_id: UUID,
    *,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: int = 200,
) -> dict[str, Any]:
    safe_limit = min(max(1, int(limit or 200)), 500)
    now = datetime.now(timezone.utc)
    end_dt = end or now
    start_dt = start or (end_dt - timedelta(days=1))

    emp = (
        await db.execute(
            select(CompanyEmployee)
            .options(selectinload(CompanyEmployee.member))
            .where(
                CompanyEmployee.companyId == company_id,
                CompanyEmployee.memberId == member_id,
                CompanyEmployee.deletedAt.is_(None),
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if emp is None:
        return {"memberId": str(member_id), "fullName": None, "sessions": []}

    rows = (
        await db.execute(
            select(PersonPresenceSession)
            .where(
                PersonPresenceSession.companyId == company_id,
                PersonPresenceSession.memberId == member_id,
                PersonPresenceSession.startedAt < end_dt,
                or_(
                    PersonPresenceSession.endedAt.is_(None),
                    PersonPresenceSession.endedAt >= start_dt,
                ),
                PersonPresenceSession.lastSeenAt >= start_dt,
            )
            .order_by(PersonPresenceSession.startedAt.asc())
            .limit(safe_limit)
        )
    ).scalars().all()

    cam_ids = {r.cameraId for r in rows}
    cam_names: dict[UUID, str] = {}
    if cam_ids:
        cams = (
            await db.execute(
                select(Camera.cameraId, Camera.name).where(Camera.cameraId.in_(cam_ids))
            )
        ).all()
        cam_names = {cid: name for cid, name in cams}

    sessions: list[dict[str, Any]] = []
    for r in rows:
        end_at = r.endedAt or r.lastSeenAt
        dwell_seconds = max(0, int((end_at - r.startedAt).total_seconds())) if end_at and r.startedAt else 0
        sessions.append(
            {
                "sessionId": str(r.sessionId),
                "cameraId": str(r.cameraId),
                "cameraName": cam_names.get(r.cameraId),
                "zoneId": str(r.zoneId) if r.zoneId else None,
                "siteFloorId": str(r.siteFloorId) if r.siteFloorId else None,
                "eventId": str(r.eventId) if r.eventId else None,
                "presenceRole": r.presenceRole,
                "startedAt": r.startedAt.isoformat() if r.startedAt else None,
                "endedAt": r.endedAt.isoformat() if r.endedAt else None,
                "lastSeenAt": r.lastSeenAt.isoformat() if r.lastSeenAt else None,
                "sampleCount": int(r.sampleCount or 0),
                "open": bool(r.open),
                "dwellSeconds": dwell_seconds,
                "dwellMinutes": round(dwell_seconds / 60.0, 2),
            }
        )

    return {
        "memberId": str(member_id),
        "fullName": _member_display_name(emp.member),
        "from": start_dt.isoformat(),
        "to": end_dt.isoformat(),
        "sessions": sessions,
    }


async def event_dwell_report(
    db: AsyncSession,
    company_id: UUID,
    event_id: UUID,
) -> dict[str, Any]:
    event = await db.get(SentinelEvent, event_id)
    if event is None or event.companyId != company_id or event.deletedAt is not None:
        return {"eventId": str(event_id), "found": False, "people": []}

    rows = (
        await db.execute(
            select(PersonPresenceSession).where(
                PersonPresenceSession.companyId == company_id,
                PersonPresenceSession.eventId == event_id,
                PersonPresenceSession.presenceRole == "BOOTH",
            )
        )
    ).scalars().all()

    cam_ids = {r.cameraId for r in rows}
    cam_names: dict[UUID, str] = {}
    if cam_ids:
        cams = (
            await db.execute(
                select(Camera.cameraId, Camera.name).where(Camera.cameraId.in_(cam_ids))
            )
        ).all()
        cam_names = {cid: name for cid, name in cams}

    by_member: dict[UUID, dict[str, Any]] = {}
    for r in rows:
        end_at = r.endedAt or r.lastSeenAt
        dwell = max(0, int((end_at - r.startedAt).total_seconds())) if end_at and r.startedAt else 0
        bucket = by_member.setdefault(
            r.memberId,
            {
                "memberId": str(r.memberId),
                "fullName": None,
                "firstSeenAt": r.startedAt,
                "totalDwellSeconds": 0,
                "booths": {},
            },
        )
        if r.startedAt and (bucket["firstSeenAt"] is None or r.startedAt < bucket["firstSeenAt"]):
            bucket["firstSeenAt"] = r.startedAt
        bucket["totalDwellSeconds"] += dwell
        booth_key = str(r.cameraId)
        booth = bucket["booths"].setdefault(
            booth_key,
            {
                "cameraId": booth_key,
                "cameraName": cam_names.get(r.cameraId),
                "dwellSeconds": 0,
                "sessions": 0,
            },
        )
        booth["dwellSeconds"] += dwell
        booth["sessions"] += 1

    member_ids = list(by_member.keys())
    if member_ids:
        members = (
            await db.execute(select(Member).where(Member.memberId.in_(member_ids)))
        ).scalars().all()
        names = {m.memberId: _member_display_name(m) for m in members}
        for mid, bucket in by_member.items():
            bucket["fullName"] = names.get(mid)

    people = []
    for bucket in by_member.values():
        booths = []
        for b in bucket["booths"].values():
            booths.append(
                {
                    **b,
                    "dwellMinutes": round(b["dwellSeconds"] / 60.0, 2),
                }
            )
        booths.sort(key=lambda x: x["dwellSeconds"], reverse=True)
        first = bucket["firstSeenAt"]
        people.append(
            {
                "memberId": bucket["memberId"],
                "fullName": bucket["fullName"],
                "firstSeenAt": first.isoformat() if first else None,
                "totalDwellSeconds": bucket["totalDwellSeconds"],
                "totalDwellMinutes": round(bucket["totalDwellSeconds"] / 60.0, 2),
                "booths": booths,
            }
        )
    people.sort(key=lambda p: p["totalDwellSeconds"], reverse=True)

    return {
        "eventId": str(event_id),
        "found": True,
        "eventName": event.name,
        "people": people,
    }


def _parse_shift_end_local(end_time: str, work_date: date) -> datetime:
    """Parse HH:MM shift end into Asia/Bangkok aware datetime on work_date."""
    raw = (end_time or "18:00").strip()
    parts = raw.split(":")
    hour = int(parts[0]) if parts else 18
    minute = int(parts[1]) if len(parts) > 1 else 0
    tz = bangkok_tz()
    return datetime(work_date.year, work_date.month, work_date.day, hour, minute, tzinfo=tz)


async def ot_evidence_report(
    db: AsyncSession,
    company_id: UUID,
    *,
    work_date: Optional[date] = None,
) -> dict[str, Any]:
    """Compare OT_AREA camera dwell after shift end vs punched overtimeMinutes.

    Never creates timestamps — evidence only.
    """
    tz = bangkok_tz()
    local_now = datetime.now(tz)
    day = work_date or local_now.date()
    day_start_local = datetime(day.year, day.month, day.day, 0, 0, 0, tzinfo=tz)
    day_end_local = day_start_local + timedelta(days=1)
    day_start_utc = day_start_local.astimezone(timezone.utc)
    day_end_utc = day_end_local.astimezone(timezone.utc)

    # Cameras tagged OT_AREA for this company.
    cams = (
        await db.execute(
            select(Camera).where(
                Camera.companyId == company_id,
                Camera.deletedAt.is_(None),
                Camera.aiConfig.isnot(None),
            )
        )
    ).scalars().all()
    ot_cam_ids: set[UUID] = set()
    for cam in cams:
        if camera_presence_meta(cam)["presenceRole"] == "OT_AREA":
            ot_cam_ids.add(cam.cameraId)

    sessions: list[PersonPresenceSession] = []
    if ot_cam_ids:
        sessions = list((
            await db.execute(
                select(PersonPresenceSession).where(
                    PersonPresenceSession.companyId == company_id,
                    PersonPresenceSession.cameraId.in_(ot_cam_ids),
                    PersonPresenceSession.presenceRole == "OT_AREA",
                    PersonPresenceSession.lastSeenAt >= day_start_utc,
                    PersonPresenceSession.startedAt < day_end_utc,
                )
            )
        ).scalars().all())

    # Default shift end for company (first active shift) — evidence uses 18:00 if none.
    shift = (
        await db.execute(
            select(WorkShift)
            .where(
                WorkShift.companyId == company_id,
                WorkShift.deletedAt.is_(None),
            )
            .order_by(WorkShift.isDefault.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    default_end = shift.endTime if shift else "18:00"
    shift_end_local = _parse_shift_end_local(default_end, day)
    shift_end_utc = shift_end_local.astimezone(timezone.utc)

    camera_minutes: dict[UUID, int] = {}
    for sess in sessions:
        end_at = sess.endedAt or sess.lastSeenAt
        start_at = max(sess.startedAt, shift_end_utc)
        if end_at <= shift_end_utc:
            continue
        if end_at <= start_at:
            continue
        secs = int((end_at - start_at).total_seconds())
        camera_minutes[sess.memberId] = camera_minutes.get(sess.memberId, 0) + max(0, secs // 60)

    # Punched OT for the work day.
    ts_rows = (
        await db.execute(
            select(EmployeeTimestamp)
            .options(selectinload(EmployeeTimestamp.company_employee))
            .where(
                EmployeeTimestamp.companyId == company_id,
                EmployeeTimestamp.timestamp >= day_start_utc,
                EmployeeTimestamp.timestamp < day_end_utc,
            )
        )
    ).scalars().all()
    punched_ot: dict[UUID, int] = {}
    member_by_emp: dict[UUID, UUID] = {}
    for ts in ts_rows:
        emp = ts.company_employee
        if emp is None:
            continue
        mid = emp.memberId
        member_by_emp[emp.company_employeeId] = mid
        punched_ot[mid] = max(punched_ot.get(mid, 0), int(ts.overtimeMinutes or 0))

    all_members = set(camera_minutes) | set(punched_ot)
    names: dict[UUID, str] = {}
    if all_members:
        members = (
            await db.execute(select(Member).where(Member.memberId.in_(list(all_members))))
        ).scalars().all()
        names = {m.memberId: _member_display_name(m) for m in members}

    items = []
    for mid in sorted(all_members, key=lambda x: names.get(x, str(x))):
        cam_m = int(camera_minutes.get(mid, 0))
        punch_m = int(punched_ot.get(mid, 0))
        if cam_m > 0 and punch_m > 0:
            status = "aligned"
        elif punch_m > 0 and cam_m == 0:
            status = "punch_without_camera"
        elif cam_m > 0 and punch_m == 0:
            status = "camera_without_punch"
        else:
            continue
        items.append(
            {
                "memberId": str(mid),
                "fullName": names.get(mid),
                "cameraOtMinutes": cam_m,
                "punchedOtMinutes": punch_m,
                "status": status,
            }
        )

    return {
        "workDate": day.isoformat(),
        "shiftEndLocal": shift_end_local.isoformat(),
        "otCameraCount": len(ot_cam_ids),
        "items": items,
    }


async def live_by_camera(
    db: AsyncSession,
    company_id: UUID,
    *,
    camera_id: Optional[UUID] = None,
) -> dict[str, Any]:
    interval = await resolve_cctv_camera_interval(db, company_id)
    cutoff = datetime.now(timezone.utc) - _here_cutoff(interval)

    stmt = select(PersonPresenceSession).where(
        PersonPresenceSession.companyId == company_id,
        PersonPresenceSession.open.is_(True),
        PersonPresenceSession.lastSeenAt >= cutoff,
    )
    if camera_id is not None:
        # Tenant isolation: camera must belong to company.
        cam = await db.get(Camera, camera_id)
        if cam is None or cam.companyId != company_id or cam.deletedAt is not None:
            return {"items": [], "cameraId": str(camera_id), "found": False}
        stmt = stmt.where(PersonPresenceSession.cameraId == camera_id)

    rows = (await db.execute(stmt.order_by(PersonPresenceSession.lastSeenAt.desc()).limit(200))).scalars().all()
    member_ids = {r.memberId for r in rows}
    names: dict[UUID, str] = {}
    if member_ids:
        members = (
            await db.execute(select(Member).where(Member.memberId.in_(list(member_ids))))
        ).scalars().all()
        names = {m.memberId: _member_display_name(m) for m in members}

    cam_ids = {r.cameraId for r in rows}
    cams: dict[UUID, Camera] = {}
    if cam_ids:
        cam_rows = (
            await db.execute(select(Camera).where(Camera.cameraId.in_(list(cam_ids))))
        ).scalars().all()
        cams = {c.cameraId: c for c in cam_rows}

    items = []
    for r in rows:
        cam = cams.get(r.cameraId)
        items.append(
            {
                "sessionId": str(r.sessionId),
                "memberId": str(r.memberId),
                "fullName": names.get(r.memberId),
                "cameraId": str(r.cameraId),
                "cameraName": cam.name if cam else None,
                "mapPosX": cam.mapPosX if cam else None,
                "mapPosY": cam.mapPosY if cam else None,
                "siteFloorId": str(r.siteFloorId or (cam.siteFloorId if cam else None) or "") or None,
                "lastSeenAt": r.lastSeenAt.isoformat() if r.lastSeenAt else None,
                "startedAt": r.startedAt.isoformat() if r.startedAt else None,
            }
        )
    return {
        "items": items,
        "cameraId": str(camera_id) if camera_id else None,
        "found": True,
        "hereCutoffSeconds": int(_here_cutoff(interval).total_seconds()),
    }


async def purge_presence_retention(db: AsyncSession, company_id: UUID) -> dict[str, int]:
    """Delete old sightings and closed sessions for one company."""
    now = datetime.now(timezone.utc)
    sight_days = max(1, int(getattr(settings, "PRESENCE_SIGHTING_RETENTION_DAYS", 14) or 14))
    sess_days = max(1, int(getattr(settings, "PRESENCE_SESSION_RETENTION_DAYS", 90) or 90))
    sight_cut = now - timedelta(days=sight_days)
    sess_cut = now - timedelta(days=sess_days)

    sight_res = await db.execute(
        delete(PersonSighting).where(
            PersonSighting.companyId == company_id,
            PersonSighting.seenAt < sight_cut,
        )
    )
    sess_res = await db.execute(
        delete(PersonPresenceSession).where(
            PersonPresenceSession.companyId == company_id,
            PersonPresenceSession.open.is_(False),
            PersonPresenceSession.lastSeenAt < sess_cut,
        )
    )
    return {
        "sightingsRemoved": int(sight_res.rowcount or 0),
        "sessionsRemoved": int(sess_res.rowcount or 0),
    }
