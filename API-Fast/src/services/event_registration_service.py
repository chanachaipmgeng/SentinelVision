"""Public & Admin Event Registration Service with concurrency-safe capacity control."""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import io
import re
from typing import Any, Optional
from uuid import UUID, uuid4

from fastapi import HTTPException, status
import qrcode
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.sentinel import SentinelEvent, SentinelEventRegistration, SentinelIdentity


def _generate_qr_data_url(data: str) -> Optional[str]:
    try:
        qr = qrcode.QRCode(box_size=6, border=2)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"
    except Exception:
        return None


def _slugify(text: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", text.strip().lower())
    return re.sub(r"[-\s]+", "-", cleaned)[:80]


async def get_public_event_by_slug(db: AsyncSession, slug: str) -> dict[str, Any]:
    norm_slug = (slug or "").strip().lower()
    stmt = select(SentinelEvent).where(
        SentinelEvent.publicSlug == norm_slug,
        SentinelEvent.deletedAt.is_(None),
    )
    res = await db.execute(stmt)
    event = res.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    reg_count = (
        await db.scalar(
            select(func.count(SentinelEventRegistration.registrationId)).where(
                SentinelEventRegistration.eventId == event.eventId,
                SentinelEventRegistration.status != "CANCELLED",
                SentinelEventRegistration.deletedAt.is_(None),
            )
        )
        or 0
    )

    now = datetime.now(timezone.utc)
    is_deadline_passed = bool(
        event.registrationDeadline and now > event.registrationDeadline
    )
    is_open = bool(event.registrationOpen and not is_deadline_passed and event.status == "LIVE")
    remaining_seats = max(0, event.capacity - reg_count)

    return {
        "eventId": str(event.eventId),
        "name": event.name,
        "publicSlug": event.publicSlug,
        "locationName": event.locationName,
        "startAt": event.startAt.isoformat(),
        "endAt": event.endAt.isoformat(),
        "welcomeMessage": event.welcomeMessage,
        "description": event.description,
        "capacity": event.capacity,
        "registeredCount": reg_count,
        "remainingSeats": remaining_seats,
        "registrationOpen": is_open,
        "registrationDeadline": (
            event.registrationDeadline.isoformat() if event.registrationDeadline else None
        ),
        "isSoldOut": remaining_seats <= 0,
        "status": event.status,
    }


async def register_public_event(
    db: AsyncSession, slug: str, body: dict[str, Any]
) -> dict[str, Any]:
    full_name = str(body.get("fullName") or "").strip()
    email = str(body.get("email") or "").strip().lower()
    phone_number = str(body.get("phoneNumber") or "").strip() or None
    organization = str(body.get("organization") or "").strip() or None
    consent_accepted = bool(body.get("consentAccepted"))

    if not full_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="fullName is required")
    if not email or "@" not in email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Valid email is required")
    if not consent_accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PDPA biometric/data processing consent is required",
        )

    norm_slug = (slug or "").strip().lower()

    # Lock event row with FOR UPDATE for concurrency-safe capacity check
    stmt = (
        select(SentinelEvent)
        .where(
            SentinelEvent.publicSlug == norm_slug,
            SentinelEvent.deletedAt.is_(None),
        )
        .with_for_update()
    )
    res = await db.execute(stmt)
    event = res.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    now = datetime.now(timezone.utc)
    if not event.registrationOpen or event.status != "LIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration is currently closed for this event",
        )
    if event.registrationDeadline and now > event.registrationDeadline:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration deadline for this event has passed",
        )

    # Check capacity under lock
    active_count = (
        await db.scalar(
            select(func.count(SentinelEventRegistration.registrationId)).where(
                SentinelEventRegistration.eventId == event.eventId,
                SentinelEventRegistration.status != "CANCELLED",
                SentinelEventRegistration.deletedAt.is_(None),
            )
        )
        or 0
    )
    if active_count >= event.capacity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This event has reached full capacity",
        )

    # Check duplicate email
    dup_stmt = select(SentinelEventRegistration).where(
        SentinelEventRegistration.eventId == event.eventId,
        SentinelEventRegistration.email == email,
        SentinelEventRegistration.status != "CANCELLED",
        SentinelEventRegistration.deletedAt.is_(None),
    )
    dup = (await db.execute(dup_stmt)).scalar_one_or_none()
    if dup:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This email address is already registered for this event",
        )

    # Create SentinelIdentity for event attendee
    identity_id = uuid4()
    identity = SentinelIdentity(
        identityId=identity_id,
        companyId=event.companyId,
        identityType="EVENT_ATTENDEE",
        fullName=full_name,
        email=email,
        phoneNumber=phone_number,
        organization=organization,
        eventId=event.eventId,
        visitPurpose=f"Event: {event.name}",
        validFrom=event.startAt,
        expiresAt=event.endAt,
        status="ACTIVE",
    )
    db.add(identity)

    reg_id = uuid4()
    registration = SentinelEventRegistration(
        registrationId=reg_id,
        eventId=event.eventId,
        companyId=event.companyId,
        identityId=identity_id,
        fullName=full_name,
        email=email,
        phoneNumber=phone_number,
        organization=organization,
        status="REGISTERED",
        consentAt=now,
    )
    db.add(registration)
    await db.commit()

    pass_code = f"sv_ev_{reg_id}"
    qr_data_url = _generate_qr_data_url(pass_code)

    return {
        "registered": True,
        "registrationId": str(reg_id),
        "identityId": str(identity_id),
        "passCode": pass_code,
        "qrDataUrl": qr_data_url,
        "eventName": event.name,
        "fullName": full_name,
        "email": email,
        "startAt": event.startAt.isoformat(),
        "endAt": event.endAt.isoformat(),
        "locationName": event.locationName,
        "welcomeMessage": event.welcomeMessage,
    }


