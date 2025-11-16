from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ..config.database import get_db
from ..controllers.face_controller import (
    add_face, 
    check_face_emp, 
    get_encodings_for_member, 
    delete_face_encoding
)
from uuid import UUID

router = APIRouter()

# เส้นทาง API สำหรับเพิ่มใบหน้า (ยังคงรับไฟล์เดียว)
@router.post("/members/{memberId}/add-face")
async def add_face_route(memberId: UUID, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    return await add_face(memberId, file, db)

# เส้นทาง API สำหรับตรวจสอบใบหน้าพร้อม Liveness (1:N)
@router.post("/members/check-face-emp")
async def check_face_emp_route(files: List[UploadFile] = File(...), db: AsyncSession = Depends(get_db)):
    return await check_face_emp(files, db)

# --- Admin Management Routes ---

# ดึงข้อมูล Encodings ทั้งหมดของพนักงานคนเดียว
@router.get("/members/{memberId}/encodings", response_model=List[dict])
async def get_encodings_route(memberId: UUID, db: AsyncSession = Depends(get_db)):
    return await get_encodings_for_member(memberId, db)

# ลบ Face Encoding หนึ่งรายการ
@router.delete("/encodings/{faceEncodingId}")
async def delete_encoding_route(faceEncodingId: UUID, db: AsyncSession = Depends(get_db)):
    return await delete_face_encoding(faceEncodingId, db)
