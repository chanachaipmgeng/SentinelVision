from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from ..config.database import get_db
from ..controllers.dashboard_controller import get_dashboard_stats

router = APIRouter()

@router.get("/stats/{companyId}",
             status_code=status.HTTP_200_OK,
             tags=["Dashboard"],
             summary="Get aggregated statistics for the dashboard")
async def get_dashboard_stats_route(companyId: UUID, db: AsyncSession = Depends(get_db)):
    """
    Provides a set of aggregated data points for displaying on a dashboard, including:
    - **summary**: Key figures like check-ins today.
    - **chartData**: Data formatted for charts, like check-ins over the last 7 days.
    - **recentActivity**: A list of the most recent timestamp events.
    """
    return await get_dashboard_stats(companyId, db)