async def update_event_registration_settings(
    db: AsyncSession, company_id: UUID, event_id: UUID, data: dict[str, Any]
) -> dict[str, Any]:
    stmt = select(SentinelEvent).where(
        SentinelEvent.eventId == event_id,
        SentinelEvent.companyId == company_id,
        SentinelEvent.deletedAt.is_(None),
    )
    res = await db.execute(stmt)
    event = res.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    if "registrationOpen" in data:
        event.registrationOpen = bool(data["registrationOpen"])
    if "publicSlug" in data:
        raw_slug = str(data["publicSlug"] or "").strip().lower()
        if raw_slug:
            slug = _slugify(raw_slug)
            # check conflict
            check = await db.scalar(
                select(SentinelEvent.eventId).where(
                    SentinelEvent.publicSlug == slug,
                    SentinelEvent.eventId != event.eventId,
                    SentinelEvent.deletedAt.is_(None),
                )
            )
            if check:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Slug '{slug}' is already taken by another event",
                )
            event.publicSlug = slug
        else:
            event.publicSlug = None
    elif event.registrationOpen and not event.publicSlug:
        # Auto generate slug if opening registration without one
        base_slug = _slugify(event.name) or "event"
        slug = f"{base_slug}-{str(event.eventId)[:8]}"
        event.publicSlug = slug

    if "registrationDeadline" in data:
        dl_raw = data["registrationDeadline"]
        if dl_raw:
            event.registrationDeadline = datetime.fromisoformat(str(dl_raw).replace("Z", "+00:00"))
        else:
            event.registrationDeadline = None
    if "description" in data:
        event.description = str(data["description"] or "").strip() or None
    if "capacity" in data and data["capacity"] is not None:
        event.capacity = max(1, int(data["capacity"]))

    event.updatedAt = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(event)

    return {
        "eventId": str(event.eventId),
        "name": event.name,
        "publicSlug": event.publicSlug,
        "registrationOpen": event.registrationOpen,
        "registrationDeadline": (
            event.registrationDeadline.isoformat() if event.registrationDeadline else None
        ),
        "capacity": event.capacity,
        "description": event.description,
    }


