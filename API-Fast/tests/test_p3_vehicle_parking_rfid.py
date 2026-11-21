"""Integration tests for P3: Vehicle LPR, Smart Parking & RFID Physical Access Card Management."""
from __future__ import annotations

import os
from uuid import uuid4
import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.company import Company
from src.services.parking_service import (
    create_or_update_vehicle,
    delete_parking_spot,
    delete_vehicle,
    get_parking_overview,
    list_parking_spots,
    list_parking_transactions,
    list_vehicles,
    lpr_barrier_scan,
    upsert_parking_spot,
)
from src.services.rfid_service import (
    delete_rfid_card,
    issue_or_update_rfid_card,
    list_rfid_cards,
    update_rfid_card_status,
    verify_rfid_access,
)

# Connect to test database or local dev instance
_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://dpu:76UT6hoC40H0RpvO9vX9oVtgYhAX8sBo@localhost:5434/dpu",
)


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(_DB_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def test_company(db_session: AsyncSession):
    company_id = uuid4()
    company = Company(
        companyId=company_id,
        companyName=f"P3 Test Corp {company_id.hex[:6]}",
        companyCode=f"P3_{company_id.hex[:6]}",
        companyInfo="P3 Test Info",
        address="123 Test St, Bangkok",
    )
    db_session.add(company)
    await db_session.commit()
    yield company_id
    # Clean up company and related records cleanly via direct SQL
    from sqlalchemy import delete
    from src.models.sentinel import SentinelParkingSpot, SentinelParkingTransaction, SentinelVehicle, SentinelRfidCard

    await db_session.execute(delete(SentinelParkingTransaction).where(SentinelParkingTransaction.companyId == company_id))
    await db_session.execute(delete(SentinelParkingSpot).where(SentinelParkingSpot.companyId == company_id))
    await db_session.execute(delete(SentinelVehicle).where(SentinelVehicle.companyId == company_id))
    await db_session.execute(delete(SentinelRfidCard).where(SentinelRfidCard.companyId == company_id))
    await db_session.execute(delete(Company).where(Company.companyId == company_id))
    await db_session.commit()


@pytest.mark.asyncio
async def test_parking_spots_crud_and_overview(db_session: AsyncSession, test_company: uuid4):
    cid = test_company

    # 1. Create parking spots
    spot1 = await upsert_parking_spot(
        db_session,
        cid,
        {"spotCode": "P-A101", "zone": "Zone A", "floor": "1F", "spotType": "STANDARD"},
    )
    assert spot1.spotCode == "P-A101"
    assert spot1.zone == "Zone A"
    assert spot1.isOccupied is False

    spot2 = await upsert_parking_spot(
        db_session,
        cid,
        {"spotCode": "P-V201", "zone": "Zone B", "floor": "2F", "spotType": "VIP"},
    )
    assert spot2.spotType == "VIP"

    # 2. Duplicate code in same company rejected
    with pytest.raises(HTTPException) as exc_info:
        await upsert_parking_spot(
            db_session,
            cid,
            {"spotCode": "P-A101", "zone": "Zone A"},
        )
    assert exc_info.value.status_code == 409

    # 3. List spots with zone filter
    spots_zone_a = await list_parking_spots(db_session, cid, zone="Zone A")
    assert len(spots_zone_a) == 1
    assert spots_zone_a[0].spotCode == "P-A101"

    # 4. Overview telemetry
    overview = await get_parking_overview(db_session, cid)
    assert overview["totalSpots"] >= 2
    assert overview["occupiedSpots"] == 0
    assert overview["availableSpots"] >= 2
    assert overview["occupancyRate"] == 0.0

    # 5. Soft delete spot
    del_ok = await delete_parking_spot(db_session, cid, spot1.spotId)
    assert del_ok is True
    spots_after = await list_parking_spots(db_session, cid)
    assert not any(s.spotCode == "P-A101" for s in spots_after)


@pytest.mark.asyncio
async def test_vehicles_crud(db_session: AsyncSession, test_company: uuid4):
    cid = test_company

    # 1. Register vehicle
    veh = await create_or_update_vehicle(
        db_session,
        cid,
        {
            "licensePlate": "9กก9999",
            "province": "กรุงเทพมหานคร",
            "vehicleType": "CAR",
            "brand": "Tesla",
            "model": "Model 3",
            "color": "White",
            "ownerType": "VIP",
            "ownerName": "คุณสมชาย วงศ์สว่าง",
            "ownerContact": "081-999-9999",
            "status": "ACTIVE",
        },
    )
    assert veh.licensePlate == "9กก9999"
    assert veh.ownerType == "VIP"

    # 2. Duplicate plate in same company rejected
    with pytest.raises(HTTPException) as exc_info:
        await create_or_update_vehicle(
            db_session,
            cid,
            {"licensePlate": "9กก9999"},
        )
    assert exc_info.value.status_code == 409

    # 3. List vehicles with query
    items, total = await list_vehicles(db_session, cid, query="สมชาย")
    assert total == 1
    assert items[0].brand == "Tesla"

    # 4. Update vehicle
    updated = await create_or_update_vehicle(
        db_session,
        cid,
        {"licensePlate": "9กก9999", "color": "Midnight Silver", "status": "ACTIVE"},
        vehicle_id=veh.vehicleId,
    )
    assert updated.color == "Midnight Silver"

    # 5. Soft delete vehicle
    del_ok = await delete_vehicle(db_session, cid, veh.vehicleId)
    assert del_ok is True
    items_after, total_after = await list_vehicles(db_session, cid, query="9กก9999")
    assert total_after == 0


@pytest.mark.asyncio
async def test_lpr_barrier_scan_lifecycle(db_session: AsyncSession, test_company: uuid4):
    cid = test_company

    # Create parking spot
    spot = await upsert_parking_spot(
        db_session,
        cid,
        {"spotCode": "VIP-01", "zone": "Zone VIP", "spotType": "VIP"},
    )
    assert spot.spotCode == "VIP-01"

    # 1. Register a Blacklisted vehicle
    await create_or_update_vehicle(
        db_session,
        cid,
        {
            "licensePlate": "8ฮฮ8888",
            "ownerType": "VISITOR",
            "status": "BLACKLISTED",
            "notes": "Repeated unauthorized intrusion attempt",
        },
    )

    # Scan Blacklisted vehicle at gate -> Denied & Barrier Hold
    bl_scan = await lpr_barrier_scan(
        db_session,
        cid,
        {
            "licensePlate": "8ฮฮ8888",
            "direction": "ENTRY",
            "gateName": "South Gate 2",
            "confidence": 0.98,
        },
    )
    assert bl_scan["authStatus"] == "DENIED"
    assert bl_scan["actionTaken"] == "BARRIER_HOLD"
    assert bl_scan["barrierOpen"] is False
    assert "Blacklisted" in bl_scan["reason"]

    # 2. Register Active VIP vehicle
    await create_or_update_vehicle(
        db_session,
        cid,
        {
            "licensePlate": "1กข1234",
            "province": "กรุงเทพมหานคร",
            "ownerType": "VIP",
            "ownerName": "Executive Member",
            "status": "ACTIVE",
        },
    )

    # Scan Entry -> Authorized, Barrier Open, Spot allocated
    entry_scan = await lpr_barrier_scan(
        db_session,
        cid,
        {
            "licensePlate": "1กข1234",
            "province": "กรุงเทพมหานคร",
            "direction": "ENTRY",
            "gateName": "North Gate 1",
            "confidence": 0.97,
        },
    )
    assert entry_scan["authStatus"] == "AUTHORIZED"
    assert entry_scan["barrierOpen"] is True
    assert entry_scan["spotAllocated"] is not None
    assert entry_scan["spotAllocated"]["spotCode"] == "VIP-01"

    # Spot should now be marked occupied
    spots = await list_parking_spots(db_session, cid, zone="Zone VIP")
    assert spots[0].isOccupied is True
    assert spots[0].occupiedPlate == "1กข1234"

    # Scan Exit -> Dwell time calculated, spot freed
    exit_scan = await lpr_barrier_scan(
        db_session,
        cid,
        {
            "licensePlate": "1กข1234",
            "direction": "EXIT",
            "gateName": "North Gate 1",
            "confidence": 0.96,
        },
    )
    assert exit_scan["direction"] == "EXIT"
    assert exit_scan["barrierOpen"] is True
    assert exit_scan["dwellMinutes"] is not None

    # Spot should now be freed
    spots_after = await list_parking_spots(db_session, cid, zone="Zone VIP")
    assert spots_after[0].isOccupied is False
    assert spots_after[0].occupiedPlate is None

    # Transactions list
    txs, count = await list_parking_transactions(db_session, cid, license_plate="1กข1234")
    assert count >= 1
    assert txs[0].exitTime is not None


@pytest.mark.asyncio
async def test_rfid_card_management_and_access(db_session: AsyncSession, test_company: uuid4):
    cid = test_company

    # 1. Issue Active RFID card
    card1 = await issue_or_update_rfid_card(
        db_session,
        cid,
        {
            "cardNumber": "E0040150CA8419",
            "facilityCode": "FAC-01",
            "cardType": "MIFARE",
            "assignedType": "EMPLOYEE",
            "holderName": "วิภาดา สิทธิศักดิ์",
            "cardStatus": "ACTIVE",
        },
    )
    assert card1.cardNumber == "E0040150CA8419"
    assert card1.cardStatus == "ACTIVE"

    # 2. Duplicate card number rejected
    with pytest.raises(HTTPException) as exc_info:
        await issue_or_update_rfid_card(
            db_session,
            cid,
            {"cardNumber": "E0040150CA8419"},
        )
    assert exc_info.value.status_code == 409

    # 3. Swipe Active Card -> Access Granted
    swipe_ok = await verify_rfid_access(
        db_session,
        cid,
        {
            "cardNumber": "E0040150CA8419",
            "facilityCode": "FAC-01",
            "doorName": "Executive Floor Gate",
        },
    )
    assert swipe_ok["granted"] is True
    assert swipe_ok["accessStatus"] == "GRANTED"
    assert swipe_ok["holderName"] == "วิภาดา สิทธิศักดิ์"

    # 4. Swipe with facility code mismatch -> Denied
    swipe_fac_mismatch = await verify_rfid_access(
        db_session,
        cid,
        {
            "cardNumber": "E0040150CA8419",
            "facilityCode": "FAC-99",
            "doorName": "Branch B Gate",
        },
    )
    assert swipe_fac_mismatch["granted"] is False
    assert swipe_fac_mismatch["reason"] == "FACILITY_CODE_MISMATCH"

    # 5. Suspend card and swipe -> Denied
    await update_rfid_card_status(db_session, cid, card1.cardId, "SUSPENDED", notes="Badge reported lost")
    swipe_suspended = await verify_rfid_access(
        db_session,
        cid,
        {
            "cardNumber": "E0040150CA8419",
            "doorName": "Executive Floor Gate",
        },
    )
    assert swipe_suspended["granted"] is False
    assert swipe_suspended["reason"] == "CARD_SUSPENDED"

    # 6. Swipe Unregistered card -> Denied
    swipe_unknown = await verify_rfid_access(
        db_session,
        cid,
        {"cardNumber": "FFFFFFFFFFFFFF"},
    )
    assert swipe_unknown["granted"] is False
    assert swipe_unknown["reason"] == "CARD_NOT_REGISTERED"

    # 7. List cards with query
    items, total = await list_rfid_cards(db_session, cid, query="วิภาดา")
    assert total == 1
    assert items[0].cardStatus == "SUSPENDED"

    # 8. Soft delete card
    del_ok = await delete_rfid_card(db_session, cid, card1.cardId)
    assert del_ok is True
    items_after, total_after = await list_rfid_cards(db_session, cid, query="E0040150CA8419")
    assert total_after == 0
