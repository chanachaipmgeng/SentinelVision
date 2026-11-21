"""Enterprise Physical RFID Cards, Multi-Credential & Access Granting Service."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.sentinel import SentinelRfidCard


async def list_rfid_cards(
    db: AsyncSession,
    company_id: UUID,
    query: Optional[str] = None,
    card_status: Optional[str] = None,
    assigned_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[SentinelRfidCard], int]:
    """List RFID badges with search filters and pagination."""
    base_where = [
        SentinelRfidCard.companyId == company_id,
        SentinelRfidCard.deletedAt.is_(None),
    ]
    if query:
        q_wild = f"%{query.strip()}%"
        base_where.append(
            SentinelRfidCard.cardNumber.ilike(q_wild)
            | SentinelRfidCard.holderName.ilike(q_wild)
            | SentinelRfidCard.notes.ilike(q_wild)
        )
    if card_status:
        base_where.append(SentinelRfidCard.cardStatus == card_status)
    if assigned_type:
        base_where.append(SentinelRfidCard.assignedType == assigned_type)

    count_stmt = select(func.count(SentinelRfidCard.cardId)).where(*base_where)
    total_res = await db.execute(count_stmt)
    total_count = total_res.scalar() or 0

    items_stmt = (
        select(SentinelRfidCard)
        .where(*base_where)
        .order_by(desc(SentinelRfidCard.createdAt))
        .limit(limit)
        .offset(offset)
    )
    items_res = await db.execute(items_stmt)
    return list(items_res.scalars().all()), total_count


async def issue_or_update_rfid_card(
    db: AsyncSession,
    company_id: UUID,
    data: dict[str, Any],
    card_id: Optional[UUID] = None,
) -> SentinelRfidCard:
    """Issue a new RFID card or update an existing badge record."""
    card_number = (data.get("cardNumber") or data.get("card_number") or "").strip().upper()
    if not card_number:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_CARD_NUMBER", "message": "cardNumber is required"},
        )

    if card_id:
        stmt = select(SentinelRfidCard).where(
            SentinelRfidCard.cardId == card_id,
            SentinelRfidCard.companyId == company_id,
            SentinelRfidCard.deletedAt.is_(None),
        )
        res = await db.execute(stmt)
        card = res.scalar_one_or_none()
        if not card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "CARD_NOT_FOUND", "message": "RFID card record not found"},
            )
    else:
        card = None

    # Check for duplicate card number in company
    dup_stmt = select(SentinelRfidCard).where(
        SentinelRfidCard.companyId == company_id,
        SentinelRfidCard.cardNumber == card_number,
        SentinelRfidCard.deletedAt.is_(None),
    )
    if card:
        dup_stmt = dup_stmt.where(SentinelRfidCard.cardId != card.cardId)
    dup_res = await db.execute(dup_stmt)
    if dup_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CARD_ALREADY_EXISTS", "message": f"Card number {card_number} is already registered"},
        )

    if not card:
        card = SentinelRfidCard(
            cardId=uuid4(),
            companyId=company_id,
            cardNumber=card_number,
        )
        db.add(card)
    else:
        card.cardNumber = card_number
    card.facilityCode = data.get("facilityCode") or data.get("facility_code")
    card.cardType = data.get("cardType") or data.get("card_type") or "MIFARE"
    card.assignedType = data.get("assignedType") or data.get("assigned_type") or "EMPLOYEE"
    card.holderName = data.get("holderName") or data.get("holder_name")
    if "companyEmployeeId" in data or "company_employee_id" in data:
        raw_emp_id = data.get("companyEmployeeId") or data.get("company_employee_id")
        card.companyEmployeeId = UUID(str(raw_emp_id)) if raw_emp_id else None
    if "identityId" in data or "identity_id" in data:
        raw_id_id = data.get("identityId") or data.get("identity_id")
        card.identityId = UUID(str(raw_id_id)) if raw_id_id else None
    if "cardStatus" in data or "card_status" in data:
        card.cardStatus = data.get("cardStatus") or data.get("card_status") or "ACTIVE"
    if "expiresAt" in data or "expires_at" in data:
        raw_exp = data.get("expiresAt") or data.get("expires_at")
        if isinstance(raw_exp, str):
            card.expiresAt = datetime.fromisoformat(raw_exp)
        elif isinstance(raw_exp, datetime):
            card.expiresAt = raw_exp
    if "notes" in data:
        card.notes = data["notes"]

    await db.commit()
    await db.refresh(card)
    return card


async def update_rfid_card_status(
    db: AsyncSession,
    company_id: UUID,
    card_id: UUID,
    new_status: str,
    notes: Optional[str] = None,
) -> SentinelRfidCard:
    """Update status of an RFID badge (ACTIVE, SUSPENDED, LOST, EXPIRED)."""
    stmt = select(SentinelRfidCard).where(
        SentinelRfidCard.cardId == card_id,
        SentinelRfidCard.companyId == company_id,
        SentinelRfidCard.deletedAt.is_(None),
    )
    res = await db.execute(stmt)
    card = res.scalar_one_or_none()
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CARD_NOT_FOUND", "message": "RFID card not found"},
        )
    card.cardStatus = new_status.strip().upper()
    if notes:
        card.notes = notes
    await db.commit()
    await db.refresh(card)
    return card


async def delete_rfid_card(db: AsyncSession, company_id: UUID, card_id: UUID) -> bool:
    """Soft delete an RFID badge record."""
    stmt = select(SentinelRfidCard).where(
        SentinelRfidCard.cardId == card_id,
        SentinelRfidCard.companyId == company_id,
        SentinelRfidCard.deletedAt.is_(None),
    )
    res = await db.execute(stmt)
    card = res.scalar_one_or_none()
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CARD_NOT_FOUND", "message": "RFID card not found"},
        )
    card.deletedAt = datetime.now(timezone.utc)
    await db.commit()
    return True


async def verify_rfid_access(
    db: AsyncSession,
    company_id: UUID,
    scan_data: dict[str, Any],
) -> dict[str, Any]:
    """Verify physical RFID swipe against registered cards, checking status, validity window, and tenant scope."""
    card_number = (scan_data.get("cardNumber") or scan_data.get("card_number") or "").strip().upper()
    door_name = scan_data.get("doorName") or scan_data.get("door_name") or "Main Access Door"
    facility_code = scan_data.get("facilityCode") or scan_data.get("facility_code")
    now = datetime.now(timezone.utc)

    if not card_number:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_CARD_NUMBER", "message": "cardNumber is required for verification"},
        )

    stmt = select(SentinelRfidCard).where(
        SentinelRfidCard.companyId == company_id,
        SentinelRfidCard.cardNumber == card_number,
        SentinelRfidCard.deletedAt.is_(None),
    )
    res = await db.execute(stmt)
    card = res.scalar_one_or_none()

    if not card:
        return {
            "granted": False,
            "accessStatus": "DENIED",
            "reason": "CARD_NOT_REGISTERED",
            "cardNumber": card_number,
            "doorName": door_name,
            "timestamp": now.isoformat(),
        }

    # Verify facility code if specified
    if facility_code and card.facilityCode and card.facilityCode != str(facility_code).strip():
        return {
            "granted": False,
            "accessStatus": "DENIED",
            "reason": "FACILITY_CODE_MISMATCH",
            "cardNumber": card_number,
            "holderName": card.holderName,
            "doorName": door_name,
            "timestamp": now.isoformat(),
        }

    # Verify status
    if card.cardStatus != "ACTIVE":
        return {
            "granted": False,
            "accessStatus": "DENIED",
            "reason": f"CARD_{card.cardStatus}",
            "cardNumber": card_number,
            "holderName": card.holderName,
            "doorName": door_name,
            "timestamp": now.isoformat(),
        }

    # Verify expiration
    if card.expiresAt and now > card.expiresAt:
        return {
            "granted": False,
            "accessStatus": "DENIED",
            "reason": "CARD_EXPIRED",
            "cardNumber": card_number,
            "holderName": card.holderName,
            "doorName": door_name,
            "timestamp": now.isoformat(),
        }

    # Record swipe telemetry
    card.lastSwipedAt = now
    card.lastDoor = door_name
    await db.commit()

    return {
        "granted": True,
        "accessStatus": "GRANTED",
        "reason": "ACCESS_AUTHORIZED",
        "cardId": str(card.cardId),
        "cardNumber": card.cardNumber,
        "cardType": card.cardType,
        "assignedType": card.assignedType,
        "holderName": card.holderName,
        "companyEmployeeId": str(card.companyEmployeeId) if card.companyEmployeeId else None,
        "identityId": str(card.identityId) if card.identityId else None,
        "doorName": door_name,
        "timestamp": now.isoformat(),
    }
