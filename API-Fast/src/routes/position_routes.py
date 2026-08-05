from fastapi import APIRouter, Depends, HTTPException, status
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

router = APIRouter()

@router.get("", response_model=List[PositionResponse])
async def get_positions_route(db: AsyncSession = Depends(get_db)):
    return await get_all_positions(db)

@router.get("/{positionId}", response_model=PositionResponse)
async def get_position_by_id_route(positionId: str, db: AsyncSession = Depends(get_db)):
    return await get_position_by_id(positionId, db)

@router.get("/company/{companyId}", response_model=List[PositionResponse])
async def get_positions_by_companyId_route(companyId: str, db: AsyncSession = Depends(get_db)):
    return await get_positions_by_companyId(companyId, db)

@router.post("", response_model=PositionResponse)
async def create_position_route(position: PositionCreate, db: AsyncSession = Depends(get_db)):
    return await create_position(position.dict(), db)

@router.put("/{positionId}", response_model=PositionResponse)
async def update_position_route(positionId: str, position: PositionUpdate, db: AsyncSession = Depends(get_db)):
    return await update_position(positionId, position.dict(exclude_unset=True), db)

@router.delete("/{positionId}")
async def delete_position_route(positionId: str, db: AsyncSession = Depends(get_db)):
    await delete_position(positionId, db)
    return {"detail": "Position deleted successfully"}
