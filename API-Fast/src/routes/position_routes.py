from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ..config.database import get_db
from ..controllers.position_controller import (
    get_all_positions,
    get_position_by_id,
    get_positions_by_companyId,
    create_position,
    update_position,
    delete_position
)
from ..schemas.position_schema import PositionCreate, PositionUpdate, PositionResponse
from ..models.member import Member
from ..security.deps import (
    assert_request_permission,
    require_permission,
    require_request_system_admin,
)

router = APIRouter()

@router.get("", response_model=List[PositionResponse])
async def get_positions_route(request: Request, db: AsyncSession = Depends(get_db)):
    """Cross-tenant listing — system admin only (Web-Manage uses /company/{companyId})."""
    require_request_system_admin(request)
    return await get_all_positions(db)

@router.get("/{positionId}", response_model=PositionResponse)
async def get_position_by_id_route(request: Request, positionId: str, db: AsyncSession = Depends(get_db)):
    position = await get_position_by_id(positionId, db)
    await assert_request_permission(request, db, "positions.read", position.companyId)
    return position

@router.get("/company/{companyId}", response_model=List[PositionResponse])
async def get_positions_by_companyId_route(
    companyId: str,
    db: AsyncSession = Depends(get_db),
    _: Member = Depends(require_permission("positions.read")),
):
    return await get_positions_by_companyId(companyId, db)

@router.post("", response_model=PositionResponse)
async def create_position_route(request: Request, position: PositionCreate, db: AsyncSession = Depends(get_db)):
    await assert_request_permission(request, db, "positions.write", position.companyId)
    return await create_position(position.dict(), db)

@router.put("/{positionId}", response_model=PositionResponse)
async def update_position_route(request: Request, positionId: str, position: PositionUpdate, db: AsyncSession = Depends(get_db)):
    existing = await get_position_by_id(positionId, db)
    await assert_request_permission(request, db, "positions.write", existing.companyId)
    if position.companyId is not None and position.companyId != existing.companyId:
        await assert_request_permission(request, db, "positions.write", position.companyId)
    return await update_position(positionId, position.dict(exclude_unset=True), db)

@router.delete("/{positionId}")
async def delete_position_route(request: Request, positionId: str, db: AsyncSession = Depends(get_db)):
    existing = await get_position_by_id(positionId, db)
    await assert_request_permission(request, db, "positions.write", existing.companyId)
    await delete_position(positionId, db)
    return {"detail": "Position deleted successfully"}
