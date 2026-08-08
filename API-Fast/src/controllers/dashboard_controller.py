from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, cast, Date
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from uuid import UUID
from datetime import datetime, timedelta

from ..models.employee_timestamp import EmployeeTimestamp, TimestampType, ApprovalStatus
from ..models.company_employee import CompanyEmployee
from ..models.company_location import CompanyLocation


def _ts_type_value(ts_type) -> int:
    if ts_type is None:
        return -1
    if isinstance(ts_type, TimestampType):
        return int(ts_type.value)
    try:
        return int(ts_type)
    except (TypeError, ValueError):
        return -1


def _activity_item(ts: EmployeeTimestamp) -> dict:
    emp = ts.company_employee
    member = emp.member if emp else None
    name = ""
    picture = None
    employee_code = ""
    if member:
        name = f"{member.firstName or ''} {member.lastName or ''}".strip()
        picture = getattr(member, "picture", None)
    if emp:
        employee_code = emp.employeeId or ""
    return {
        "timestampId": str(ts.timestampId),
        "employeeName": name or "ไม่ทราบชื่อ",
        "employeeId": employee_code,
        "timestamp": ts.timestamp,
        "locationName": ts.locationName or "",
        "timestampType": _ts_type_value(ts.timestampType),
        "latitude": ts.latitude,
        "longitude": ts.longitude,
        "photoTimestamp": ts.photoTimestamp,
        "picture": picture,
        "approvalStatus": ts.approvalStatus or ApprovalStatus.NONE.value,
        "note": ts.note or "",
    }


async def get_dashboard_stats(companyId: UUID, db: AsyncSession):
    """Aggregated check-in stats, chart, map points, and recent activity for the company dashboard."""
    try:
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        seven_days_ago = today_start - timedelta(days=7)

        # --- Summary counts today ---
        stmt_today = select(func.count(EmployeeTimestamp.timestampId)).where(
            and_(
                EmployeeTimestamp.companyId == companyId,
                EmployeeTimestamp.timestamp >= today_start,
            )
        )
        check_ins_today = (await db.execute(stmt_today)).scalar_one_or_none() or 0

        stmt_outside = select(func.count(EmployeeTimestamp.timestampId)).where(
            and_(
                EmployeeTimestamp.companyId == companyId,
                EmployeeTimestamp.timestamp >= today_start,
                EmployeeTimestamp.timestampType == TimestampType.WARNING,
            )
        )
        outside_today = (await db.execute(stmt_outside)).scalar_one_or_none() or 0

        stmt_pending = select(func.count(EmployeeTimestamp.timestampId)).where(
            and_(
                EmployeeTimestamp.companyId == companyId,
                EmployeeTimestamp.approvalStatus == ApprovalStatus.PENDING.value,
            )
        )
        pending_approval = (await db.execute(stmt_pending)).scalar_one_or_none() or 0

        in_area_today = max(0, int(check_ins_today) - int(outside_today))

        # --- Recent activity (realtime feed) ---
        stmt_recent = (
            select(EmployeeTimestamp)
            .where(EmployeeTimestamp.companyId == companyId)
            .order_by(EmployeeTimestamp.timestamp.desc())
            .limit(25)
            .options(
                selectinload(EmployeeTimestamp.company_employee).selectinload(
                    CompanyEmployee.member
                )
            )
        )
        recent_activity_raw = (await db.execute(stmt_recent)).scalars().all()
        recent_activity = [_activity_item(ts) for ts in recent_activity_raw]

        # --- Map points today (with coordinates) ---
        stmt_map = (
            select(EmployeeTimestamp)
            .where(
                and_(
                    EmployeeTimestamp.companyId == companyId,
                    EmployeeTimestamp.timestamp >= today_start,
                    EmployeeTimestamp.latitude.is_not(None),
                    EmployeeTimestamp.longitude.is_not(None),
                )
            )
            .order_by(EmployeeTimestamp.timestamp.desc())
            .limit(200)
            .options(
                selectinload(EmployeeTimestamp.company_employee).selectinload(
                    CompanyEmployee.member
                )
            )
        )
        map_raw = (await db.execute(stmt_map)).scalars().all()
        map_points = []
        for ts in map_raw:
            try:
                lat = float(ts.latitude)
                lng = float(ts.longitude)
            except (TypeError, ValueError):
                continue
            if not (abs(lat) <= 90 and abs(lng) <= 180):
                continue
            item = _activity_item(ts)
            item["latitude"] = lat
            item["longitude"] = lng
            map_points.append(item)

        # --- Company locations (default map center / HQ pins) ---
        stmt_locs = select(CompanyLocation).where(CompanyLocation.companyId == companyId)
        loc_raw = (await db.execute(stmt_locs)).scalars().all()
        company_locations = []
        for loc in loc_raw:
            try:
                lat = float(loc.latitude)
                lng = float(loc.longitude)
            except (TypeError, ValueError):
                continue
            if not (abs(lat) <= 90 and abs(lng) <= 180):
                continue
            loc_type = loc.locationType
            if hasattr(loc_type, "value"):
                loc_type = loc_type.value
            try:
                loc_type = int(loc_type)
            except (TypeError, ValueError):
                loc_type = 0
            company_locations.append(
                {
                    "locationId": str(loc.locationId),
                    "locationName": loc.locationName or "",
                    "latitude": lat,
                    "longitude": lng,
                    "radius": float(loc.radius or 0),
                    "locationType": loc_type,
                }
            )

        # --- 7-day chart ---
        stmt_chart = (
            select(
                cast(EmployeeTimestamp.timestamp, Date).label("date"),
                func.count(EmployeeTimestamp.timestampId).label("count"),
            )
            .where(
                and_(
                    EmployeeTimestamp.companyId == companyId,
                    EmployeeTimestamp.timestamp >= seven_days_ago,
                )
            )
            .group_by(cast(EmployeeTimestamp.timestamp, Date))
            .order_by(cast(EmployeeTimestamp.timestamp, Date))
        )
        chart_data_raw = (await db.execute(stmt_chart)).all()
        chart_data_map = {row.date.isoformat(): row.count for row in chart_data_raw}
        check_ins_last_7_days = []
        for i in range(7):
            day = (seven_days_ago + timedelta(days=i)).date()
            date_str = day.isoformat()
            check_ins_last_7_days.append(
                {"date": date_str, "count": chart_data_map.get(date_str, 0)}
            )

        return {
            "summary": {
                "checkInsToday": check_ins_today,
                "inAreaToday": in_area_today,
                "outsideToday": outside_today,
                "pendingApproval": pending_approval,
            },
            "chartData": {
                "checkInsLast7Days": check_ins_last_7_days,
                "todayBreakdown": {
                    "inArea": in_area_today,
                    "outside": outside_today,
                },
            },
            "mapPoints": map_points,
            "companyLocations": company_locations,
            "recentActivity": recent_activity,
            "serverTime": now.isoformat() + "Z",
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch dashboard stats: {str(e)}",
        )
