"""Enterprise Vehicle, Smart Parking, and LPR Barrier Automation Service."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.sentinel import SentinelParkingSpot, SentinelParkingTransaction, SentinelVehicle


async def get_parking_overview(db: AsyncSession, company_id: UUID) -> dict[str, Any]:
    """Retrieve high-level parking telemetry, capacity, occupancy, and active counts."""
    # 1. Total and occupied spots
    spots_stmt = select(
        func.count(SentinelParkingSpot.spotId).label("total_spots"),
        func.count().filter(SentinelParkingSpot.isOccupied.is_(True)).label("occupied_spots"),
    ).where(
        SentinelParkingSpot.companyId == company_id,
        SentinelParkingSpot.deletedAt.is_(None),
    )
    res_spots = await db.execute(spots_stmt)
    total_spots, occupied_spots = res_spots.one()
    total_spots = total_spots or 0
    occupied_spots = occupied_spots or 0
    available_spots = max(0, total_spots - occupied_spots)
    occupancy_rate = round((occupied_spots / total_spots * 100), 1) if total_spots > 0 else 0.0

    # 2. Registered vehicles count
    veh_stmt = select(
        func.count(SentinelVehicle.vehicleId).label("total_vehicles"),
        func.count().filter(SentinelVehicle.status == "ACTIVE").label("active_vehicles"),
        func.count().filter(SentinelVehicle.status == "BLACKLISTED").label("blacklisted_vehicles"),
    ).where(
        SentinelVehicle.companyId == company_id,
        SentinelVehicle.deletedAt.is_(None),
    )
    res_veh = await db.execute(veh_stmt)
    total_veh, active_veh, blacklisted_veh = res_veh.one()

    # 3. Today's transactions
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tx_today_stmt = select(
        func.count(SentinelParkingTransaction.transactionId).label("entries_today"),
        func.count().filter(SentinelParkingTransaction.exitTime.is_not(None)).label("exits_today"),
    ).where(
        SentinelParkingTransaction.companyId == company_id,
        SentinelParkingTransaction.entryTime >= today_start,
    )
    res_tx_today = await db.execute(tx_today_stmt)
    entries_today, exits_today = res_tx_today.one()

    # 4. Zone occupancy breakdown
    zones_stmt = (
        select(
            SentinelParkingSpot.zone,
            func.count(SentinelParkingSpot.spotId).label("total"),
            func.count().filter(SentinelParkingSpot.isOccupied.is_(True)).label("occupied"),
        )
        .where(
            SentinelParkingSpot.companyId == company_id,
            SentinelParkingSpot.deletedAt.is_(None),
        )
        .group_by(SentinelParkingSpot.zone)
        .order_by(SentinelParkingSpot.zone)
    )
    res_zones = await db.execute(zones_stmt)
    zone_breakdown = [
        {
            "zone": row.zone,
            "total": row.total,
            "occupied": row.occupied,
            "available": max(0, row.total - row.occupied),
            "rate": round((row.occupied / row.total * 100), 1) if row.total > 0 else 0.0,
        }
        for row in res_zones.all()
    ]

    # 5. Recent 5 transactions
    recent_tx_stmt = (
        select(SentinelParkingTransaction)
        .where(SentinelParkingTransaction.companyId == company_id)
        .order_by(desc(SentinelParkingTransaction.entryTime))
        .limit(5)
    )
    res_recent_tx = await db.execute(recent_tx_stmt)
    recent_txs = [
        {
            "transactionId": str(tx.transactionId),
            "licensePlate": tx.licensePlate,
            "province": tx.province,
            "entryTime": tx.entryTime.isoformat() if tx.entryTime else None,
            "exitTime": tx.exitTime.isoformat() if tx.exitTime else None,
            "dwellMinutes": tx.dwellMinutes,
            "gateIn": tx.gateIn,
            "gateOut": tx.gateOut,
            "authStatus": tx.authStatus,
            "actionTaken": tx.actionTaken,
        }
        for tx in res_recent_tx.scalars().all()
    ]

    return {
        "totalSpots": total_spots,
        "occupiedSpots": occupied_spots,
        "availableSpots": available_spots,
        "occupancyRate": occupancy_rate,
        "totalVehicles": total_veh or 0,
        "activeVehicles": active_veh or 0,
        "blacklistedVehicles": blacklisted_veh or 0,
        "entriesToday": entries_today or 0,
        "exitsToday": exits_today or 0,
        "zoneBreakdown": zone_breakdown,
        "recentTransactions": recent_txs,
    }


async def list_parking_spots(
    db: AsyncSession,
    company_id: UUID,
    zone: Optional[str] = None,
    status_filter: Optional[str] = None,
    is_occupied: Optional[bool] = None,
) -> list[SentinelParkingSpot]:
    """List parking spots filtered by company and optional zone/occupancy."""
    stmt = (
        select(SentinelParkingSpot)
        .where(
            SentinelParkingSpot.companyId == company_id,
            SentinelParkingSpot.deletedAt.is_(None),
        )
        .order_by(SentinelParkingSpot.zone, SentinelParkingSpot.spotCode)
    )
    if zone:
        stmt = stmt.where(SentinelParkingSpot.zone == zone)
    if status_filter:
        stmt = stmt.where(SentinelParkingSpot.status == status_filter)
    if is_occupied is not None:
        stmt = stmt.where(SentinelParkingSpot.isOccupied.is_(is_occupied))

    res = await db.execute(stmt)
    return list(res.scalars().all())


async def upsert_parking_spot(
    db: AsyncSession,
    company_id: UUID,
    data: dict[str, Any],
    spot_id: Optional[UUID] = None,
) -> SentinelParkingSpot:
    """Create or update a physical parking spot."""
    spot_code = (data.get("spotCode") or data.get("spot_code") or "").strip().upper()
    zone = (data.get("zone") or "Zone A").strip()
    if not spot_code:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_SPOT_CODE", "message": "spotCode is required"},
        )

    if spot_id:
        stmt = select(SentinelParkingSpot).where(
            SentinelParkingSpot.spotId == spot_id,
            SentinelParkingSpot.companyId == company_id,
            SentinelParkingSpot.deletedAt.is_(None),
        )
        res = await db.execute(stmt)
        spot = res.scalar_one_or_none()
        if not spot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "SPOT_NOT_FOUND", "message": "Parking spot not found"},
            )
    else:
        spot = None

    # Check for duplicate spot_code in company
    dup_stmt = select(SentinelParkingSpot).where(
        SentinelParkingSpot.companyId == company_id,
        SentinelParkingSpot.spotCode == spot_code,
        SentinelParkingSpot.deletedAt.is_(None),
    )
    if spot:
        dup_stmt = dup_stmt.where(SentinelParkingSpot.spotId != spot.spotId)
    dup_res = await db.execute(dup_stmt)
    if dup_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "SPOT_ALREADY_EXISTS", "message": f"Spot code {spot_code} already exists"},
        )

    if not spot:
        spot = SentinelParkingSpot(
            spotId=uuid4(),
            companyId=company_id,
            spotCode=spot_code,
            zone=zone,
        )
        db.add(spot)
    else:
        spot.spotCode = spot_code
        spot.zone = zone

    if "floor" in data:
        spot.floor = data["floor"]
    if "spotType" in data or "spot_type" in data:
        spot.spotType = data.get("spotType") or data.get("spot_type") or "STANDARD"
    if "status" in data:
        spot.status = data["status"]

    await db.commit()
    await db.refresh(spot)
    return spot


async def delete_parking_spot(db: AsyncSession, company_id: UUID, spot_id: UUID) -> bool:
    """Soft delete a parking spot."""
    stmt = select(SentinelParkingSpot).where(
        SentinelParkingSpot.spotId == spot_id,
        SentinelParkingSpot.companyId == company_id,
        SentinelParkingSpot.deletedAt.is_(None),
    )
    res = await db.execute(stmt)
    spot = res.scalar_one_or_none()
    if not spot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SPOT_NOT_FOUND", "message": "Parking spot not found"},
        )
    spot.deletedAt = datetime.now(timezone.utc)
    await db.commit()
    return True


async def list_vehicles(
    db: AsyncSession,
    company_id: UUID,
    query: Optional[str] = None,
    owner_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[SentinelVehicle], int]:
    """List registered vehicles with search and pagination."""
    base_where = [
        SentinelVehicle.companyId == company_id,
        SentinelVehicle.deletedAt.is_(None),
    ]
    if query:
        q_wild = f"%{query.strip()}%"
        base_where.append(
            SentinelVehicle.licensePlate.ilike(q_wild)
            | SentinelVehicle.ownerName.ilike(q_wild)
            | SentinelVehicle.brand.ilike(q_wild)
        )
    if owner_type:
        base_where.append(SentinelVehicle.ownerType == owner_type)
    if status_filter:
        base_where.append(SentinelVehicle.status == status_filter)

    count_stmt = select(func.count(SentinelVehicle.vehicleId)).where(*base_where)
    total_res = await db.execute(count_stmt)
    total_count = total_res.scalar() or 0

    items_stmt = (
        select(SentinelVehicle)
        .where(*base_where)
        .order_by(desc(SentinelVehicle.createdAt))
        .limit(limit)
        .offset(offset)
    )
    items_res = await db.execute(items_stmt)
    return list(items_res.scalars().all()), total_count


async def create_or_update_vehicle(
    db: AsyncSession,
    company_id: UUID,
    data: dict[str, Any],
    vehicle_id: Optional[UUID] = None,
) -> SentinelVehicle:
    """Register or update a vehicle record."""
    plate = (data.get("licensePlate") or data.get("license_plate") or "").strip().upper()
    if not plate:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_PLATE", "message": "licensePlate is required"},
        )

    if vehicle_id:
        stmt = select(SentinelVehicle).where(
            SentinelVehicle.vehicleId == vehicle_id,
            SentinelVehicle.companyId == company_id,
            SentinelVehicle.deletedAt.is_(None),
        )
        res = await db.execute(stmt)
        vehicle = res.scalar_one_or_none()
        if not vehicle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "VEHICLE_NOT_FOUND", "message": "Vehicle record not found"},
            )
    else:
        vehicle = None

    # Check for duplicate plate in company
    dup_stmt = select(SentinelVehicle).where(
        SentinelVehicle.companyId == company_id,
        SentinelVehicle.licensePlate == plate,
        SentinelVehicle.deletedAt.is_(None),
    )
    if vehicle:
        dup_stmt = dup_stmt.where(SentinelVehicle.vehicleId != vehicle.vehicleId)
    dup_res = await db.execute(dup_stmt)
    if dup_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "VEHICLE_ALREADY_EXISTS", "message": f"Vehicle with plate {plate} is already registered"},
        )

    if not vehicle:
        vehicle = SentinelVehicle(
            vehicleId=uuid4(),
            companyId=company_id,
            licensePlate=plate,
        )
        db.add(vehicle)
    else:
        vehicle.licensePlate = plate
    vehicle.province = data.get("province")
    vehicle.vehicleType = data.get("vehicleType") or data.get("vehicle_type") or "CAR"
    vehicle.brand = data.get("brand")
    vehicle.model = data.get("model")
    vehicle.color = data.get("color")
    vehicle.ownerType = data.get("ownerType") or data.get("owner_type") or "EMPLOYEE"
    vehicle.ownerName = data.get("ownerName") or data.get("owner_name")
    vehicle.ownerContact = data.get("ownerContact") or data.get("owner_contact")
    if "companyEmployeeId" in data or "company_employee_id" in data:
        raw_emp_id = data.get("companyEmployeeId") or data.get("company_employee_id")
        vehicle.companyEmployeeId = UUID(str(raw_emp_id)) if raw_emp_id else None
    if "identityId" in data or "identity_id" in data:
        raw_id_id = data.get("identityId") or data.get("identity_id")
        vehicle.identityId = UUID(str(raw_id_id)) if raw_id_id else None
    if "status" in data:
        vehicle.status = data["status"]
    if "notes" in data:
        vehicle.notes = data["notes"]

    await db.commit()
    await db.refresh(vehicle)
    return vehicle


async def delete_vehicle(db: AsyncSession, company_id: UUID, vehicle_id: UUID) -> bool:
    """Soft delete a registered vehicle."""
    stmt = select(SentinelVehicle).where(
        SentinelVehicle.vehicleId == vehicle_id,
        SentinelVehicle.companyId == company_id,
        SentinelVehicle.deletedAt.is_(None),
    )
    res = await db.execute(stmt)
    vehicle = res.scalar_one_or_none()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "VEHICLE_NOT_FOUND", "message": "Vehicle record not found"},
        )
    vehicle.deletedAt = datetime.now(timezone.utc)
    await db.commit()
    return True


async def lpr_barrier_scan(
    db: AsyncSession,
    company_id: UUID,
    scan_data: dict[str, Any],
) -> dict[str, Any]:
    """Process real-time LPR camera barrier event: entry/exit authorization, spot binding, and dwell calculation."""
    raw_plate = (scan_data.get("licensePlate") or scan_data.get("license_plate") or "").strip().upper()
    province = scan_data.get("province")
    direction = (scan_data.get("direction") or "ENTRY").strip().upper()
    gate_name = scan_data.get("gateName") or scan_data.get("gate_name") or "Main Gate"
    confidence = float(scan_data.get("confidence") or 0.95)
    snapshot_url = scan_data.get("snapshotUrl") or scan_data.get("snapshot_url")
    now = datetime.now(timezone.utc)

    if not raw_plate:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_PLATE", "message": "licensePlate is required for LPR scan"},
        )

    # 1. Look up vehicle in database
    veh_stmt = select(SentinelVehicle).where(
        SentinelVehicle.companyId == company_id,
        SentinelVehicle.licensePlate == raw_plate,
        SentinelVehicle.deletedAt.is_(None),
    )
    veh_res = await db.execute(veh_stmt)
    vehicle = veh_res.scalar_one_or_none()

    # 2. Determine Authorization Status
    if vehicle and vehicle.status == "BLACKLISTED":
        auth_status = "DENIED"
        action_taken = "BARRIER_HOLD"
        reason = f"ALERT: Blacklisted vehicle {raw_plate} ({vehicle.notes or 'Security risk'})"
    elif vehicle and vehicle.status == "ACTIVE":
        auth_status = "AUTHORIZED"
        action_taken = "BARRIER_OPEN"
        reason = f"Authorized {vehicle.ownerType}: {vehicle.ownerName or raw_plate}"
    else:
        auth_status = "VISITOR_TEMP"
        action_taken = "BARRIER_OPEN"
        reason = f"Temporary Visitor Pass issued for {raw_plate}"

    spot_allocated: Optional[dict[str, Any]] = None
    dwell_minutes: Optional[int] = None
    tx_id = uuid4()

    if direction == "ENTRY":
        # If authorized/visitor, attempt to allocate an available spot
        if action_taken == "BARRIER_OPEN":
            pref_spot_type = "VIP" if (vehicle and vehicle.ownerType == "VIP") else "STANDARD"
            spot_stmt = (
                select(SentinelParkingSpot)
                .where(
                    SentinelParkingSpot.companyId == company_id,
                    SentinelParkingSpot.deletedAt.is_(None),
                    SentinelParkingSpot.isOccupied.is_(False),
                    SentinelParkingSpot.status == "AVAILABLE",
                )
                .order_by(
                    # Prefer exact spotType match, else any available spot
                    (SentinelParkingSpot.spotType != pref_spot_type),
                    SentinelParkingSpot.zone,
                    SentinelParkingSpot.spotCode,
                )
                .limit(1)
            )
            spot_res = await db.execute(spot_stmt)
            spot = spot_res.scalar_one_or_none()
            if spot:
                spot.isOccupied = True
                spot.occupiedVehicleId = vehicle.vehicleId if vehicle else None
                spot.occupiedPlate = raw_plate
                spot.occupiedSince = now
                spot.status = "OCCUPIED"
                spot_allocated = {
                    "spotId": str(spot.spotId),
                    "spotCode": spot.spotCode,
                    "zone": spot.zone,
                    "floor": spot.floor,
                    "spotType": spot.spotType,
                }

        # Create Entry Transaction
        tx = SentinelParkingTransaction(
            transactionId=tx_id,
            companyId=company_id,
            vehicleId=vehicle.vehicleId if vehicle else None,
            spotId=UUID(spot_allocated["spotId"]) if spot_allocated else None,
            licensePlate=raw_plate,
            province=province,
            entryTime=now,
            exitTime=None,
            dwellMinutes=None,
            gateIn=gate_name,
            gateOut=None,
            entryConfidence=confidence,
            exitConfidence=None,
            entrySnapshotUrl=snapshot_url,
            exitSnapshotUrl=None,
            authStatus=auth_status,
            actionTaken=action_taken,
        )
        db.add(tx)

    else:  # EXIT
        # Find active/recent transaction for this plate
        tx_stmt = (
            select(SentinelParkingTransaction)
            .where(
                SentinelParkingTransaction.companyId == company_id,
                SentinelParkingTransaction.licensePlate == raw_plate,
                SentinelParkingTransaction.exitTime.is_(None),
            )
            .order_by(desc(SentinelParkingTransaction.entryTime))
            .limit(1)
        )
        tx_res = await db.execute(tx_stmt)
        active_tx = tx_res.scalar_one_or_none()

        if active_tx:
            diff_seconds = (now - active_tx.entryTime).total_seconds()
            dwell_minutes = max(1, int(diff_seconds / 60))
            active_tx.exitTime = now
            active_tx.dwellMinutes = dwell_minutes
            active_tx.gateOut = gate_name
            active_tx.exitConfidence = confidence
            active_tx.exitSnapshotUrl = snapshot_url
            tx_id = active_tx.transactionId
        else:
            # Standalone exit transaction without prior recorded entry
            tx = SentinelParkingTransaction(
                transactionId=tx_id,
                companyId=company_id,
                vehicleId=vehicle.vehicleId if vehicle else None,
                spotId=None,
                licensePlate=raw_plate,
                province=province,
                entryTime=now,
                exitTime=now,
                dwellMinutes=0,
                gateIn=None,
                gateOut=gate_name,
                entryConfidence=None,
                exitConfidence=confidence,
                entrySnapshotUrl=None,
                exitSnapshotUrl=snapshot_url,
                authStatus=auth_status,
                actionTaken=action_taken,
            )
            db.add(tx)

        # Free occupied spot
        free_stmt = (
            update(SentinelParkingSpot)
            .where(
                SentinelParkingSpot.companyId == company_id,
                SentinelParkingSpot.occupiedPlate == raw_plate,
                SentinelParkingSpot.deletedAt.is_(None),
            )
            .values(
                isOccupied=False,
                occupiedVehicleId=None,
                occupiedPlate=None,
                occupiedSince=None,
                status="AVAILABLE",
            )
        )
        await db.execute(free_stmt)

    await db.commit()

    return {
        "transactionId": str(tx_id),
        "licensePlate": raw_plate,
        "province": province,
        "direction": direction,
        "authStatus": auth_status,
        "actionTaken": action_taken,
        "barrierOpen": action_taken == "BARRIER_OPEN",
        "reason": reason,
        "gate": gate_name,
        "spotAllocated": spot_allocated,
        "dwellMinutes": dwell_minutes,
        "ownerInfo": {
            "ownerType": vehicle.ownerType if vehicle else "UNKNOWN",
            "ownerName": vehicle.ownerName if vehicle else None,
            "vehicleType": vehicle.vehicleType if vehicle else "CAR",
            "brand": vehicle.brand if vehicle else None,
            "model": vehicle.model if vehicle else None,
            "color": vehicle.color if vehicle else None,
        }
        if vehicle
        else None,
        "timestamp": now.isoformat(),
    }


async def list_parking_transactions(
    db: AsyncSession,
    company_id: UUID,
    license_plate: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[SentinelParkingTransaction], int]:
    """List parking transactions with search and pagination."""
    base_where = [SentinelParkingTransaction.companyId == company_id]
    if license_plate:
        base_where.append(SentinelParkingTransaction.licensePlate.ilike(f"%{license_plate.strip()}%"))

    count_stmt = select(func.count(SentinelParkingTransaction.transactionId)).where(*base_where)
    total_res = await db.execute(count_stmt)
    total_count = total_res.scalar() or 0

    items_stmt = (
        select(SentinelParkingTransaction)
        .where(*base_where)
        .order_by(desc(SentinelParkingTransaction.entryTime))
        .limit(limit)
        .offset(offset)
    )
    items_res = await db.execute(items_stmt)
    return list(items_res.scalars().all()), total_count
