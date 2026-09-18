from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ..config.database import get_db
from ..models.member import Member
from ..schemas.member_schema import MemberCreate, MemberResponse, MemberUpdate
from ..controllers.member_controller import (
    get_users,
    get_user_by_id,
    create_user,
    update_user,
    delete_user
)
from ..middlewares.auth_middleware import authenticate_jwt  # Middleware for token authentication

router = APIRouter()

@router.get("", response_model=List[MemberResponse])
async def get_members(
    includeDeleted: bool = False,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(authenticate_jwt)  # Validate JWT token
):
    return await get_users(db, include_deleted=includeDeleted)

@router.get("/{memberId}", response_model=MemberResponse)
async def get_member(
    memberId: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(authenticate_jwt)  # Validate JWT token
):
    member = await get_user_by_id(memberId, db)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return member

@router.post("", response_model=MemberResponse)
async def create_new_member(
    member: MemberCreate,
    db: AsyncSession = Depends(get_db),
):
    return await create_user(member, db)

@router.put("/{memberId}", response_model=MemberResponse)
async def update_existing_member(
    memberId: str, 
    member_update: MemberUpdate, 
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(authenticate_jwt)  # Validate JWT token
):
    return await update_user(memberId, member_update, db)

@router.delete("/{memberId}")
async def delete_existing_member(
    memberId: str, 
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(authenticate_jwt)  # Validate JWT token
):
    return await delete_user(memberId, db)
