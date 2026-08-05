from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from typing import Optional
from datetime import datetime

from ..schemas.employee_timestamp_schema import EmployeeTimestampUpdate, TimestampApprovalAction
from ..models.employee_timestamp import EmployeeTimestamp, TimestampType, ApprovalStatus
from uuid import UUID
from ..models.company_employee import CompanyEmployee
from ..models.company_location import CompanyLocation
from ..utils.geolocation import get_distance_in_km


def _employee_brief(emp: Optional[CompanyEmployee]) -> Optional[dict]:
    if not emp:
        return None
    member = emp.member
    position = emp.position
    department = emp.department
    return {
        "member": {
            "memberId": member.memberId,
            "username": member.username,
            "email": member.email,
            "firstName": member.firstName,
            "lastName": member.lastName,
            "phoneNumber": getattr(member, "phoneNumber", None),
            "birthDate": getattr(member, "birthDate", None),
            "address": getattr(member, "address", None),
            "emergencyContactName": getattr(member, "emergencyContactName", None),
            "emergencyContactPhone": getattr(member, "emergencyContactPhone", None),
            "attachmentUrls": getattr(member, "attachmentUrls", None),
        }
        if member
        else None,
        "position": {
            "positionId": position.positionId,
            "thName": position.thName,
            "engName": position.engName,
        }
        if position
        else None,
        "department": {
            "departmentId": department.departmentId,
            "thName": department.thName,
            "engName": department.engName,
        }
        if department
        else None,
        "company_employeeId": emp.company_employeeId,
        "employeeId": emp.employeeId or "",
        "bossId": emp.bossId or "",
    }


def _timestamp_payload(time: EmployeeTimestamp) -> dict:
    return {
        "employee": _employee_brief(time.company_employee),
        "company_employeeId": time.company_employeeId,
        "timestampType": time.timestampType,
        "locationName": time.locationName,
        "latitude": time.latitude,
        "longitude": time.longitude,
        "photoTimestamp": time.photoTimestamp,
        "timestampId": time.timestampId,
        "companyId": time.companyId,
        "timestamp": time.timestamp,
        "createdAt": time.createdAt,
        "updatedAt": time.updatedAt,
        "note": time.note,
        "approvalStatus": time.approvalStatus,
        "approvedBy": time.approvedBy,
        "approvedAt": time.approvedAt,
        "rejectReason": time.rejectReason,
    }


async def get_all_timestamps(companyId: str, db: AsyncSession):
    result = await db.execute(
        select(EmployeeTimestamp)
        .where(EmployeeTimestamp.companyId == companyId)
        .options(
            selectinload(EmployeeTimestamp.company_employee).joinedload(CompanyEmployee.member),
            selectinload(EmployeeTimestamp.company_employee).joinedload(CompanyEmployee.position),
            selectinload(EmployeeTimestamp.company_employee).joinedload(CompanyEmployee.department),
        )
    )
    return [_timestamp_payload(time) for time in result.scalars().all()]


async def get_timestamp_by_id(timestampId: UUID, companyId: UUID, db: AsyncSession):
    result = await db.execute(
        select(EmployeeTimestamp)
        .where(
            EmployeeTimestamp.timestampId == timestampId,
            EmployeeTimestamp.companyId == companyId,
        )
        .options(
            selectinload(EmployeeTimestamp.company_employee).joinedload(CompanyEmployee.member),
            selectinload(EmployeeTimestamp.company_employee).joinedload(CompanyEmployee.position),
            selectinload(EmployeeTimestamp.company_employee).joinedload(CompanyEmployee.department),
        )
    )
    timestamp = result.scalar_one_or_none()
    if not timestamp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timestamp not found")
    return _timestamp_payload(timestamp)


def _is_null_island(lat: float, lon: float) -> bool:
    """Placeholder / failed geolocation often arrives as exactly 0,0."""
    try:
        return abs(float(lat)) < 1e-6 and abs(float(lon)) < 1e-6
    except (TypeError, ValueError):
        return True