async def list_event_registrations(
    db: AsyncSession,
    company_id: UUID,
    event_id: UUID,
    limit: int = 50,
    offset: int = 0,
    search: Optional[str] = None,
    status_filter: Optional[str] = None,
) -> dict[str, Any]:
    # Ensure event exists and belongs to company
    event_stmt = select(SentinelEvent).where(
        SentinelEvent.eventId == event_id,
        SentinelEvent.companyId == company_id,
        SentinelEvent.deletedAt.is_(None),
    )
    event = (await db.execute(event_stmt)).scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    q = select(SentinelEventRegistration).where(
        SentinelEventRegistration.eventId == event_id,
        SentinelEventRegistration.companyId == company_id,
        SentinelEventRegistration.deletedAt.is_(None),
    )
    if status_filter:
        q = q.where(SentinelEventRegistration.status == status_filter.upper())
    if search:
        s = f"%{search.strip().lower()}%"
        q = q.where(
            func.lower(SentinelEventRegistration.fullName).like(s)
            | func.lower(SentinelEventRegistration.email).like(s)
            | func.lower(SentinelEventRegistration.organization).like(s)
        )

    count_stmt = select(func.count()).select_from(q.subquery())
    total = (await db.scalar(count_stmt)) or 0

    items_stmt = q.order_by(SentinelEventRegistration.createdAt.desc()).limit(limit).offset(offset)
    items = (await db.execute(items_stmt)).scalars().all()

    return {
        "total": total,
        "items": [
            {
                "registrationId": str(r.registrationId),
                "eventId": str(r.eventId),
                "identityId": str(r.identityId) if r.identityId else None,
                "fullName": r.fullName,
                "email": r.email,
                "phoneNumber": r.phoneNumber,
                "organization": r.organization,
                "status": r.status,
                "consentAt": r.consentAt.isoformat(),
                "checkInAt": r.checkInAt.isoformat() if r.checkInAt else None,
                "createdAt": r.createdAt.isoformat(),
            }
            for r in items
        ],
    }


async def export_event_registrations_csv(
    db: AsyncSession, company_id: UUID, event_id: UUID
) -> str:
    res = await list_event_registrations(
        db, company_id, event_id, limit=10000, offset=0
    )
    rows = ["Registration ID,Full Name,Email,Phone,Organization,Status,Consent At,Check-in At,Created At"]
    for r in res["items"]:
        def _esc(val: Any) -> str:
            s = str(val or "").replace('"', '""')
            return f'"{s}"'
        rows.append(
            f"{r['registrationId']},{_esc(r['fullName'])},{_esc(r['email'])},{_esc(r['phoneNumber'])},"
            f"{_esc(r['organization'])},{r['status']},{r['consentAt']},{_esc(r['checkInAt'])},{r['createdAt']}"
        )
    return "\n".join(rows)


async def cancel_event_registration(
    db: AsyncSession, company_id: UUID, event_id: UUID, registration_id: UUID
) -> dict[str, Any]:
    stmt = select(SentinelEventRegistration).where(
        SentinelEventRegistration.registrationId == registration_id,
        SentinelEventRegistration.eventId == event_id,
        SentinelEventRegistration.companyId == company_id,
        SentinelEventRegistration.deletedAt.is_(None),
    )
    reg = (await db.execute(stmt)).scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")

    reg.status = "CANCELLED"
    reg.updatedAt = datetime.now(timezone.utc)
    if reg.identityId:
        id_stmt = select(SentinelIdentity).where(
            SentinelIdentity.identityId == reg.identityId,
            SentinelIdentity.companyId == company_id,
        )
        identity = (await db.execute(id_stmt)).scalar_one_or_none()
        if identity:
            identity.status = "INACTIVE"
            identity.updatedAt = datetime.now(timezone.utc)

    await db.commit()
    return {"cancelled": True, "registrationId": str(registration_id)}
