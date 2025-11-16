from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, cast, Date
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from uuid import UUID
from datetime import datetime, timedelta

from ..models.employee_timestamp import EmployeeTimestamp
from ..models.company_employee import CompanyEmployee

async def get_dashboard_stats(companyId: UUID, db: AsyncSession):
    """
    รวบรวมสถิติการลงเวลาสำหรับหน้า Dashboard
    """
    try:
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        seven_days_ago = today_start - timedelta(days=7)

        # 1. Total Check-ins Today
        stmt_today = select(func.count(EmployeeTimestamp.timestampId)).where(
            and_(
                EmployeeTimestamp.companyId == companyId,
                EmployeeTimestamp.timestamp >= today_start
            )
        )
        result_today = await db.execute(stmt_today)
        check_ins_today = result_today.scalar_one_or_none() or 0

        # 2. Recent Activity (Last 5 check-ins)
        stmt_recent = (
            select(EmployeeTimestamp)
            .where(EmployeeTimestamp.companyId == companyId)
            .order_by(EmployeeTimestamp.timestamp.desc())
            .limit(5)
            .options(selectinload(EmployeeTimestamp.company_employee).selectinload(CompanyEmployee.member))
        )
        result_recent = await db.execute(stmt_recent)
        recent_activity_raw = result_recent.scalars().all()
        
        recent_activity = [
            {
                "employeeName": f"{ts.company_employee.member.firstName} {ts.company_employee.member.lastName}",
                "timestamp": ts.timestamp,
                "locationName": ts.locationName,
                "timestampType": ts.timestampType
            }
            for ts in recent_activity_raw
        ]

        # 3. Check-ins over the last 7 days (for chart)
        stmt_chart = (
            select(
                cast(EmployeeTimestamp.timestamp, Date).label("date"),
                func.count(EmployeeTimestamp.timestampId).label("count")
            )
            .where(
                and_(
                    EmployeeTimestamp.companyId == companyId,
                    EmployeeTimestamp.timestamp >= seven_days_ago
                )
            )
            .group_by(cast(EmployeeTimestamp.timestamp, Date))
            .order_by(cast(EmployeeTimestamp.timestamp, Date))
        )
        result_chart = await db.execute(stmt_chart)
        chart_data_raw = result_chart.all()

        # Format chart data and fill missing days
        chart_data_map = {row.date.isoformat(): row.count for row in chart_data_raw}
        check_ins_last_7_days = []
        for i in range(7):
            day = (seven_days_ago + timedelta(days=i)).date()
            date_str = day.isoformat()
            check_ins_last_7_days.append({
                "date": date_str,
                "count": chart_data_map.get(date_str, 0)
            })

        # Assemble the final response
        dashboard_data = {
            "summary": {
                "checkInsToday": check_ins_today,
                # Add more summary stats here in the future, e.g., late check-ins
            },
            "chartData": {
                "checkInsLast7Days": check_ins_last_7_days
            },
            "recentActivity": recent_activity
        }

        return dashboard_data

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch dashboard stats: {str(e)}"
        )
