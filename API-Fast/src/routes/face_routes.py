from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from ..config.database import get_db
from ..controllers.face_controller import (
    add_face,
    check_face_emp,
    identify_face,
    check_in_face,
    check_in_face_walkby,
    get_encodings_for_member,
    delete_face_encoding,
)
from uuid import UUID

router = APIRouter()


@router.post("/members/{memberId}/add-face")
async def add_face_route(
    memberId: UUID, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)
):
    return await add_face(memberId, file, db)


@router.post("/members/check-face-emp")
async def check_face_emp_route(
    files: List[UploadFile] = File(...), db: AsyncSession = Depends(get_db)
):
    return await check_face_emp(files, db)


@router.post("/members/identify")
async def identify_face_route(
    file: UploadFile = File(...), db: AsyncSession = Depends(get_db)
):
    """Single-frame identify for live name overlay (no liveness / no timestamp)."""
    return await identify_face(file, db)


@router.post("/members/check-in")
async def check_in_face_route(
    files: List[UploadFile] = File(...),
    companyId: UUID = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    note: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Secure mode: multi-frame liveness + match + timestamp."""
    return await check_in_face(
        files, companyId, latitude, longitude, db, note=note
    )


@router.post("/members/check-in-walkby")
async def check_in_face_walkby_route(
    files: List[UploadFile] = File(...),
    companyId: UUID = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    note: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Walk-by mode: 1–2 frames, no motion liveness (multi-person pass-through)."""
    return await check_in_face_walkby(
        files, companyId, latitude, longitude, db, note=note
    )


@router.get("/members/{memberId}/encodings", response_model=List[dict])
async def get_encodings_route(
    memberId: UUID, db: AsyncSession = Depends(get_db)
):
    return await get_encodings_for_member(memberId, db)


@router.delete("/encodings/{faceEncodingId}")
async def delete_encoding_route(
    faceEncodingId: UUID, db: AsyncSession = Depends(get_db)
):
    return await delete_face_encoding(faceEncodingId, db)