async def create_timestamp(data: dict, companyId: UUID, db: AsyncSession):
    user_lat = data.get("latitude")
    user_lon = data.get("longitude")
    note = (data.get("note") or "").strip() if data.get("note") else ""

    if user_lat is None or user_lon is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Latitude and Longitude are required.",
        )
    if _is_null_island(user_lat, user_lon):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid GPS coordinates (0,0). Enable location / open kiosk via HTTPS.",
        )

    stmt = select(CompanyLocation).where(CompanyLocation.companyId == companyId)
    result = await db.execute(stmt)
    locations = result.scalars().all()

    is_in_area = False
    found_location_name = "Outside Registered Area"

    if locations:
        for loc in locations:
            distance = get_distance_in_km(user_lat, user_lon, loc.latitude, loc.longitude)
            if distance <= loc.radius:
                is_in_area = True
                found_location_name = loc.locationName
                break

    data["timestampType"] = TimestampType.CHECK_IN if is_in_area else TimestampType.WARNING
    data["locationName"] = found_location_name
    data["companyId"] = companyId
    data["note"] = note or None

    if is_in_area:
        data["approvalStatus"] = ApprovalStatus.NONE.value
    else:
        if not note:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Note is required when checking in outside registered area.",
            )
        data["approvalStatus"] = ApprovalStatus.PENDING.value

    # Drop unknown keys that ORM does not accept
    allowed = {
        "company_employeeId",
        "companyId",
        "timestampType",
        "locationName",
        "latitude",
        "longitude",
        "photoTimestamp",
        "note",
        "approvalStatus",
    }
    clean = {k: v for k, v in data.items() if k in allowed}

    new_timestamp = EmployeeTimestamp(**clean)
    db.add(new_timestamp)
    await db.commit()
    await db.refresh(new_timestamp)

    result = await db.execute(
        select(CompanyEmployee)
        .where(
            CompanyEmployee.company_employeeId == new_timestamp.company_employeeId,
            CompanyEmployee.companyId == companyId,
        )
        .options(
            selectinload(CompanyEmployee.member),
            selectinload(CompanyEmployee.company),
            selectinload(CompanyEmployee.position),
            selectinload(CompanyEmployee.department),
        )
    )
    company_employee = result.scalar_one_or_none()
    if not company_employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company Employee not found")

    new_timestamp.company_employee = company_employee
    return _timestamp_payload(new_timestamp)


async def update_timestamp(
    timestampId: UUID, companyId: UUID, data: EmployeeTimestampUpdate, db: AsyncSession
):
    result = await db.execute(
        select(EmployeeTimestamp).where(
            EmployeeTimestamp.timestampId == timestampId,
            EmployeeTimestamp.companyId == companyId,
        )
    )
    timestamp = result.scalar_one_or_none()
    if not timestamp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timestamp not found")

    payload = data.dict(exclude_unset=True)
    for key, value in payload.items():
        setattr(timestamp, key, value)
    await db.commit()
    await db.refresh(timestamp)
    return timestamp


async def approve_or_reject_timestamp(
    timestampId: UUID,
    companyId: UUID,
    action: TimestampApprovalAction,
    db: AsyncSession,
):
    result = await db.execute(
        select(EmployeeTimestamp)
        .where(
            EmployeeTimestamp.timestampId == timestampId,
            EmployeeTimestamp.companyId == companyId,
        )
        .options(
            selectinload(EmployeeTimestamp.company_employee).joinedload(CompanyEmployee.member),
            selectinload(EmployeeTimestamp.company_employee).joinedload(CompanyEmployee.position),
            selectinload(EmployeeTimestamp.company_employee).joinedload(CompanyEmployee.department),
        )
    )
    timestamp = result.scalar_one_or_none()
    if not timestamp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timestamp not found")

    if timestamp.approvalStatus != ApprovalStatus.PENDING.value and timestamp.approvalStatus != ApprovalStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PENDING timestamps can be approved or rejected.",
        )

    if action.approve:
        timestamp.approvalStatus = ApprovalStatus.APPROVED.value
        timestamp.timestampType = TimestampType.CHECK_IN
        timestamp.rejectReason = None
    else:
        if not (action.rejectReason or "").strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="rejectReason is required when rejecting.",
            )
        timestamp.approvalStatus = ApprovalStatus.REJECTED.value
        timestamp.rejectReason = action.rejectReason.strip()
        timestamp.timestampType = TimestampType.DISAPPROVE

    timestamp.approvedBy = action.approvedBy
    timestamp.approvedAt = datetime.utcnow()
    await db.commit()
    await db.refresh(timestamp)
    return _timestamp_payload(timestamp)


async def delete_timestamp(timestampId: UUID, companyId: UUID, db: AsyncSession):
    result = await db.execute(
        select(EmployeeTimestamp).where(
            EmployeeTimestamp.timestampId == timestampId,
            EmployeeTimestamp.companyId == companyId,
        )
    )
    timestamp = result.scalar_one_or_none()
    if not timestamp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timestamp not found")
    await db.delete(timestamp)
    await db.commit()


async def search_timestamps(
    companyId: str,
    company_employeeId: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    timestampType: Optional[int] = None,
    approvalStatus: Optional[str] = None,
    db: AsyncSession = None,
):
    query = select(EmployeeTimestamp).where(EmployeeTimestamp.companyId == companyId)

    if start_date:
        query = query.where(EmployeeTimestamp.timestamp >= start_date)
    if end_date:
        query = query.where(EmployeeTimestamp.timestamp <= end_date)
    if company_employeeId:
        query = query.where(EmployeeTimestamp.company_employeeId == company_employeeId)
    if timestampType is not None:
        query = query.where(EmployeeTimestamp.timestampType == timestampType)
    if approvalStatus:
        query = query.where(EmployeeTimestamp.approvalStatus == approvalStatus)

    result = await db.execute(
        query.options(
            selectinload(EmployeeTimestamp.company_employee).joinedload(CompanyEmployee.member),
            selectinload(EmployeeTimestamp.company_employee).joinedload(CompanyEmployee.position),
            selectinload(EmployeeTimestamp.company_employee).joinedload(CompanyEmployee.department),
        )
    )
    return [_timestamp_payload(time) for time in result.scalars().all()]
