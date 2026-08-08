from fastapi import APIRouter, Depends, UploadFile, File, Form, WebSocket
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
    clear_member_face_encodings,
    verify_member_face,
    get_kiosk_attendance,
)
from ..controllers.face_ws_controller import kiosk_websocket
from ..utils.face_gpu_queue import face_gpu_queue_stats
from uuid import UUID

router = APIRouter()


@router.websocket("/ws/kiosk")
async def face_kiosk_ws(websocket: WebSocket):
    """Realtime kiosk stream: session → identify/checkin via GPU queue."""
    await kiosk_websocket(websocket)


@router.get("/queue-stats")
async def face_queue_stats():
    return face_gpu_queue_stats()


@router.get("/kiosk-attendance/{companyId}")
async def kiosk_attendance_route(companyId: UUID, db: AsyncSession = Depends(get_db)):
    """Today's checked-in / not-yet roster for the face kiosk panel."""
    return await get_kiosk_attendance(companyId, db)


@router.post("/members/{memberId}/add-face")
async def add_face_route(
    memberId: UUID, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)
):
    return await add_face(memberId, file, db)


@router.post("/members/check-face-emp")
async def check_face_emp_route(
    files: List[UploadFile] = File(...),
    companyId: UUID = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """1:N match within company only (no timestamp)."""
    return await check_face_emp(files, companyId, db)


@router.post("/members/identify")
async def identify_face_route(
    file: UploadFile = File(...),
    companyId: UUID = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Single-frame identify within company for live name overlay (no timestamp)."""
    return await identify_face(file, companyId, db)


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


@router.post("/members/{memberId}/verify")
async def verify_member_face_route(
    memberId: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Test-scan vs this member only — returns confidence %, no timestamp."""
    return await verify_member_face(memberId, file, db)


@router.delete("/members/{memberId}/encodings")
async def clear_member_encodings_route(
    memberId: UUID, db: AsyncSession = Depends(get_db)
):
    """Clear all enrolled faces for one member."""
    return await clear_member_face_encodings(memberId, db)


@router.delete("/encodings/{faceEncodingId}")
async def delete_encoding_route(
    faceEncodingId: UUID, db: AsyncSession = Depends(get_db)
):
    return await delete_face_encoding(faceEncodingId, db)

